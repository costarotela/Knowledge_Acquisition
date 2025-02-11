from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel

class ScrapingConfig(BaseModel):
    """Configuration for scraping operations."""
    max_retries: int = 3
    timeout: int = 30
    headers: Dict[str, str] = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    proxy: Optional[str] = None
    verify_ssl: bool = True
    rate_limit: float = 1.0  # seconds between requests

class ScrapedData(BaseModel):
    """Base model for scraped data."""
    url: str
    timestamp: str
    content: Any
    metadata: Dict[str, Any] = {}

class BaseScraper(ABC):
    """Abstract base class for all scrapers."""
    
    def __init__(self, config: Optional[ScrapingConfig] = None):
        self.config = config or ScrapingConfig()
        
    @abstractmethod
    async def scrape(self, url: str) -> ScrapedData:
        """Scrape data from a single URL."""
        pass
    
    @abstractmethod
    async def scrape_multiple(self, urls: List[str]) -> List[ScrapedData]:
        """Scrape data from multiple URLs."""
        pass
    
    @abstractmethod
    async def search(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """Search for content using the scraper's search capabilities."""
        pass
    
    @abstractmethod
    async def validate_url(self, url: str) -> bool:
        """Validate if a URL is supported by this scraper."""
        pass
    
    @abstractmethod
    async def extract_metadata(self, content: Any) -> Dict[str, Any]:
        """Extract metadata from scraped content."""
        pass
