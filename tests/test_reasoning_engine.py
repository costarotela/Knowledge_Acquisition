"""
Tests for the reasoning engine.
"""

import pytest
import torch
from datetime import datetime, timedelta
import uuid
from PIL import Image
import numpy as np

from core_system.knowledge_base.models import KnowledgeEntity, ContentType
from core_system.knowledge_base.storage.base import HybridStore
from core_system.multimodal_processor.alignment import CrossModalAlignment
from core_system.reasoning.engine import (
    ReasoningEngine,
    Hypothesis,
    ValidationResult,
    KnowledgeSynthesis
)


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
            metadata={},
            relations=[]
        )
        for _ in range(3)
    ]
    
    store.vector_store.search_similar.return_value = mock_entities
    store.graph_store.get_related_entities.return_value = mock_entities
    
    return store


@pytest.fixture
def mock_alignment(mocker):
    """Mock cross-modal alignment."""
    alignment = mocker.Mock(spec=CrossModalAlignment)
    alignment.align.return_value = torch.randn(512)  # Mock embedding
    return alignment


@pytest.fixture
def engine(mock_store, mock_alignment, mocker):
    """Reasoning engine instance with mocked dependencies."""
    # Mock LLM and CLIP
    mocker.patch(
        'transformers.AutoModelForCausalLM.from_pretrained',
        return_value=mocker.Mock()
    )
    mocker.patch(
        'transformers.AutoTokenizer.from_pretrained',
        return_value=mocker.Mock()
    )
    mocker.patch(
        'transformers.CLIPModel.from_pretrained',
        return_value=mocker.Mock()
    )
    mocker.patch(
        'transformers.CLIPProcessor.from_pretrained',
        return_value=mocker.Mock()
    )
    
    engine = ReasoningEngine(
        store=mock_store,
        alignment=mock_alignment
    )
    
    # Mock LLM response generation
    engine._generate_llm_response = mocker.AsyncMock(
        return_value="Mocked LLM response"
    )
    
    return engine


def create_test_hypothesis() -> Hypothesis:
    """Create a test hypothesis."""
    return Hypothesis(
        statement="Test hypothesis statement",
        confidence=0.8,
        evidence=["Evidence 1", "Evidence 2"],
        source_entities=[str(uuid.uuid4())],
        modalities=[ContentType.TEXT],
        timestamp=datetime.utcnow(),
        metadata={}
    )


@pytest.mark.asyncio
async def test_reason_with_context(engine):
    """Test reasoning with provided context."""
    context = [
        KnowledgeEntity(
            id=uuid.uuid4(),
            content_type=ContentType.TEXT,
            content="Test content",
            version=1,
            confidence=0.9,
            embeddings={},
            metadata={},
            relations=[]
        )
    ]
    
    result = await engine.reason(
        query="Test query",
        context_entities=context
    )
    
    assert isinstance(result, KnowledgeSynthesis)
    assert result.statement
    assert result.confidence > 0
    assert len(result.source_hypotheses) > 0


@pytest.mark.asyncio
async def test_reason_without_context(engine, mock_store):
    """Test reasoning without provided context."""
    result = await engine.reason(
        query="Test query"
    )
    
    assert isinstance(result, KnowledgeSynthesis)
    mock_store.vector_store.search_similar.assert_called_once()
    mock_store.graph_store.get_related_entities.assert_called_once()


@pytest.mark.asyncio
async def test_hypothesis_generation(engine):
    """Test hypothesis generation."""
    context = [
        KnowledgeEntity(
            id=uuid.uuid4(),
            content_type=ContentType.TEXT,
            content="Test content",
            version=1,
            confidence=0.9,
            embeddings={},
            metadata={},
            relations=[]
        )
    ]
    
    hypotheses = await engine._generate_hypotheses(
        query="Test query",
        context=context,
        max_hypotheses=3
    )
    
    assert len(hypotheses) == 3
    for hypothesis in hypotheses:
        assert isinstance(hypothesis, Hypothesis)
        assert hypothesis.statement
        assert hypothesis.confidence > 0


@pytest.mark.asyncio
async def test_hypothesis_validation(engine):
    """Test hypothesis validation."""
    hypothesis = create_test_hypothesis()
    context = [
        KnowledgeEntity(
            id=uuid.uuid4(),
            content_type=ContentType.TEXT,
            content="Test content",
            version=1,
            confidence=0.9,
            embeddings={},
            metadata={},
            relations=[]
        )
    ]
    
    result = await engine._validate_hypothesis(
        hypothesis,
        context
    )
    
    assert isinstance(result, ValidationResult)
    assert isinstance(result.is_valid, bool)
    assert 0 <= result.confidence <= 1


