"""
Base interfaces for the hybrid storage system.
Defines the contract that specific implementations must follow.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from uuid import UUID

from ..models import KnowledgeEntity, Relation


class VectorStore(ABC):
    """Abstract base class for vector storage implementations."""
    
    @abstractmethod
    async def add_entity(self, entity: KnowledgeEntity) -> bool:
        """Add a new entity to the vector store."""
        pass
    
    @abstractmethod
    async def get_entity(self, entity_id: UUID) -> Optional[KnowledgeEntity]:
        """Retrieve an entity by its ID."""
        pass
    
    @abstractmethod
    async def search_similar(
        self, 
        query_vector: List[float], 
        limit: int = 10,
        filter_dict: Optional[Dict[str, Any]] = None
    ) -> List[KnowledgeEntity]:
        """Search for similar entities using a query vector."""
        pass
    
    @abstractmethod
    async def update_entity(self, entity: KnowledgeEntity) -> bool:
        """Update an existing entity."""
        pass
    
    @abstractmethod
    async def delete_entity(self, entity_id: UUID) -> bool:
        """Delete an entity from the store."""
        pass


class GraphStore(ABC):
    """Abstract base class for graph storage implementations."""
    
    @abstractmethod
    async def add_entity(self, entity: KnowledgeEntity) -> bool:
        """Add a new entity node to the graph."""
        pass
    
    @abstractmethod
    async def add_relation(self, source_id: UUID, relation: Relation) -> bool:
        """Add a new relation between entities."""
        pass
    
    @abstractmethod
    async def get_entity(self, entity_id: UUID) -> Optional[KnowledgeEntity]:
        """Retrieve an entity node by its ID."""
        pass
    
    @abstractmethod
    async def get_relations(
        self, 
        entity_id: UUID,
        relation_types: Optional[List[str]] = None
    ) -> List[Relation]:
        """Get all relations for an entity."""
        pass
    
    @abstractmethod
    async def search_path(
        self,
        start_id: UUID,
        end_id: UUID,
        max_depth: int = 3
    ) -> List[List[Relation]]:
        """Find paths between two entities."""
        pass
    
    @abstractmethod
    async def update_entity(self, entity: KnowledgeEntity) -> bool:
        """Update an existing entity node."""
        pass
    
    @abstractmethod
    async def delete_entity(self, entity_id: UUID) -> bool:
        """Delete an entity and its relations."""
        pass


class HybridStore:
    """Coordinates operations between vector and graph stores."""
    
    def __init__(
        self,
        vector_store: VectorStore,
        graph_store: GraphStore
    ):
        self.vector_store = vector_store
        self.graph_store = graph_store
    
    async def add_entity(self, entity: KnowledgeEntity) -> bool:
        """Add entity to both stores atomically."""
        try:
            vector_success = await self.vector_store.add_entity(entity)
            if not vector_success:
                return False
            
            graph_success = await self.graph_store.add_entity(entity)
            if not graph_success:
                # Rollback vector store
                await self.vector_store.delete_entity(entity.id)
                return False
            
            # Add relations
            for relation in entity.relations:
                await self.graph_store.add_relation(entity.id, relation)
            
            return True
        except Exception as e:
            # Log error and rollback
            print(f"Error adding entity: {e}")
            await self.vector_store.delete_entity(entity.id)
            await self.graph_store.delete_entity(entity.id)
            return False
    
    async def get_entity(self, entity_id: UUID) -> Optional[KnowledgeEntity]:
        """Get entity with its relations."""
        entity = await self.vector_store.get_entity(entity_id)
        if not entity:
            return None
        
        # Enrich with relations
        relations = await self.graph_store.get_relations(entity_id)
        entity.relations = relations
        return entity
    
    async def search_knowledge(
        self,
        query_vector: List[float],
        limit: int = 10,
        max_path_depth: int = 2
    ) -> Dict[str, Any]:
        """
        Perform a hybrid search using both vector similarity and graph relations.
        Returns both similar entities and their relationships.
        """
        # Get similar entities
        similar = await self.vector_store.search_similar(query_vector, limit)
        
        # Enrich with graph information
        result = {
            "direct_matches": similar,
            "related_entities": [],
            "paths": []
        }
        
        # Find connections between similar entities
        for i, entity1 in enumerate(similar):
            for entity2 in similar[i+1:]:
                paths = await self.graph_store.search_path(
                    entity1.id,
                    entity2.id,
                    max_depth=max_path_depth
                )
                if paths:
                    result["paths"].extend(paths)
        
        return result
