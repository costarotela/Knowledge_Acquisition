import pytest
from unittest.mock import Mock, patch
from core_system.learning.researchers import WebResearcher
from core_system.learning.researchers.base import ResearchQuery

@pytest.fixture
def web_researcher():
    return WebResearcher(
        config={
            "language": "es",
            "min_article_length": 100
        }
    )

def test_search_execution():
    """Test execution of web searches"""
    researcher = WebResearcher()
    query = ResearchQuery(
        topic="machine learning",
        depth="medium",
        language="es"
    )
    
    results = researcher.execute_search(query)
    
    assert len(results) > 0
    for result in results:
        assert "url" in result
        assert "title" in result
        assert "snippet" in result

def test_content_extraction():
    """Test extraction of clean content from web pages"""
    researcher = WebResearcher()
    
    test_url = "https://example.com/article"
    with patch("requests.get") as mock_get:
        mock_get.return_value.text = "<html><body><article>Test content</article></body></html>"
        
        content = researcher.extract_content(test_url)
        
        assert content.strip() == "Test content"
        assert len(content) >= researcher.config["min_article_length"]

def test_source_validation():
    """Test validation of web sources"""
    researcher = WebResearcher()
    
    valid_source = {
        "url": "https://example.edu/research",
        "domain_authority": 80,
        "last_updated": "2024-01-01"
    }
    
    invalid_source = {
        "url": "https://suspicious-site.com",
        "domain_authority": 20,
        "last_updated": "2020-01-01"
    }
    
    assert researcher.validate_source(valid_source)
    assert not researcher.validate_source(invalid_source)

def test_rate_limiting():
    """Test rate limiting functionality"""
    researcher = WebResearcher(
        config={
            "requests_per_minute": 10
        }
    )
    
    # Simulate multiple requests
    for _ in range(12):
        researcher.execute_search(
            ResearchQuery(topic="test", depth="low")
        )
    
    # Verify rate limiting was applied
    assert researcher.rate_limiter.is_limited()

def test_cache_mechanism():
    """Test caching of search results"""
    researcher = WebResearcher()
    query = ResearchQuery(
        topic="artificial intelligence",
        depth="low"
    )
    
    # First search should hit the API
    first_results = researcher.execute_search(query)
    
    # Second search should hit the cache
    with patch("requests.get") as mock_get:
        second_results = researcher.execute_search(query)
        assert not mock_get.called
        
    assert first_results == second_results