@pytest.mark.asyncio
async def test_knowledge_synthesis(engine):
    """Test knowledge synthesis."""
    hypotheses = [create_test_hypothesis() for _ in range(3)]
    validations = [
        ValidationResult(
            hypothesis=h,
            is_valid=True,
            confidence=0.8,
            contradictions=[],
            supporting_evidence=["Evidence"],
            validation_method="test",
            timestamp=datetime.utcnow()
        )
        for h in hypotheses
    ]
    context = [
        KnowledgeEntity(
            id=uuid.uuid4(),
            content_type=ContentType.TEXT,
            content="Test content",
            version=1,
            confidence=0.9,
            embeddings={},
            metadata={},
            relations=[]
        )
    ]
    
    synthesis = await engine._synthesize_knowledge(
        query="Test query",
        hypotheses=hypotheses,
        validations=validations,
        context=context
    )
    
    assert isinstance(synthesis, KnowledgeSynthesis)
    assert synthesis.statement
    assert synthesis.confidence > 0
    assert len(synthesis.source_hypotheses) > 0


@pytest.mark.asyncio
async def test_multimodal_reasoning(engine):
    """Test reasoning with multiple modalities."""
    # Create multimodal context
    context = [
        KnowledgeEntity(
            id=uuid.uuid4(),
            content_type=ContentType.TEXT,
            content="Text description",
            version=1,
            confidence=0.9,
            embeddings={},
            metadata={},
            relations=[]
        ),
        KnowledgeEntity(
            id=uuid.uuid4(),
            content_type=ContentType.IMAGE,
            content=Image.new('RGB', (224, 224), color='red'),
            version=1,
            confidence=0.9,
            embeddings={},
            metadata={},
            relations=[]
        ),
        KnowledgeEntity(
            id=uuid.uuid4(),
            content_type=ContentType.AUDIO,
            content=np.random.randn(16000),  # 1 second of audio
            version=1,
            confidence=0.9,
            embeddings={},
            metadata={},
            relations=[]
        )
    ]
    
    result = await engine.reason(
        query="Analyze all modalities",
        context_entities=context
    )
    
    assert isinstance(result, KnowledgeSynthesis)
    assert any(
        ContentType.TEXT in h.modalities
        for h in result.source_hypotheses
    )
    assert any(
        ContentType.IMAGE in h.modalities
        for h in result.source_hypotheses
    )
    assert any(
        ContentType.AUDIO in h.modalities
        for h in result.source_hypotheses
    )


@pytest.mark.asyncio
async def test_uncertain_synthesis(engine):
    """Test synthesis with uncertain hypotheses."""
    hypotheses = [create_test_hypothesis() for _ in range(3)]
    validations = [
        ValidationResult(
            hypothesis=h,
            is_valid=False,  # All hypotheses invalid
            confidence=0.3,
            contradictions=["Contradiction"],
            supporting_evidence=[],
            validation_method="test",
            timestamp=datetime.utcnow()
        )
        for h in hypotheses
    ]
    context = [
        KnowledgeEntity(
            id=uuid.uuid4(),
            content_type=ContentType.TEXT,
            content="Test content",
            version=1,
            confidence=0.9,
            embeddings={},
            metadata={},
            relations=[]
        )
    ]
    
    synthesis = await engine._synthesize_knowledge(
        query="Test query",
        hypotheses=hypotheses,
        validations=validations,
        context=context
    )
    
    assert isinstance(synthesis, KnowledgeSynthesis)
    assert synthesis.confidence < 0.5  # Low confidence
    assert "uncertain" in synthesis.statement.lower()
    assert synthesis.metadata.get("reason") == "no_valid_hypotheses"


@pytest.mark.asyncio
async def test_temporal_context(engine):
    """Test temporal context handling."""
    # Create hypotheses with different timestamps
    now = datetime.utcnow()
    hypotheses = [
        Hypothesis(
            statement=f"Hypothesis {i}",
            confidence=0.8,
            evidence=["Evidence"],
            source_entities=[str(uuid.uuid4())],
            modalities=[ContentType.TEXT],
            timestamp=now + timedelta(hours=i),
            metadata={}
        )
        for i in range(3)
    ]
    
    temporal_context = engine._get_temporal_context(hypotheses)
    
    assert isinstance(temporal_context, tuple)
    assert len(temporal_context) == 2
    start, end = temporal_context
    assert start == now
    assert end == now + timedelta(hours=2)
