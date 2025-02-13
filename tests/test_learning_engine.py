"""
Tests for the self-learning engine.
"""

import pytest
import torch
import numpy as np
from datetime import datetime, timedelta
import uuid
import asyncio
from pathlib import Path
import tempfile
import shutil

from core_system.knowledge_base.models import KnowledgeEntity, ContentType
from core_system.knowledge_base.storage.base import HybridStore
from core_system.reasoning.engine import ReasoningEngine
from core_system.multimodal_processor.alignment import CrossModalAlignment
from core_system.learning.engine import (
    SelfLearningEngine,
    KnowledgeGap,
    ResearchResult,
    ConsolidationMetrics
)


@pytest.fixture
def temp_model_dir():
    """Temporary directory for model files."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def mock_store(mocker):
    """Mock hybrid store."""
    store = mocker.Mock(spec=HybridStore)
    store.vector_store = mocker.Mock()
    store.graph_store = mocker.Mock()
    return store


@pytest.fixture
def mock_reasoning(mocker):
    """Mock reasoning engine."""
    engine = mocker.Mock(spec=ReasoningEngine)
    return engine


@pytest.fixture
def mock_alignment(mocker):
    """Mock cross-modal alignment."""
    alignment = mocker.Mock(spec=CrossModalAlignment)
    return alignment


@pytest.fixture
def learning_engine(
    mock_store,
    mock_reasoning,
    mock_alignment,
    temp_model_dir
):
    """Self-learning engine instance."""
    return SelfLearningEngine(
        store=mock_store,
        reasoning_engine=mock_reasoning,
        alignment=mock_alignment,
        model_dir=temp_model_dir
    )


def create_test_gap() -> KnowledgeGap:
    """Create a test knowledge gap."""
    return KnowledgeGap(
        topic="test_topic",
        description="Test gap description",
        importance=0.8,
        modalities=[ContentType.TEXT],
        related_entities=[str(uuid.uuid4())],
        detection_method="test",
        detection_confidence=0.9,
        timestamp=datetime.utcnow(),
        metadata={}
    )


def create_test_result(gap: KnowledgeGap) -> ResearchResult:
    """Create a test research result."""
    return ResearchResult(
        gap=gap,
        findings=[{
            "content": "Test finding",
            "confidence": 0.8,
            "source": "test"
        }],
        confidence=0.8,
        source_urls=["http://test.com"],
        processing_time=1.0,
        validation_score=0.9,
        metadata={}
    )


@pytest.mark.asyncio
async def test_learning_loop_startup(learning_engine, mocker):
    """Test learning loop initialization."""
    # Mock methods
    mocker.patch.object(
        learning_engine,
        '_detect_gaps',
        return_value=[create_test_gap()]
    )
    mocker.patch.object(
        learning_engine,
        '_research_gap',
        return_value=create_test_result(create_test_gap())
    )
    mocker.patch.object(
        learning_engine,
        '_integrate_findings',
        return_value=None
    )
    
    # Start loop and run briefly
    task = asyncio.create_task(learning_engine.start_learning_loop())
    await asyncio.sleep(0.1)
    task.cancel()
    
    try:
        await task
    except asyncio.CancelledError:
        pass
    
    # Verify methods were called
    learning_engine._detect_gaps.assert_called_once()
    learning_engine._research_gap.assert_called_once()
    learning_engine._integrate_findings.assert_called_once()


@pytest.mark.asyncio
async def test_gap_detection(learning_engine):
    """Test knowledge gap detection."""
    gaps = await learning_engine._detect_gaps()
    
    assert isinstance(gaps, list)
    for gap in gaps:
        assert isinstance(gap, KnowledgeGap)
        assert 0 <= gap.importance <= 1
        assert 0 <= gap.detection_confidence <= 1


@pytest.mark.asyncio
async def test_gap_prioritization(learning_engine):
    """Test gap prioritization."""
    gaps = [
        KnowledgeGap(
            topic=f"topic_{i}",
            description=f"Gap {i}",
            importance=0.5 + i/10,
            modalities=[ContentType.TEXT],
            related_entities=[],
            detection_method="test",
            detection_confidence=0.8,
            timestamp=datetime.utcnow() - timedelta(hours=i),
            metadata={}
        )
        for i in range(5)
    ]
    
    prioritized = learning_engine._prioritize_gaps(gaps)
    
    assert len(prioritized) == len(gaps)
    assert prioritized[0].importance > prioritized[-1].importance


@pytest.mark.asyncio
async def test_research_execution(learning_engine, mocker):
    """Test research execution for a gap."""
    gap = create_test_gap()
    
    # Mock research methods
    mocker.patch.object(
        learning_engine,
        '_plan_research',
        return_value=[("web", "test query")]
    )
    mocker.patch.object(
        learning_engine,
        '_web_research',
        return_value={
            "findings": [{"content": "test", "confidence": 0.8}],
            "sources": ["http://test.com"]
        }
    )
    
    result = await learning_engine._research_gap(gap)
    
    assert isinstance(result, ResearchResult)
    assert result.gap == gap
    assert len(result.findings) > 0
    assert result.confidence > 0
    assert len(result.source_urls) > 0


@pytest.mark.asyncio
async def test_knowledge_integration(learning_engine, mocker):
    """Test integration of research findings."""
    gap = create_test_gap()
    result = create_test_result(gap)
    
    # Mock entity creation
    mock_entity = KnowledgeEntity(
        id=uuid.uuid4(),
        content_type=ContentType.TEXT,
        content="Test content",
        version=1,
        confidence=0.9,
        embeddings={},
        metadata={},
        relations=[]
    )
    
    mocker.patch.object(
        learning_engine,
        '_create_entity_from_finding',
        return_value=mock_entity
    )
    
    await learning_engine._integrate_findings([result])
    
    # Verify store updates
    learning_engine.store.add_entities.assert_called_once()


@pytest.mark.asyncio
async def test_knowledge_consolidation(learning_engine):
    """Test knowledge consolidation process."""
    metrics = await learning_engine._consolidate_knowledge()
    
    assert isinstance(metrics, ConsolidationMetrics)
    assert 0 <= metrics.consistency_score <= 1
    assert metrics.training_time > 0


@pytest.mark.asyncio
async def test_concurrent_research(learning_engine, mocker):
    """Test concurrent research tasks."""
    gaps = [create_test_gap() for _ in range(3)]
    
    # Mock research to take different times
    async def mock_research(gap):
        await asyncio.sleep(0.1 * gaps.index(gap))
        return create_test_result(gap)
    
    mocker.patch.object(learning_engine, '_research_gap', side_effect=mock_research)
    
    # Start concurrent research
    tasks = [
        learning_engine._research_gap(gap)
        for gap in gaps
    ]
    
    results = await asyncio.gather(*tasks)
    
    assert len(results) == len(gaps)
    for result in results:
        assert isinstance(result, ResearchResult)


@pytest.mark.asyncio
async def test_error_handling(learning_engine, mocker):
    """Test error handling in learning process."""
    gap = create_test_gap()
    
    # Mock research to raise error
    mocker.patch.object(
        learning_engine,
        '_research_gap',
        side_effect=Exception("Test error")
    )
    
    # Should handle error without crashing
    task = asyncio.create_task(learning_engine.start_learning_loop())
    await asyncio.sleep(0.1)
    task.cancel()
    
    try:
        await task
    except asyncio.CancelledError:
        pass


@pytest.mark.asyncio
async def test_gap_detector_model(learning_engine):
    """Test gap detector neural network."""
    # Create random embedding
    embedding = torch.randn(1, 512).to(learning_engine.device)
    
    # Get gap score
    score = learning_engine.gap_detector(embedding)
    
    assert isinstance(score, torch.Tensor)
    assert 0 <= score.item() <= 1


@pytest.mark.asyncio
async def test_findings_cache(learning_engine):
    """Test findings cache mechanism."""
    gap = create_test_gap()
    result = create_test_result(gap)
    
    # Add to cache
    learning_engine._findings_cache[gap.topic] = result
    
    # Verify cache
    assert gap.topic in learning_engine._findings_cache
    assert learning_engine._findings_cache[gap.topic] == result
