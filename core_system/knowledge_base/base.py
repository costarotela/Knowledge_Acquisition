"""
Base classes for the unified knowledge base system.
"""
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class KnowledgeFragment(BaseModel):
    """A fragment of knowledge with its metadata."""
    content: str
    source_type: str
    confidence_score: float = 0.0
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)

class KnowledgeItem(BaseModel):
    """Complete knowledge item with all metadata."""
    id: Optional[str] = None
    content: str
    source_url: str
    source_type: str
    fragments: List[KnowledgeFragment] = Field(default_factory=list)
    topics: List[str] = Field(default_factory=list)
    relations: List[Dict[str, str]] = Field(default_factory=list)
    confidence_score: float = 0.0
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None

class KnowledgeQuery(BaseModel):
    """Query parameters for knowledge search."""
    query: str
    topics: Optional[List[str]] = None
    source_types: Optional[List[str]] = None
    min_confidence: float = 0.0
    max_results: int = 10
    include_metadata: bool = True

class BaseKnowledgeStore(ABC):
    """Abstract base class for knowledge storage implementations."""
    
    @abstractmethod
    async def store_item(self, item: KnowledgeItem) -> str:
        """Store a knowledge item."""
        pass
    
    @abstractmethod
    async def get_item(self, item_id: str) -> Optional[KnowledgeItem]:
        """Retrieve a knowledge item by ID."""
        pass
    
    @abstractmethod
    async def search(self, query: KnowledgeQuery) -> List[KnowledgeItem]:
        """Search for knowledge items."""
        pass
    
    @abstractmethod
    async def update_item(self, item_id: str, updates: Dict[str, Any]) -> bool:
        """Update a knowledge item."""
        pass
    
    @abstractmethod
    async def delete_item(self, item_id: str) -> bool:
        """Delete a knowledge item."""
        pass

class BaseKnowledgeGraph(ABC):
    """Abstract base class for knowledge graph implementations."""
    
    @abstractmethod
    async def add_concept(self, concept: str, properties: Dict[str, Any]) -> str:
        """Add a concept node to the graph."""
        pass
    
    @abstractmethod
    async def add_relation(self, from_concept: str, to_concept: str, relation_type: str, properties: Dict[str, Any]) -> str:
        """Add a relation between concepts."""
        pass
    
    @abstractmethod
    async def get_related_concepts(self, concept: str, relation_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get concepts related to the given concept."""
        pass
    
    @abstractmethod
    async def search_concepts(self, query: str) -> List[Dict[str, Any]]:
        """Search for concepts in the graph."""
        pass
