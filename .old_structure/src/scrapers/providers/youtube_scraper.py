import re
from datetime import datetime
from typing import Any, Dict, List, Optional
import aiohttp
import asyncio
from bs4 import BeautifulSoup
from pytube import YouTube, Search
from ..base_scraper import BaseScraper, ScrapedData, ScrapingConfig

class YouTubeData(ScrapedData):
    """Model for YouTube-specific scraped data."""
    title: str
    description: str
    views: Optional[int] = None
    length: Optional[int] = None
    author: str
    publish_date: Optional[datetime] = None
    thumbnail_url: str
    tags: List[str] = []
    captions: Dict[str, str] = {}

class YouTubeScraper(BaseScraper):
    """Scraper implementation for YouTube."""
    
    def __init__(self, config: Optional[ScrapingConfig] = None):
        super().__init__(config)
        self._url_pattern = r'^(https?://)?(www\.)?(youtube\.com|youtu\.be)/.+$'
    
    async def validate_url(self, url: str) -> bool:
        """Check if URL is a valid YouTube URL."""
        return bool(re.match(self._url_pattern, url))
    
    async def scrape(self, url: str) -> YouTubeData:
        """Scrape data from a YouTube video URL."""
        try:
            # Use pytube to extract video information
            yt = YouTube(url)
            
            # Get captions if available
            captions = {}
            if yt.captions:
                for caption in yt.captions:
                    captions[caption.code] = caption.generate_srt_captions()
            
            # Get video length safely
            try:
                length = int(yt.length)
            except (TypeError, ValueError):
                length = None
            
            # Get views safely
            try:
                views = int(yt.views)
            except (TypeError, ValueError):
                views = None
            
            return YouTubeData(
                url=url,
                timestamp=datetime.now().isoformat(),
                content={
                    "video_id": yt.video_id,
                    "streams": [
                        {
                            "itag": stream.itag,
                            "mime_type": stream.mime_type,
                            "resolution": getattr(stream, "resolution", None),
                            "abr": getattr(stream, "abr", None)
                        }
                        for stream in yt.streams
                    ]
                },
                title=yt.title,
                description=yt.description or "",
                views=views,
                length=length,
                author=yt.author,
                publish_date=yt.publish_date,
                thumbnail_url=yt.thumbnail_url,
                tags=yt.keywords if hasattr(yt, "keywords") else [],
                captions=captions,
                metadata={
                    "rating": getattr(yt, "rating", None),
                    "channel_id": yt.channel_id,
                    "channel_url": yt.channel_url
                }
            )
        except Exception as e:
            raise Exception(f"Error scraping YouTube video: {str(e)}")
    
    async def scrape_multiple(self, urls: List[str]) -> List[YouTubeData]:
        """Scrape multiple YouTube videos."""
        tasks = []
        async with aiohttp.ClientSession() as session:
            for url in urls:
                if await self.validate_url(url):
                    tasks.append(self.scrape(url))
                await asyncio.sleep(self.config.rate_limit)
            
            return await asyncio.gather(*tasks)
    
    async def search(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """Search for YouTube videos."""
        try:
            s = Search(query)
            results = []
            
            for i, result in enumerate(s.results):
                if i >= max_results:
                    break
                
                # Get video length safely
                try:
                    duration = int(result.length) if hasattr(result, "length") else None
                except (TypeError, ValueError, AttributeError):
                    duration = None
                
                # Get views safely
                try:
                    views = int(result.views) if hasattr(result, "views") else None
                except (TypeError, ValueError, AttributeError):
                    views = None
                
                # Get publish date safely
                try:
                    publish_date = result.publish_date.isoformat() if result.publish_date else None
                except AttributeError:
                    publish_date = None
                
                results.append({
                    "title": result.title,
                    "url": result.watch_url,
                    "thumbnail": result.thumbnail_url,
                    "channel": result.author,
                    "publish_date": publish_date,
                    "description": result.description or "",
                    "duration": duration,
                    "views": views
                })
                
            return results
        except Exception as e:
            raise Exception(f"Error searching YouTube: {str(e)}")
    
    async def extract_metadata(self, content: Any) -> Dict[str, Any]:
        """Extract metadata from YouTube video content."""
        if not isinstance(content, dict) or "video_id" not in content:
            raise ValueError("Invalid content format")
            
        return {
            "video_id": content["video_id"],
            "available_streams": len(content["streams"]),
            "highest_resolution": max(
                (s["resolution"] for s in content["streams"] if s["resolution"]),
                default=None
            ),
            "has_audio_only": any(
                "audio" in s["mime_type"] and "video" not in s["mime_type"]
                for s in content["streams"]
            )
        }
