"""
Base researcher interface and utilities.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging
from pydantic import BaseModel
import aiohttp
import asyncio
from pathlib import Path
import json

from ...knowledge_base.models import ContentType

logger = logging.getLogger(__name__)


class ResearchQuery(BaseModel):
    """Research query specification."""
    query: str
    modalities: List[ContentType]
    context: Dict[str, Any]
    max_results: int = 10
    min_confidence: float = 0.7
    timestamp: datetime


class ResearchFinding(BaseModel):
    """Individual research finding."""
    content: Any
    content_type: ContentType
    source: str
    source_url: Optional[str]
    confidence: float
    metadata: Dict
    timestamp: datetime


class ResearchResult(BaseModel):
    """Complete research result."""
    query: ResearchQuery
    findings: List[ResearchFinding]
    total_findings: int
    processing_time: float
    metadata: Dict


class BaseResearcher(ABC):
    """Base class for all researchers."""
    
    def __init__(
        self,
        config: Optional[Dict] = None,
        cache_dir: Optional[str] = None
    ):
        self.config = config or {}
        self.cache_dir = Path(cache_dir) if cache_dir else None
        if self.cache_dir:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize HTTP session
        self._session: Optional[aiohttp.ClientSession] = None
        
        # Rate limiting
        self._last_request: Optional[datetime] = None
        self._request_semaphore = asyncio.Semaphore(
            self.config.get("max_concurrent_requests", 3)
        )
    
    async def __aenter__(self):
        """Context manager entry."""
        await self.setup()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        await self.cleanup()
    
    async def setup(self):
        """Set up resources."""
        if not self._session:
            self._session = aiohttp.ClientSession()
    
    async def cleanup(self):
        """Clean up resources."""
        if self._session:
            await self._session.close()
            self._session = None
    
    @abstractmethod
    async def research(self, query: ResearchQuery) -> ResearchResult:
        """Conduct research for the given query."""
        raise NotImplementedError
    
    async def _make_request(
        self,
        url: str,
        method: str = "GET",
        **kwargs
    ) -> Dict:
        """Make rate-limited HTTP request."""
        if not self._session:
            await self.setup()
        
        # Apply rate limiting
        if self._last_request:
            min_delay = self.config.get("min_request_delay", 1.0)
            elapsed = (datetime.utcnow() - self._last_request).total_seconds()
            if elapsed < min_delay:
                await asyncio.sleep(min_delay - elapsed)
        
        async with self._request_semaphore:
            try:
                async with self._session.request(
                    method,
                    url,
                    **kwargs
                ) as response:
                    response.raise_for_status()
                    self._last_request = datetime.utcnow()
                    return await response.json()
            
            except aiohttp.ClientError as e:
                logger.error(f"Request error for {url}: {e}")
                raise
    
    def _load_cache(self, key: str) -> Optional[Dict]:
        """Load cached data."""
        if not self.cache_dir:
            return None
        
        cache_file = self.cache_dir / f"{key}.json"
        if cache_file.exists():
            try:
                with cache_file.open() as f:
                    data = json.load(f)
                
                # Check cache expiry
                if data.get("timestamp"):
                    age = (
                        datetime.utcnow() -
                        datetime.fromisoformat(data["timestamp"])
                    ).total_seconds()
                    
                    max_age = self.config.get("cache_max_age", 86400)  # 1 day
                    if age > max_age:
                        return None
                
                return data
            
            except Exception as e:
                logger.error(f"Error loading cache for {key}: {e}")
                return None
        
        return None
    
    def _save_cache(self, key: str, data: Dict) -> None:
        """Save data to cache."""
        if not self.cache_dir:
            return
        
        try:
            cache_file = self.cache_dir / f"{key}.json"
            data["timestamp"] = datetime.utcnow().isoformat()
            
            with cache_file.open("w") as f:
                json.dump(data, f, indent=2)
        
        except Exception as e:
            logger.error(f"Error saving cache for {key}: {e}")
    
    def _get_cache_key(self, query: ResearchQuery) -> str:
        """Generate cache key for query."""
        # Include relevant query attributes in key
        key_parts = [
            query.query,
            "-".join(str(m) for m in query.modalities),
            str(query.max_results)
        ]
        return "_".join(key_parts)
