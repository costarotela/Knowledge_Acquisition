"""
Pipeline processor implementation.
"""
from typing import Dict, Any, List, Optional, Union
import logging
import asyncio
from datetime import datetime
import time
import cachetools

from .schemas import (
    DataType, ProcessingStage, ProcessingPriority,
    ValidationResult, DataTransformation, ProcessingMetadata,
    ProcessedData, PipelineConfig, PipelineState, ProcessingNode
)
from ..integration.agent_coordinator import AgentCoordinator
from ...config.schemas import SystemConfig

logger = logging.getLogger(__name__)

class PipelineProcessor:
    """Processes data through configured pipeline stages."""
    
    def __init__(
        self,
        config: SystemConfig,
        coordinator: AgentCoordinator
    ):
        """Initialize pipeline processor."""
        self.config = config
        self.coordinator = coordinator
        
        # Pipeline configurations
        self.pipelines: Dict[str, PipelineConfig] = {}
        self.pipeline_states: Dict[str, PipelineState] = {}
        
        # Cache setup
        self.cache = cachetools.TTLCache(
            maxsize=1000,
            ttl=3600
        )
    
    async def register_pipeline(
        self,
        pipeline: PipelineConfig
    ) -> bool:
        """Register a new processing pipeline."""
        try:
            if pipeline.pipeline_id in self.pipelines:
                logger.warning(f"Pipeline {pipeline.pipeline_id} already exists")
                return False
            
            # Validate agent availability
            for node in pipeline.nodes:
                for agent_id in node.agent_ids:
                    if agent_id not in self.coordinator.agents:
                        raise ValueError(f"Agent {agent_id} not found")
            
            self.pipelines[pipeline.pipeline_id] = pipeline
            logger.info(f"Registered pipeline {pipeline.pipeline_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error registering pipeline: {e}")
            return False
    
    async def process_data(
        self,
        pipeline_id: str,
        input_data: Union[str, Dict[str, Any], List[Any]],
        data_type: DataType,
        priority: ProcessingPriority = ProcessingPriority.MEDIUM
    ) -> Optional[List[ProcessedData]]:
        """Process data through pipeline."""
        try:
            pipeline = self.pipelines.get(pipeline_id)
            if not pipeline:
                raise ValueError(f"Pipeline {pipeline_id} not found")
            
            # Initialize pipeline state
            state = PipelineState(
                pipeline_id=pipeline_id,
                start_time=datetime.now(),
                current_stage=ProcessingStage.EXTRACTION
            )
            self.pipeline_states[pipeline_id] = state
            
            # Create initial processed data
            initial_data = ProcessedData(
                data_id=f"{pipeline_id}_{int(time.time())}",
                data_type=data_type,
                content=input_data,
                metadata=ProcessingMetadata(
                    source_id="input",
                    processing_time=0,
                    agent_id="system",
                    stage=ProcessingStage.EXTRACTION
                ),
                confidence=1.0
            )
            
            # Process through pipeline nodes
            current_data = [initial_data]
            for node in pipeline.nodes:
                try:
                    state.current_node = node.node_id
                    state.current_stage = node.stage
                    
                    # Check cache if enabled
                    if node.cache_config and node.cache_config.enabled:
                        cache_key = self._generate_cache_key(
                            node.node_id,
                            current_data
                        )
                        cached_result = self.cache.get(cache_key)
                        if cached_result:
                            current_data = cached_result
                            state.completed_nodes.append(node.node_id)
                            continue
                    
                    # Process node
                    start_time = time.time()
                    processed = await self._process_node(
                        node,
                        current_data,
                        priority
                    )
                    processing_time = time.time() - start_time
                    
                    if not processed:
                        if node.required:
                            raise ValueError(f"Required node {node.node_id} failed")
                        state.failed_nodes.append(node.node_id)
                        continue
                    
                    # Update metadata
                    for data in processed:
                        data.metadata.processing_time = processing_time
                    
                    # Cache results if enabled
                    if node.cache_config and node.cache_config.enabled:
                        self.cache[cache_key] = processed
                    
                    current_data = processed
                    state.completed_nodes.append(node.node_id)
                    state.processed_data.extend(processed)
                    
                except Exception as e:
                    logger.error(f"Error processing node {node.node_id}: {e}")
                    if node.required:
                        raise
                    state.failed_nodes.append(node.node_id)
            
            state.status = "completed"
            return current_data
            
        except Exception as e:
            logger.error(f"Error processing pipeline {pipeline_id}: {e}")
            if pipeline_id in self.pipeline_states:
                state = self.pipeline_states[pipeline_id]
                state.status = "failed"
                state.error = str(e)
            return None
    
    async def _process_node(
        self,
        node: ProcessingNode,
        input_data: List[ProcessedData],
        priority: ProcessingPriority
    ) -> Optional[List[ProcessedData]]:
        """Process data through a single node."""
        try:
            # Validate input types
            for data in input_data:
                if data.data_type not in node.input_types:
                    raise ValueError(
                        f"Invalid input type {data.data_type} "
                        f"for node {node.node_id}"
                    )
            
            # Create tasks for each agent
            tasks = []
            for agent_id in node.agent_ids:
                task = {
                    "id": f"{node.node_id}_{agent_id}_{int(time.time())}",
                    "task_type": node.stage.value,
                    "input_data": {
                        "data": [d.dict() for d in input_data],
                        "node_config": node.dict()
                    },
                    "priority": priority.value
                }
                tasks.append(task)
            
            # Execute tasks in parallel
            results = await asyncio.gather(
                *[
                    self.coordinator.submit_task(task, [agent_id])
                    for task, agent_id in zip(tasks, node.agent_ids)
                ],
                return_exceptions=True
            )
            
            # Process results
            processed_data = []
            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"Task failed: {result}")
                    continue
                
                if not result or not result.success:
                    continue
                
                # Convert results to ProcessedData
                for data_dict in result.data.get("processed_data", []):
                    try:
                        processed = ProcessedData(**data_dict)
                        processed_data.append(processed)
                    except Exception as e:
                        logger.error(f"Error converting result: {e}")
            
            return processed_data if processed_data else None
            
        except Exception as e:
            logger.error(f"Error in node {node.node_id}: {e}")
            return None
    
    def _generate_cache_key(
        self,
        node_id: str,
        data: List[ProcessedData]
    ) -> str:
        """Generate cache key for node and data."""
        # Create deterministic key from node and data
        data_keys = []
        for d in data:
            if isinstance(d.content, (str, int, float, bool)):
                data_keys.append(str(d.content))
            else:
                data_keys.append(d.data_id)
        
        return f"{node_id}_{'-'.join(sorted(data_keys))}"
    
    def get_pipeline_state(
        self,
        pipeline_id: str
    ) -> Optional[PipelineState]:
        """Get current state of pipeline execution."""
        return self.pipeline_states.get(pipeline_id)
    
    def clear_pipeline_state(self, pipeline_id: str):
        """Clear pipeline state."""
        if pipeline_id in self.pipeline_states:
            del self.pipeline_states[pipeline_id]
