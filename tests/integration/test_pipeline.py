"""
Integration tests for pipeline processing.
"""
import pytest
import asyncio
from datetime import datetime

from core_system.pipeline.processor import PipelineProcessor
from core_system.pipeline.schemas import (
    DataType, ProcessingStage, ProcessingPriority,
    ProcessingNode, PipelineConfig, CacheConfig
)
from core_system.integration.agent_coordinator import AgentCoordinator
from config.schemas import SystemConfig

@pytest.fixture
def system_config():
    """Create system configuration for testing."""
    return SystemConfig(
        api={
            "openai_api_key": "test_key"
        },
        storage={
            "vector_store_path": "/tmp/test_vector_store",
            "knowledge_base_path": "/tmp/test_kb",
            "cache_dir": "/tmp/test_cache"
        },
        processing={
            "batch_size": 32,
            "max_workers": 4
        },
        monitoring={
            "log_level": "INFO",
            "log_file": "test.log"
        }
    )

@pytest.fixture
def coordinator(system_config):
    """Create agent coordinator for testing."""
    return AgentCoordinator(system_config)

@pytest.fixture
def pipeline_processor(system_config, coordinator):
    """Create pipeline processor for testing."""
    return PipelineProcessor(system_config, coordinator)

@pytest.fixture
def test_pipeline():
    """Create test pipeline configuration."""
    return PipelineConfig(
        pipeline_id="test_pipeline",
        description="Test pipeline",
        nodes=[
            ProcessingNode(
                node_id="extraction",
                stage=ProcessingStage.EXTRACTION,
                agent_ids=["youtube_main"],
                input_types=[DataType.VIDEO],
                output_types=[DataType.TEXT, DataType.AUDIO],
                cache_config=CacheConfig(
                    enabled=True,
                    max_size=100
                )
            ),
            ProcessingNode(
                node_id="validation",
                stage=ProcessingStage.VALIDATION,
                agent_ids=["rag_main"],
                input_types=[DataType.TEXT],
                output_types=[DataType.TEXT],
                required=True
            ),
            ProcessingNode(
                node_id="storage",
                stage=ProcessingStage.STORAGE,
                agent_ids=["rag_main"],
                input_types=[DataType.TEXT],
                output_types=[DataType.STRUCTURED],
                required=True
            )
        ],
        max_parallel_nodes=2
    )

@pytest.mark.asyncio
async def test_pipeline_registration(pipeline_processor, test_pipeline):
    """Test pipeline registration."""
    # Register pipeline
    success = await pipeline_processor.register_pipeline(test_pipeline)
    assert success
    
    # Verify pipeline is registered
    assert test_pipeline.pipeline_id in pipeline_processor.pipelines

@pytest.mark.asyncio
async def test_data_processing(pipeline_processor, test_pipeline, coordinator):
    """Test complete data processing flow."""
    # Register pipeline
    await pipeline_processor.register_pipeline(test_pipeline)
    
    # Create test data
    test_data = "test video content"
    
    # Process data
    result = await pipeline_processor.process_data(
        pipeline_id=test_pipeline.pipeline_id,
        input_data=test_data,
        data_type=DataType.VIDEO,
        priority=ProcessingPriority.HIGH
    )
    
    # Verify results
    assert result is not None
    assert len(result) > 0
    
    # Check pipeline state
    state = pipeline_processor.get_pipeline_state(test_pipeline.pipeline_id)
    assert state is not None
    assert state.status == "completed"
    assert len(state.completed_nodes) == len(test_pipeline.nodes)

@pytest.mark.asyncio
async def test_cache_functionality(pipeline_processor, test_pipeline):
    """Test pipeline cache functionality."""
    # Register pipeline
    await pipeline_processor.register_pipeline(test_pipeline)
    
    # Process same data twice
    test_data = "test video content"
    
    # First processing
    start_time = datetime.now()
    result1 = await pipeline_processor.process_data(
        pipeline_id=test_pipeline.pipeline_id,
        input_data=test_data,
        data_type=DataType.VIDEO
    )
    first_duration = (datetime.now() - start_time).total_seconds()
    
    # Second processing
    start_time = datetime.now()
    result2 = await pipeline_processor.process_data(
        pipeline_id=test_pipeline.pipeline_id,
        input_data=test_data,
        data_type=DataType.VIDEO
    )
    second_duration = (datetime.now() - start_time).total_seconds()
    
    # Verify cache effectiveness
    assert second_duration < first_duration
    assert result1 == result2

@pytest.mark.asyncio
async def test_error_handling(pipeline_processor, test_pipeline):
    """Test pipeline error handling."""
    # Register pipeline
    await pipeline_processor.register_pipeline(test_pipeline)
    
    # Process invalid data
    result = await pipeline_processor.process_data(
        pipeline_id=test_pipeline.pipeline_id,
        input_data="invalid data",
        data_type=DataType.IMAGE  # Pipeline doesn't support images
    )
    
    # Verify error handling
    assert result is None
    
    # Check pipeline state
    state = pipeline_processor.get_pipeline_state(test_pipeline.pipeline_id)
    assert state is not None
    assert state.status == "failed"
    assert state.error is not None

@pytest.mark.asyncio
async def test_parallel_processing(pipeline_processor, test_pipeline):
    """Test parallel processing capabilities."""
    # Register pipeline
    await pipeline_processor.register_pipeline(test_pipeline)
    
    # Process multiple items in parallel
    test_data = ["video1", "video2", "video3"]
    
    # Start all processing tasks
    tasks = [
        pipeline_processor.process_data(
            pipeline_id=test_pipeline.pipeline_id,
            input_data=data,
            data_type=DataType.VIDEO
        )
        for data in test_data
    ]
    
    # Wait for all tasks to complete
    results = await asyncio.gather(*tasks)
    
    # Verify results
    assert len(results) == len(test_data)
    assert all(result is not None for result in results)

@pytest.mark.asyncio
async def test_priority_processing(pipeline_processor, test_pipeline):
    """Test priority-based processing."""
    # Register pipeline
    await pipeline_processor.register_pipeline(test_pipeline)
    
    # Process items with different priorities
    low_priority = pipeline_processor.process_data(
        pipeline_id=test_pipeline.pipeline_id,
        input_data="low priority data",
        data_type=DataType.VIDEO,
        priority=ProcessingPriority.LOW
    )
    
    high_priority = pipeline_processor.process_data(
        pipeline_id=test_pipeline.pipeline_id,
        input_data="high priority data",
        data_type=DataType.VIDEO,
        priority=ProcessingPriority.HIGH
    )
    
    # Wait for both to complete
    results = await asyncio.gather(low_priority, high_priority)
    
    # Verify both completed successfully
    assert all(result is not None for result in results)
