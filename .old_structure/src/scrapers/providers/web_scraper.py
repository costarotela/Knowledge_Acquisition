import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional
import aiohttp
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from ..base_scraper import BaseScraper, ScrapedData, ScrapingConfig

class WebData(ScrapedData):
    """Model for web-specific scraped data."""
    title: str
    text_content: str
    html_content: str
    links: List[str] = []
    images: List[str] = []

class WebScraper(BaseScraper):
    """General-purpose web scraper implementation."""
    
    def __init__(self, config: Optional[ScrapingConfig] = None):
        super().__init__(config)
        
    async def validate_url(self, url: str) -> bool:
        """Validate if URL is accessible and returns HTML content."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    headers=self.config.headers,
                    proxy=self.config.proxy,
                    ssl=self.config.verify_ssl,
                    timeout=self.config.timeout
                ) as response:
                    return (
                        response.status == 200 and
                        'text/html' in response.headers.get('content-type', '').lower()
                    )
        except:
            return False
    
    async def scrape(self, url: str) -> WebData:
        """Scrape data from a web page."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    headers=self.config.headers,
                    proxy=self.config.proxy,
                    ssl=self.config.verify_ssl,
                    timeout=self.config.timeout
                ) as response:
                    if response.status != 200:
                        raise Exception(f"HTTP {response.status}: {response.reason}")
                    
                    html_content = await response.text()
                    soup = BeautifulSoup(html_content, 'html.parser')
                    
                    # Extract title
                    title = soup.title.string if soup.title else ""
                    
                    # Extract text content
                    for script in soup(["script", "style"]):
                        script.decompose()
                    text_content = soup.get_text(separator='\n', strip=True)
                    
                    # Extract links
                    base_url = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
                    links = [
                        urljoin(base_url, a.get('href'))
                        for a in soup.find_all('a', href=True)
                    ]
                    
                    # Extract images
                    images = [
                        urljoin(base_url, img.get('src'))
                        for img in soup.find_all('img', src=True)
                    ]
                    
                    return WebData(
                        url=url,
                        timestamp=datetime.now().isoformat(),
                        content=html_content,
                        title=title,
                        text_content=text_content,
                        html_content=html_content,
                        links=links,
                        images=images,
                        metadata={
                            "headers": dict(response.headers),
                            "content_type": response.headers.get('content-type'),
                            "content_length": len(html_content),
                            "status_code": response.status
                        }
                    )
        except Exception as e:
            raise Exception(f"Error scraping web page: {str(e)}")
    
    async def scrape_multiple(self, urls: List[str]) -> List[WebData]:
        """Scrape multiple web pages."""
        tasks = []
        async with aiohttp.ClientSession() as session:
            for url in urls:
                if await self.validate_url(url):
                    tasks.append(self.scrape(url))
                await asyncio.sleep(self.config.rate_limit)
            
            return await asyncio.gather(*tasks)
    
    async def search(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """
        Note: This is a placeholder. For real search functionality,
        you would need to integrate with a search engine API like
        Google Custom Search, Bing Web Search, or DuckDuckGo.
        """
        raise NotImplementedError(
            "Web search requires integration with a search engine API. "
            "Please implement this method with your preferred search provider."
        )
    
    async def extract_metadata(self, content: Any) -> Dict[str, Any]:
        """Extract metadata from web page content."""
        if not isinstance(content, str):
            raise ValueError("Invalid content format")
            
        soup = BeautifulSoup(content, 'html.parser')
        
        # Extract meta tags
        meta_tags = {}
        for meta in soup.find_all('meta'):
            name = meta.get('name') or meta.get('property')
            if name:
                meta_tags[name] = meta.get('content')
        
        return {
            "meta_tags": meta_tags,
            "encoding": soup.original_encoding,
            "links_count": len(soup.find_all('a')),
            "images_count": len(soup.find_all('img')),
            "paragraphs_count": len(soup.find_all('p'))
        }
