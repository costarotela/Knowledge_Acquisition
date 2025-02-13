"""
Web-based researcher implementation.
"""

import asyncio
from typing import Dict, List, Optional
from datetime import datetime
import logging
from bs4 import BeautifulSoup
import trafilatura
import newspaper
from newspaper import Article
import hashlib
import re

from .base import (
    BaseResearcher,
    ResearchQuery,
    ResearchFinding,
    ResearchResult
)
from ...knowledge_base.models import ContentType

logger = logging.getLogger(__name__)


class WebResearcher(BaseResearcher):
    """
    Researcher that uses web sources including:
    - Search engines
    - News sites
    - Blogs
    - Documentation
    """
    
    def __init__(self, config: Optional[Dict] = None, **kwargs):
        super().__init__(config, **kwargs)
        
        # Default config
        self.config.update({
            "search_apis": {
                "serpapi": {
                    "api_key": None,  # Set via env var
                    "endpoint": "https://serpapi.com/search"
                },
                "duckduckgo": {
                    "endpoint": "https://api.duckduckgo.com"
                }
            },
            "max_concurrent_downloads": 5,
            "min_article_length": 100,
            "max_article_age_days": 365,
            "blocked_domains": set(),
            "language": "es"  # Spanish default
        })
        
        # Update with provided config
        if config:
            self.config.update(config)
        
        # Download semaphore
        self._download_semaphore = asyncio.Semaphore(
            self.config["max_concurrent_downloads"]
        )
    
    async def research(self, query: ResearchQuery) -> ResearchResult:
        """Conduct web research."""
        start_time = datetime.utcnow()
        
        try:
            # 1. Check cache
            cache_key = self._get_cache_key(query)
            cached = self._load_cache(cache_key)
            if cached:
                return ResearchResult(**cached)
            
            # 2. Get search results
            search_results = await self._search(
                query.query,
                max_results=query.max_results
            )
            
            # 3. Process results concurrently
            tasks = []
            for result in search_results:
                if self._is_valid_url(result["url"]):
                    task = asyncio.create_task(
                        self._process_url(result["url"])
                    )
                    tasks.append(task)
            
            findings = []
            if tasks:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                for result in results:
                    if isinstance(result, ResearchFinding):
                        findings.append(result)
            
            # 4. Create research result
            research_result = ResearchResult(
                query=query,
                findings=findings,
                total_findings=len(findings),
                processing_time=(
                    datetime.utcnow() - start_time
                ).total_seconds(),
                metadata={
                    "source": "web",
                    "search_results": len(search_results),
                    "successful_downloads": len(findings)
                }
            )
            
            # 5. Cache result
            self._save_cache(cache_key, research_result.dict())
            
            return research_result
        
        except Exception as e:
            logger.error(f"Error in web research: {e}", exc_info=True)
            raise
    
    async def _search(
        self,
        query: str,
        max_results: int = 10
    ) -> List[Dict]:
        """Get search results from multiple engines."""
        results = []
        
        # Try SerpAPI if configured
        if self.config["search_apis"]["serpapi"]["api_key"]:
            try:
                serp_results = await self._search_serpapi(query, max_results)
                results.extend(serp_results)
            except Exception as e:
                logger.error(f"SerpAPI search error: {e}")
        
        # Fallback to DuckDuckGo
        if not results:
            try:
                ddg_results = await self._search_duckduckgo(query, max_results)
                results.extend(ddg_results)
            except Exception as e:
                logger.error(f"DuckDuckGo search error: {e}")
        
        return results[:max_results]
    
    async def _search_serpapi(
        self,
        query: str,
        max_results: int
    ) -> List[Dict]:
        """Search using SerpAPI."""
        config = self.config["search_apis"]["serpapi"]
        params = {
            "q": query,
            "api_key": config["api_key"],
            "num": max_results,
            "hl": self.config["language"]
        }
        
        data = await self._make_request(
            config["endpoint"],
            params=params
        )
        
        results = []
        for item in data.get("organic_results", []):
            results.append({
                "url": item["link"],
                "title": item["title"],
                "snippet": item.get("snippet", "")
            })
        
        return results
    
    async def _search_duckduckgo(
        self,
        query: str,
        max_results: int
    ) -> List[Dict]:
        """Search using DuckDuckGo."""
        config = self.config["search_apis"]["duckduckgo"]
        params = {
            "q": query,
            "format": "json",
            "kl": self.config["language"]
        }
        
        data = await self._make_request(
            config["endpoint"],
            params=params
        )
        
        results = []
        for item in data.get("Results", [])[:max_results]:
            results.append({
                "url": item["FirstURL"],
                "title": item["Text"],
                "snippet": ""
            })
        
        return results
    
    def _is_valid_url(self, url: str) -> bool:
        """Check if URL is valid and not blocked."""
        try:
            # Check against blocked domains
            domain = re.search(r"https?://([^/]+)", url)
            if domain and domain.group(1) in self.config["blocked_domains"]:
                return False
            
            # Add more validation as needed
            return True
        
        except Exception:
            return False
    
    async def _process_url(self, url: str) -> Optional[ResearchFinding]:
        """Process a single URL."""
        async with self._download_semaphore:
            try:
                # 1. Download and parse article
                article = await self._download_article(url)
                
                if not article:
                    return None
                
                # 2. Extract content
                content = self._extract_content(article)
                
                if not content or len(content) < self.config["min_article_length"]:
                    return None
                
                # 3. Create finding
                return ResearchFinding(
                    content=content,
                    content_type=ContentType.TEXT,
                    source="web",
                    source_url=url,
                    confidence=self._calculate_confidence(article),
                    metadata={
                        "title": article.title,
                        "authors": article.authors,
                        "publish_date": (
                            article.publish_date.isoformat()
                            if article.publish_date else None
                        ),
                        "language": article.meta_lang or self.config["language"]
                    },
                    timestamp=datetime.utcnow()
                )
            
            except Exception as e:
                logger.error(f"Error processing {url}: {e}")
                return None
    
    async def _download_article(self, url: str) -> Optional[Article]:
        """Download and parse article."""
        try:
            article = Article(url, language=self.config["language"])
            
            # Download in thread pool
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, article.download)
            await loop.run_in_executor(None, article.parse)
            
            return article
        
        except Exception as e:
            logger.error(f"Error downloading {url}: {e}")
            return None
    
    def _extract_content(self, article: Article) -> Optional[str]:
        """Extract clean content from article."""
        try:
            # Use trafilatura for better cleaning
            cleaned = trafilatura.extract(
                article.html,
                include_tables=False,
                include_images=False,
                include_links=False,
                no_fallback=True
            )
            
            if cleaned:
                return cleaned
            
            # Fallback to newspaper3k
            return article.text
        
        except Exception as e:
            logger.error(f"Error extracting content: {e}")
            return None
    
    def _calculate_confidence(self, article: Article) -> float:
        """Calculate confidence score for article."""
        score = 0.5  # Base score
        
        try:
            # Adjust based on various factors
            if article.publish_date:
                age_days = (
                    datetime.utcnow() - article.publish_date
                ).days
                
                if age_days <= self.config["max_article_age_days"]:
                    score += 0.1
            
            if article.authors:
                score += 0.1
            
            if len(article.text) > 1000:
                score += 0.1
            
            if article.meta_lang == self.config["language"]:
                score += 0.1
            
            # Add more factors as needed
            
            return min(score, 1.0)
        
        except Exception:
            return score
