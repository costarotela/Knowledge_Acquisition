"""
Tests for researcher implementations.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
import uuid
from pathlib import Path
import tempfile
import shutil
import json
import aiohttp
from unittest.mock import AsyncMock, patch
import numpy as np
from PIL import Image

from core_system.knowledge_base.models import (
    KnowledgeEntity,
    ContentType,
    Relation
)
from core_system.knowledge_base.storage.base import HybridStore
from core_system.multimodal_processor.alignment import CrossModalAlignment
from core_system.learning.researchers.base import (
    ResearchQuery,
    ResearchFinding,
    ResearchResult,
    BaseResearcher
)
from core_system.learning.researchers.web import WebResearcher
from core_system.learning.researchers.academic import AcademicResearcher
from core_system.learning.researchers.internal import InternalResearcher


@pytest.fixture
def temp_cache_dir():
    """Temporary directory for cache files."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def mock_store(mocker):
    """Mock hybrid store."""
    store = mocker.Mock(spec=HybridStore)
    store.vector_store = mocker.Mock()
    store.graph_store = mocker.Mock()
    
    # Setup mock search results
    mock_entities = [
        KnowledgeEntity(
            id=uuid.uuid4(),
            content_type=ContentType.TEXT,
            content="Test content",
            version=1,
            confidence=0.9,
            embeddings={},
            metadata={
                "timestamp": datetime.utcnow().isoformat()
            },
            relations=[]
        )
        for _ in range(3)
    ]
    
    store.vector_store.search_similar = AsyncMock(return_value=mock_entities)
    store.graph_store.get_related_entities = AsyncMock(return_value=mock_entities)
    
    return store


@pytest.fixture
def mock_alignment(mocker):
    """Mock cross-modal alignment."""
    alignment = mocker.Mock(spec=CrossModalAlignment)
    alignment.align = AsyncMock(return_value=np.random.randn(512))
    return alignment


@pytest.fixture
def mock_session(mocker):
    """Mock aiohttp session."""
    session = mocker.Mock(spec=aiohttp.ClientSession)
    
    # Mock response
    response = mocker.Mock()
    response.__aenter__ = AsyncMock(return_value=response)
    response.__aexit__ = AsyncMock()
    response.raise_for_status = mocker.Mock()
    response.json = AsyncMock(return_value={"status": "ok"})
    
    session.request = AsyncMock(return_value=response)
    return session


def create_test_query() -> ResearchQuery:
    """Create a test research query."""
    return ResearchQuery(
        query="test query",
        modalities=[ContentType.TEXT],
        context={},
        max_results=5,
        min_confidence=0.7,
        timestamp=datetime.utcnow()
    )


class TestBaseResearcher:
    """Tests for BaseResearcher."""
    
    @pytest.mark.asyncio
    async def test_context_manager(self, mock_session):
        """Test context manager protocol."""
        researcher = BaseResearcher()
        
        async with researcher:
            assert researcher._session is not None
        
        assert researcher._session is None
    
    @pytest.mark.asyncio
    async def test_rate_limiting(self, mock_session, mocker):
        """Test request rate limiting."""
        researcher = BaseResearcher({
            "min_request_delay": 0.1
        })
        researcher._session = mock_session
        
        # Make multiple requests
        start_time = datetime.utcnow()
        await asyncio.gather(
            researcher._make_request("http://test1.com"),
            researcher._make_request("http://test2.com")
        )
        duration = (datetime.utcnow() - start_time).total_seconds()
        
        assert duration >= 0.1  # Should respect rate limit
    
    def test_cache_operations(self, temp_cache_dir):
        """Test cache operations."""
        researcher = BaseResearcher(
            cache_dir=temp_cache_dir
        )
        
        # Test data
        key = "test_key"
        data = {"test": "data"}
        
        # Save to cache
        researcher._save_cache(key, data)
        
        # Load from cache
        loaded = researcher._load_cache(key)
        assert loaded["test"] == data["test"]
        
        # Test cache expiry
        old_data = {
            "test": "old",
            "timestamp": (
                datetime.utcnow() - timedelta(days=2)
            ).isoformat()
        }
        researcher._save_cache("old_key", old_data)
        assert researcher._load_cache("old_key") is None


class TestWebResearcher:
    """Tests for WebResearcher."""
    
    @pytest.mark.asyncio
    async def test_web_research(self, mock_session, temp_cache_dir):
        """Test web research process."""
        researcher = WebResearcher(
            cache_dir=temp_cache_dir
        )
        researcher._session = mock_session
        
        # Mock newspaper3k
        with patch("newspaper.Article") as MockArticle:
            mock_article = MockArticle.return_value
            mock_article.title = "Test Title"
            mock_article.text = "Test Content"
            mock_article.authors = ["Author 1"]
            mock_article.publish_date = datetime.utcnow()
            
            result = await researcher.research(create_test_query())
            
            assert isinstance(result, ResearchResult)
            assert result.total_findings >= 0
    
    @pytest.mark.asyncio
    async def test_url_validation(self, temp_cache_dir):
        """Test URL validation."""
        researcher = WebResearcher(
            config={"blocked_domains": {"blocked.com"}},
            cache_dir=temp_cache_dir
        )
        
        assert researcher._is_valid_url("https://good.com/page")
        assert not researcher._is_valid_url("https://blocked.com/page")
    
    @pytest.mark.asyncio
    async def test_content_extraction(self, temp_cache_dir):
        """Test content extraction."""
        researcher = WebResearcher(
            cache_dir=temp_cache_dir
        )
        
        # Mock article
        class MockArticle:
            def __init__(self):
                self.title = "Test"
                self.text = "Content"
                self.html = "<html>Content</html>"
                self.authors = ["Author"]
                self.publish_date = datetime.utcnow()
                self.meta_lang = "es"
        
        content = researcher._extract_content(MockArticle())
        assert content is not None
        assert len(content) > 0


