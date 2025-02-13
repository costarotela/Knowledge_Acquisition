"""
Tests for knowledge synthesis system.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
import uuid
import numpy as np
from PIL import Image
import io
import json
from unittest.mock import AsyncMock, patch, MagicMock

from core_system.knowledge_base.models import (
    KnowledgeEntity,
    ContentType,
    Relation
)
from core_system.knowledge_base.storage.base import HybridStore
from core_system.multimodal_processor.alignment import CrossModalAlignment
from core_system.learning.researchers.base import (
    ResearchFinding,
    ResearchResult
)
from core_system.learning.synthesis.validator import (
    KnowledgeValidator,
    ValidationRule,
    ValidationResult
)
from core_system.learning.synthesis.synthesizer import (
    KnowledgeSynthesizer,
    SynthesisResult
)


@pytest.fixture
def mock_store():
    """Mock hybrid store."""
    store = MagicMock(spec=HybridStore)
    store.vector_store = MagicMock()
    store.graph_store = MagicMock()
    
    # Setup mock search results
    mock_entities = [
        KnowledgeEntity(
            id=uuid.uuid4(),
            content_type=ContentType.TEXT,
            content="Test content",
            version=1,
            confidence=0.9,
            embeddings={"default": np.random.randn(512).tolist()},
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
def mock_alignment():
    """Mock cross-modal alignment."""
    alignment = MagicMock(spec=CrossModalAlignment)
    alignment.align = AsyncMock(return_value=np.random.randn(512))
    alignment.compare = AsyncMock(return_value=0.8)
    return alignment


def create_test_finding(
    content_type: ContentType = ContentType.TEXT,
    confidence: float = 0.8
) -> ResearchFinding:
    """Create a test research finding."""
    content = "Test content"
    if content_type == ContentType.IMAGE:
        # Create dummy image
        img = Image.new('RGB', (100, 100), color='red')
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        content = buf.getvalue()
    elif content_type == ContentType.AUDIO:
        # Create dummy audio
        content = np.random.randn(16000)  # 1 second at 16kHz
    
    return ResearchFinding(
        content=content,
        content_type=content_type,
        source="test",
        source_url="http://test.com",
        confidence=confidence,
        metadata={
            "timestamp": datetime.utcnow().isoformat()
        },
        timestamp=datetime.utcnow()
    )


class TestKnowledgeValidator:
    """Tests for KnowledgeValidator."""
    
    @pytest.mark.asyncio
    async def test_validation_rules(self, mock_store, mock_alignment):
        """Test validation rules application."""
        validator = KnowledgeValidator(
            store=mock_store,
            alignment=mock_alignment
        )
        
        # Create test findings
        findings = [
            create_test_finding(ContentType.TEXT),
            create_test_finding(ContentType.IMAGE),
            create_test_finding(ContentType.AUDIO)
        ]
        
        # Validate findings
        results = await validator.validate(findings)
        
        assert len(results) == len(findings)
        for result in results:
            assert isinstance(result, ValidationResult)
            assert result.finding is not None
            assert result.rules_applied
            assert result.scores
            assert 0 <= result.overall_score <= 1
            assert isinstance(result.is_valid, bool)
            assert 0 <= result.confidence <= 1
    
    @pytest.mark.asyncio
    async def test_content_validation(self, mock_store, mock_alignment):
        """Test content validation rules."""
        validator = KnowledgeValidator(
            store=mock_store,
            alignment=mock_alignment
        )
        
        # Test with valid content
        finding = create_test_finding(
            content_type=ContentType.TEXT
        )
        results = await validator.validate([finding])
        
        assert results[0].is_valid
        assert "content_length" in results[0].scores
        assert "content_relevance" in results[0].scores
        
        # Test with invalid content
        finding = ResearchFinding(
            content="",  # Empty content
            content_type=ContentType.TEXT,
            source="test",
            source_url="http://test.com",
            confidence=0.8,
            metadata={},
            timestamp=datetime.utcnow()
        )
        results = await validator.validate([finding])
        
        assert not results[0].is_valid
        assert results[0].scores["content_length"] == 0
    
    @pytest.mark.asyncio
    async def test_source_validation(self, mock_store, mock_alignment):
        """Test source validation rules."""
        validator = KnowledgeValidator(
            store=mock_store,
            alignment=mock_alignment
        )
        
        # Test with academic source
        finding = ResearchFinding(
            content="Test content",
            content_type=ContentType.TEXT,
            source="academic",
            source_url="http://scholar.test.com",
            confidence=0.8,
            metadata={
                "authors": ["Author 1"],
                "publish_date": datetime.utcnow().isoformat()
            },
            timestamp=datetime.utcnow()
        )
        results = await validator.validate([finding])
        
        assert results[0].is_valid
        assert results[0].scores["source_reliability"] > 0.7
        
        # Test with web source
        finding.source = "web"
        finding.metadata = {}
        results = await validator.validate([finding])
        
        assert results[0].scores["source_reliability"] < 0.7
    
    @pytest.mark.asyncio
    async def test_consistency_validation(self, mock_store, mock_alignment):
        """Test consistency validation rules."""
        validator = KnowledgeValidator(
            store=mock_store,
            alignment=mock_alignment
        )
        
        # Test with consistent content
        mock_alignment.compare.return_value = 0.9
        finding = create_test_finding()
        results = await validator.validate([finding])
        
        assert results[0].is_valid
        assert results[0].scores["internal_consistency"] > 0.8
        
        # Test with inconsistent content
        mock_alignment.compare.return_value = 0.3
        results = await validator.validate([finding])
        
        assert results[0].scores["internal_consistency"] < 0.5
    
    @pytest.mark.asyncio
    async def test_validation_timeout(self, mock_store, mock_alignment):
        """Test validation timeout handling."""
        validator = KnowledgeValidator(
            store=mock_store,
            alignment=mock_alignment,
            config={"validation_timeout": 0.1}
        )
        
        # Make alignment slow
        async def slow_align(*args):
            await asyncio.sleep(0.2)
            return np.random.randn(512)
        
        mock_alignment.align = slow_align
        
        finding = create_test_finding()
        results = await validator.validate([finding])
        
        assert len(results) == 1
        assert "Timeout" in " ".join(results[0].feedback)


class TestKnowledgeSynthesizer:
    """Tests for KnowledgeSynthesizer."""
    
    @pytest.mark.asyncio
    async def test_synthesis_process(self, mock_store, mock_alignment):
        """Test knowledge synthesis process."""
        synthesizer = KnowledgeSynthesizer(
            store=mock_store,
            alignment=mock_alignment
        )
        
        # Create validation results
        findings = [
            create_test_finding(ContentType.TEXT),
            create_test_finding(ContentType.IMAGE),
            create_test_finding(ContentType.AUDIO)
        ]
        
        validation_results = [
            ValidationResult(
                finding=finding,
                rules_applied=["test_rule"],
                scores={"test_rule": 0.8},
                overall_score=0.8,
                is_valid=True,
                confidence=0.8,
                feedback=[],
                metadata={},
                timestamp=datetime.utcnow()
            )
            for finding in findings
        ]
        
        # Synthesize knowledge
        result = await synthesizer.synthesize(validation_results)
        
        assert isinstance(result, SynthesisResult)
        assert len(result.entities) == len(validation_results)
        assert result.relations
        assert 0 <= result.confidence <= 1
        assert result.metadata["total_findings"] == len(validation_results)
    
    @pytest.mark.asyncio
    async def test_entity_creation(self, mock_store, mock_alignment):
        """Test knowledge entity creation."""
        synthesizer = KnowledgeSynthesizer(
            store=mock_store,
            alignment=mock_alignment
        )
        
        # Create validation result
        finding = create_test_finding()
        validation_result = ValidationResult(
            finding=finding,
            rules_applied=["test_rule"],
            scores={"test_rule": 0.8},
            overall_score=0.8,
            is_valid=True,
            confidence=0.8,
            feedback=[],
            metadata={},
            timestamp=datetime.utcnow()
        )
        
        # Create entity
        entity = await synthesizer._create_entity(validation_result)
        
        assert isinstance(entity, KnowledgeEntity)
        assert entity.content == finding.content
        assert entity.content_type == finding.content_type
        assert entity.confidence == validation_result.confidence
        assert "default" in entity.embeddings
        assert entity.metadata["source"] == finding.source
    
    @pytest.mark.asyncio
    async def test_relation_finding(self, mock_store, mock_alignment):
        """Test relation finding process."""
        synthesizer = KnowledgeSynthesizer(
            store=mock_store,
            alignment=mock_alignment
        )
        
        # Create entities
        entities = [
            KnowledgeEntity(
                id=uuid.uuid4(),
                content_type=ContentType.TEXT,
                content=f"Test content {i}",
                version=1,
                confidence=0.8,
                embeddings={"default": np.random.randn(512).tolist()},
                metadata={},
                relations=[]
            )
            for i in range(3)
        ]
        
        # Find relations
        relations = await synthesizer._find_relations(entities)
        
        assert len(relations) > 0
        for relation in relations:
            assert isinstance(relation, Relation)
            assert relation.type == "similar_to"
            assert relation.confidence >= synthesizer.config["min_confidence"]
    
    @pytest.mark.asyncio
    async def test_invalid_findings(self, mock_store, mock_alignment):
        """Test handling of invalid findings."""
        synthesizer = KnowledgeSynthesizer(
            store=mock_store,
            alignment=mock_alignment
        )
        
        # Create invalid validation results
        validation_results = [
            ValidationResult(
                finding=create_test_finding(),
                rules_applied=["test_rule"],
                scores={"test_rule": 0.3},
                overall_score=0.3,
                is_valid=False,
                confidence=0.3,
                feedback=["Invalid content"],
                metadata={},
                timestamp=datetime.utcnow()
            )
            for _ in range(3)
        ]
        
        # Synthesize knowledge
        result = await synthesizer.synthesize(validation_results)
        
        assert len(result.entities) == 0
        assert len(result.relations) == 0
        assert result.confidence == 0.0
        assert result.metadata["status"] == "no_valid_findings"
