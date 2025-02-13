"""
Schemas for pipeline processing system.
"""
from typing import Dict, Any, List, Optional, Union
from enum import Enum
from datetime import datetime
from pydantic import BaseModel, Field, validator

class DataType(str, Enum):
    """Types of data that can be processed."""
    TEXT = "text"
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    CODE = "code"
    STRUCTURED = "structured"
    EMBEDDING = "embedding"

class ProcessingStage(str, Enum):
    """Stages in the processing pipeline."""
    EXTRACTION = "extraction"
    TRANSFORMATION = "transformation"
    VALIDATION = "validation"
    ENRICHMENT = "enrichment"
    STORAGE = "storage"

class ProcessingPriority(str, Enum):
    """Priority levels for processing tasks."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ValidationResult(BaseModel):
    """Result of data validation."""
    is_valid: bool
    confidence: float = Field(ge=0.0, le=1.0)
    issues: List[str] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)

class DataTransformation(BaseModel):
    """Record of data transformation."""
    original_type: DataType
    target_type: DataType
    transformation_method: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    success: bool
    error: Optional[str] = None

class ProcessingMetadata(BaseModel):
    """Metadata for processed data."""
    source_id: str
    timestamp: datetime = Field(default_factory=datetime.now)
    processing_time: float
    agent_id: str
    stage: ProcessingStage
    transformations: List[DataTransformation] = Field(default_factory=list)
    validation_results: List[ValidationResult] = Field(default_factory=list)

class ProcessedData(BaseModel):
    """Container for processed data with metadata."""
    data_id: str
    data_type: DataType
    content: Any
    metadata: ProcessingMetadata
    confidence: float = Field(ge=0.0, le=1.0)
    dependencies: List[str] = Field(default_factory=list)
    
    @validator("content")
    def validate_content_type(cls, v, values):
        """Validate content matches data_type."""
        data_type = values.get("data_type")
        if data_type == DataType.TEXT and not isinstance(v, str):
            raise ValueError("Text data must be string")
        elif data_type == DataType.STRUCTURED and not isinstance(v, (dict, list)):
            raise ValueError("Structured data must be dict or list")
        elif data_type == DataType.EMBEDDING and not isinstance(v, list):
            raise ValueError("Embedding must be list of floats")
        return v

class CacheConfig(BaseModel):
    """Configuration for data caching."""
    enabled: bool = True
    max_size: int = Field(default=1024, description="Max cache size in MB")
    ttl: int = Field(default=3600, description="Time to live in seconds")
    strategy: str = Field(default="lru", description="Cache eviction strategy")

class ProcessingNode(BaseModel):
    """Definition of a processing node in the pipeline."""
    node_id: str
    stage: ProcessingStage
    agent_ids: List[str]
    input_types: List[DataType]
    output_types: List[DataType]
    required: bool = True
    timeout: int = Field(default=300)
    retry_policy: Dict[str, Any] = Field(default_factory=dict)
    cache_config: Optional[CacheConfig] = None

class PipelineConfig(BaseModel):
    """Configuration for a processing pipeline."""
    pipeline_id: str
    description: str
    nodes: List[ProcessingNode]
    max_parallel_nodes: int = Field(default=4)
    timeout: int = Field(default=3600)
    error_handling: Dict[str, Any] = Field(default_factory=dict)
    
    @validator("nodes")
    def validate_node_sequence(cls, v):
        """Validate node sequence is valid."""
        if not v:
            raise ValueError("Pipeline must have at least one node")
        
        # Check stage sequence
        stages = [node.stage for node in v]
        required_stages = {
            ProcessingStage.EXTRACTION,
            ProcessingStage.VALIDATION,
            ProcessingStage.STORAGE
        }
        
        if not all(stage in stages for stage in required_stages):
            raise ValueError(f"Pipeline must include stages: {required_stages}")
        
        return v

class PipelineState(BaseModel):
    """Current state of a pipeline execution."""
    pipeline_id: str
    start_time: datetime
    current_stage: ProcessingStage
    completed_nodes: List[str] = Field(default_factory=list)
    failed_nodes: List[str] = Field(default_factory=list)
    processed_data: List[ProcessedData] = Field(default_factory=list)
    current_node: Optional[str] = None
    status: str = "running"
    error: Optional[str] = None
