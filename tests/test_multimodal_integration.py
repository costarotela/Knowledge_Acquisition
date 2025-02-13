"""
Tests for multimodal integration system.
"""

import pytest
import torch
import numpy as np
from pathlib import Path
import tempfile
import shutil
from PIL import Image
from datetime import datetime, timedelta
import uuid

from core_system.knowledge_base.models import KnowledgeEntity, ContentType
from core_system.knowledge_base.storage.base import HybridStore
from core_system.multimodal_processor.alignment import CrossModalAlignment
from core_system.multimodal_processor.integrator import MultimodalIntegrator
from core_system.multimodal_processor.utils import (
    process_audio,
    process_image,
    save_embeddings,
    load_embeddings
)


@pytest.fixture
def temp_cache_dir():
    """Temporary directory for cache."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def alignment():
    """CrossModalAlignment instance."""
    return CrossModalAlignment()


@pytest.fixture
def store(mocker):
    """Mock hybrid store."""
    mock_store = mocker.Mock(spec=HybridStore)
    mock_store.vector_store = mocker.Mock()
    mock_store.graph_store = mocker.Mock()
    return mock_store


@pytest.fixture
def integrator(store, alignment, temp_cache_dir):
    """MultimodalIntegrator instance."""
    return MultimodalIntegrator(
        store=store,
        alignment=alignment,
        cache_dir=temp_cache_dir
    )


def create_test_entity(content_type: ContentType):
    """Create a test knowledge entity."""
    return KnowledgeEntity(
        id=uuid.uuid4(),
        content_type=content_type,
        content="test content",
        version=1,
        confidence=0.9,
        embeddings={},
        metadata={},
        relations=[]
    )


@pytest.mark.asyncio
async def test_process_text_entity(integrator):
    """Test processing of text entity."""
    entity = create_test_entity(ContentType.TEXT)
    entity.content = "This is a test text."
    
    processed = await integrator.process_entity(entity)
    
    assert "aligned" in processed.embeddings
    assert isinstance(processed.embeddings["aligned"], torch.Tensor)
    assert processed.embeddings["aligned"].shape[-1] == 512  # CLIP dimension


@pytest.mark.asyncio
async def test_process_image_entity(integrator):
    """Test processing of image entity."""
    # Create test image
    img = Image.new('RGB', (224, 224), color='red')
    
    entity = create_test_entity(ContentType.IMAGE)
    entity.content = img
    
    processed = await integrator.process_entity(entity)
    
    assert "aligned" in processed.embeddings
    assert isinstance(processed.embeddings["aligned"], torch.Tensor)
    assert processed.embeddings["aligned"].shape[-1] == 512


@pytest.mark.asyncio
async def test_process_audio_entity(integrator):
    """Test processing of audio entity."""
    # Create test audio
    audio = np.random.randn(16000)  # 1 second of random audio
    
    entity = create_test_entity(ContentType.AUDIO)
    entity.content = audio
    
    processed = await integrator.process_entity(entity)
    
    assert "aligned" in processed.embeddings
    assert isinstance(processed.embeddings["aligned"], torch.Tensor)
    assert processed.embeddings["aligned"].shape[-1] == 512


@pytest.mark.asyncio
async def test_batch_processing(integrator):
    """Test batch processing of entities."""
    entities = [
        create_test_entity(ContentType.TEXT)
        for _ in range(5)
    ]
    
    processed = await integrator.batch_process(entities)
    
    assert len(processed) == 5
    for entity in processed:
        assert "aligned" in entity.embeddings


@pytest.mark.asyncio
async def test_caching(integrator, temp_cache_dir):
    """Test embedding caching."""
    entity = create_test_entity(ContentType.TEXT)
    
    # First processing
    processed1 = await integrator.process_entity(entity)
    embedding1 = processed1.embeddings["aligned"]
    
    # Second processing (should use cache)
    processed2 = await integrator.process_entity(entity)
    embedding2 = processed2.embeddings["aligned"]
    
    assert torch.equal(embedding1, embedding2)
    
    # Check cache file exists
    cache_files = list(Path(temp_cache_dir).glob("*.npz"))
    assert len(cache_files) == 1


@pytest.mark.asyncio
async def test_force_recompute(integrator):
    """Test force recomputation of embeddings."""
    entity = create_test_entity(ContentType.TEXT)
    
    # First processing
    processed1 = await integrator.process_entity(entity)
    embedding1 = processed1.embeddings["aligned"]
    
    # Force recompute
    processed2 = await integrator.process_entity(
        entity,
        force_recompute=True
    )
    embedding2 = processed2.embeddings["aligned"]
    
    # Should be different due to randomness in neural networks
    assert not torch.equal(embedding1, embedding2)


@pytest.mark.asyncio
async def test_clear_cache(integrator, temp_cache_dir):
    """Test cache clearing."""
    entity = create_test_entity(ContentType.TEXT)
    await integrator.process_entity(entity)
    
    # Clear cache
    integrator.clear_cache()
    
    # Check cache is empty
    assert len(list(Path(temp_cache_dir).glob("*.npz"))) == 0
    assert len(integrator._embedding_cache) == 0


@pytest.mark.asyncio
async def test_clear_cache_with_date(integrator, temp_cache_dir):
    """Test selective cache clearing based on date."""
    entity = create_test_entity(ContentType.TEXT)
    await integrator.process_entity(entity)
    
    # Clear cache older than future date
    future_date = datetime.utcnow() + timedelta(days=1)
    integrator.clear_cache(older_than=future_date)
    
    # Cache should be empty
    assert len(list(Path(temp_cache_dir).glob("*.npz"))) == 0
    
    # Clear cache older than past date
    past_date = datetime.utcnow() - timedelta(days=1)
    await integrator.process_entity(entity)
    integrator.clear_cache(older_than=past_date)
    
    # Cache should still have the recent entry
    assert len(list(Path(temp_cache_dir).glob("*.npz"))) == 1


@pytest.mark.asyncio
async def test_update_store(integrator, store):
    """Test store updates."""
    entities = [
        create_test_entity(ContentType.TEXT)
        for _ in range(3)
    ]
    
    await integrator.update_store(entities)
    
    # Check vector store update
    store.vector_store.add_entities.assert_called_once_with(entities)
    
    # Check graph store updates
    store.graph_store.add_entities.assert_called_once_with(entities)
    
    # No relations in test entities
    store.graph_store.add_relations.assert_not_called()
