"""
Knowledge base models.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
import uuid
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict


class ContentType(str, Enum):
    """Content type enum."""
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    STRUCTURED = "structured"


class RelationType(str, Enum):
    """Relation type enum."""
    IS_A = "is_a"
    PART_OF = "part_of"
    RELATED_TO = "related_to"
    DERIVED_FROM = "derived_from"
    CONTRADICTS = "contradicts"
    SUPPORTS = "supports"
    TEMPORAL = "temporal"
    CAUSAL = "causal"


class Relation(BaseModel):
    """Represents relationships between knowledge entities."""
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    relation_type: RelationType
    target_id: str
    confidence: float = Field(ge=0.0, le=1.0)
    metadata: Dict[str, Any] = {}
    temporal_context: Optional[Dict[str, datetime]] = None


class ContentMetadata(BaseModel):
    """Content metadata."""
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    language: Optional[str] = None
    format: Optional[str] = None
    size: Optional[int] = None
    duration: Optional[float] = None
    resolution: Optional[Dict[str, int]] = None
    encoding: Optional[str] = None
    additional: Dict[str, Any] = {}
    source: str
    source_url: Optional[str] = None
    timestamp: datetime
    authors: Optional[List[str]] = None
    license: Optional[str] = None
    tags: List[str] = []
    custom: Dict[str, Any] = {}


class KnowledgeEntity(BaseModel):
    """Knowledge entity."""
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    content: Any
    content_type: ContentType
    metadata: ContentMetadata
    relations: List[Relation] = []
    embeddings: Dict[str, List[float]] = {}
    confidence: float = Field(ge=0.0, le=1.0)
    source: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    version: int = 1
    tags: List[str] = []

    def add_relation(self, relation_type: RelationType, target_id: str, confidence: float = 1.0):
        """Add a new relation to the entity."""
        relation = Relation(
            relation_type=relation_type,
            target_id=target_id,
            confidence=confidence
        )
        self.relations.append(relation)

    def update_embedding(self, model_name: str, embedding: List[float]):
        """Update or add an embedding vector for a specific model."""
        self.embeddings[model_name] = embedding

    def to_dict(self) -> dict:
        """Convert the entity to a dictionary format suitable for storage."""
        return self.dict(exclude_none=True)
