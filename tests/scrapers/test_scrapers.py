import pytest
import asyncio
from src.scrapers.providers.youtube_scraper import YouTubeScraper
from src.scrapers.providers.web_scraper import WebScraper
from src.scrapers.base_scraper import ScrapingConfig

@pytest.mark.asyncio
async def test_youtube_scraper():
    scraper = YouTubeScraper(ScrapingConfig(rate_limit=1.0))
    
    # Test URL validation
    valid_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    invalid_url = "https://example.com"
    
    assert await scraper.validate_url(valid_url)
    assert not await scraper.validate_url(invalid_url)
    
    # Test search functionality
    results = await scraper.search("Python programming", max_results=5)
    assert len(results) <= 5
    assert all(isinstance(result, dict) for result in results)
    assert all("title" in result for result in results)

@pytest.mark.asyncio
async def test_web_scraper():
    scraper = WebScraper(ScrapingConfig(rate_limit=1.0))
    
    # Test URL validation
    test_url = "https://example.com"
    assert await scraper.validate_url(test_url)
    
    # Test scraping
    data = await scraper.scrape(test_url)
    assert data.url == test_url
    assert data.title
    assert data.text_content
    assert isinstance(data.links, list)
    assert isinstance(data.images, list)
    
    # Test metadata extraction
    metadata = await scraper.extract_metadata(data.content)
    assert "links_count" in metadata
    assert "images_count" in metadata
    assert "paragraphs_count" in metadata

@pytest.mark.asyncio
async def test_multiple_urls():
    web_scraper = WebScraper(ScrapingConfig(rate_limit=1.0))
    urls = [
        "https://example.com",
        "https://example.org",
    ]
    
    results = await web_scraper.scrape_multiple(urls)
    assert len(results) == 2
    assert all(result.url in urls for result in results)