class TestAcademicResearcher:
    """Tests for AcademicResearcher."""
    
    @pytest.mark.asyncio
    async def test_academic_research(self, mock_session, temp_cache_dir):
        """Test academic research process."""
        researcher = AcademicResearcher(
            cache_dir=temp_cache_dir
        )
        researcher._session = mock_session
        
        # Mock scholarly
        with patch("scholarly.search_pubs") as mock_search:
            mock_search.return_value = iter([{
                "scholar_id": "123",
                "num_citations": 10,
                "bib": {
                    "title": "Test Paper",
                    "abstract": "Test Abstract",
                    "author": ["Author 1"],
                    "pub_year": "2023"
                }
            }])
            
            result = await researcher.research(create_test_query())
            
            assert isinstance(result, ResearchResult)
            assert result.total_findings >= 0
    
    @pytest.mark.asyncio
    async def test_publication_validation(self, temp_cache_dir):
        """Test publication validation."""
        researcher = AcademicResearcher(
            config={
                "max_paper_age_years": 5,
                "min_citations": 1
            },
            cache_dir=temp_cache_dir
        )
        
        valid_pub = {
            "year": str(datetime.utcnow().year - 1),
            "citations": 10
        }
        assert researcher._is_valid_publication(valid_pub)
        
        old_pub = {
            "year": str(datetime.utcnow().year - 10),
            "citations": 10
        }
        assert not researcher._is_valid_publication(old_pub)
    
    @pytest.mark.asyncio
    async def test_content_extraction(self, temp_cache_dir):
        """Test content extraction from papers."""
        researcher = AcademicResearcher(
            cache_dir=temp_cache_dir
        )
        
        paper = {
            "title": "Test Paper",
            "abstract": "Test Abstract",
            "authors": ["Author 1", "Author 2"]
        }
        
        content = researcher._extract_paper_content(paper)
        assert "Test Paper" in content
        assert "Test Abstract" in content
        assert "Author 1" in content


class TestInternalResearcher:
    """Tests for InternalResearcher."""
    
    @pytest.mark.asyncio
    async def test_internal_research(
        self,
        mock_store,
        mock_alignment,
        temp_cache_dir
    ):
        """Test internal research process."""
        researcher = InternalResearcher(
            store=mock_store,
            alignment=mock_alignment,
            cache_dir=temp_cache_dir
        )
        
        result = await researcher.research(create_test_query())
        
        assert isinstance(result, ResearchResult)
        assert result.total_findings >= 0
        
        # Verify store interactions
        mock_store.vector_store.search_similar.assert_called_once()
        mock_store.graph_store.get_related_entities.assert_called()
    
    @pytest.mark.asyncio
    async def test_pattern_analysis(
        self,
        mock_store,
        mock_alignment,
        temp_cache_dir
    ):
        """Test pattern analysis."""
        researcher = InternalResearcher(
            store=mock_store,
            alignment=mock_alignment,
            cache_dir=temp_cache_dir
        )
        
        # Create test entities
        entities = [
            KnowledgeEntity(
                id=uuid.uuid4(),
                content_type=ContentType.TEXT,
                content=f"Content {i}",
                version=1,
                confidence=0.8 + i/10,
                embeddings={},
                metadata={
                    "timestamp": (
                        datetime.utcnow() - timedelta(days=i)
                    ).isoformat()
                },
                relations=[
                    Relation(
                        type="related_to",
                        target_id=str(uuid.uuid4()),
                        target_type=ContentType.TEXT,
                        confidence=0.9
                    )
                ]
            )
            for i in range(3)
        ]
        
        patterns = await researcher._analyze_patterns(entities)
        
        assert len(patterns) > 0
        for pattern in patterns:
            assert "statistics" in pattern
            assert "relations" in pattern
            assert "content_patterns" in pattern
    
    @pytest.mark.asyncio
    async def test_insight_generation(
        self,
        mock_store,
        mock_alignment,
        temp_cache_dir
    ):
        """Test insight generation."""
        researcher = InternalResearcher(
            store=mock_store,
            alignment=mock_alignment,
            cache_dir=temp_cache_dir
        )
        
        patterns = [{
            "content_type": ContentType.TEXT,
            "statistics": {
                "count": 5,
                "avg_confidence": 0.9,
                "temporal_range": {
                    "start": "2023-01-01T00:00:00",
                    "end": "2023-12-31T23:59:59",
                    "duration_days": 365
                }
            },
            "relations": [{
                "type": "related_to",
                "target_type": ContentType.TEXT,
                "frequency": 0.8,
                "avg_confidence": 0.9
            }],
            "content_patterns": []
        }]
        
        insights = await researcher._generate_insights(
            patterns,
            create_test_query()
        )
        
        assert len(insights) > 0
        for insight in insights:
            assert "type" in insight
            assert "content" in insight
            assert "confidence" in insight
            assert "evidence" in insight
