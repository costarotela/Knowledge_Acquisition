"""
ChromaDB implementation of the vector store.
Provides efficient similarity search and vector storage.
"""

import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions
from typing import List, Optional, Dict, Any
from uuid import UUID
import json

from .base import VectorStore
from ..models import KnowledgeEntity


class ChromaStore(VectorStore):
    """ChromaDB-based vector store implementation."""
    
    def __init__(
        self,
        collection_name: str = "knowledge_base",
        embedding_function: str = "sentence-transformers/all-MiniLM-L6-v2",
        persist_directory: str = "./data/chromadb"
    ):
        # Initialize ChromaDB client
        self.client = chromadb.Client(Settings(
            persist_directory=persist_directory,
            chroma_db_impl="duckdb+parquet"
        ))
        
        # Create or get collection
        self.embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=embedding_function
        )
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            embedding_function=self.embedding_function
        )
    
    async def add_entity(self, entity: KnowledgeEntity) -> bool:
        """Add entity to ChromaDB."""
        try:
            # Convert entity to format suitable for ChromaDB
            metadata = {
                "content_type": entity.content_type.value,
                "confidence": entity.confidence,
                "created_at": entity.created_at.isoformat(),
                "updated_at": entity.updated_at.isoformat(),
                "version": entity.version,
                "tags": json.dumps(entity.tags),
                # Add other metadata as needed
            }
            
            # Get text representation for embedding
            if entity.content_type.value == "text":
                text = entity.content
            else:
                # For non-text content, use metadata or description
                text = f"{entity.content_type.value}:{entity.metadata.additional.get('description', '')}"
            
            # Add to ChromaDB
            self.collection.add(
                ids=[str(entity.id)],
                embeddings=[entity.embeddings.get("default", None)],  # Use pre-computed if available
                metadatas=[metadata],
                documents=[text]
            )
            return True
        except Exception as e:
            print(f"Error adding to ChromaDB: {e}")
            return False
    
    async def get_entity(self, entity_id: UUID) -> Optional[KnowledgeEntity]:
        """Retrieve entity from ChromaDB."""
        try:
            result = self.collection.get(
                ids=[str(entity_id)],
                include=["embeddings", "metadatas", "documents"]
            )
            
            if not result or not result["ids"]:
                return None
            
            # Convert ChromaDB result back to KnowledgeEntity
            metadata = result["metadatas"][0]
            return KnowledgeEntity(
                id=entity_id,
                content=result["documents"][0],
                content_type=metadata["content_type"],
                confidence=metadata["confidence"],
                created_at=metadata["created_at"],
                updated_at=metadata["updated_at"],
                version=metadata["version"],
                tags=json.loads(metadata["tags"]),
                embeddings={"default": result["embeddings"][0]}
            )
        except Exception as e:
            print(f"Error retrieving from ChromaDB: {e}")
            return None
    
    async def search_similar(
        self,
        query_vector: List[float],
        limit: int = 10,
        filter_dict: Optional[Dict[str, Any]] = None
    ) -> List[KnowledgeEntity]:
        """Search for similar entities using vector similarity."""
        try:
            # Convert filter_dict to ChromaDB where clause if provided
            where = self._convert_filter_to_where(filter_dict) if filter_dict else None
            
            results = self.collection.query(
                query_embeddings=[query_vector],
                n_results=limit,
                where=where,
                include=["embeddings", "metadatas", "documents"]
            )
            
            entities = []
            for i, entity_id in enumerate(results["ids"][0]):
                metadata = results["metadatas"][0][i]
                entity = KnowledgeEntity(
                    id=UUID(entity_id),
                    content=results["documents"][0][i],
                    content_type=metadata["content_type"],
                    confidence=metadata["confidence"],
                    created_at=metadata["created_at"],
                    updated_at=metadata["updated_at"],
                    version=metadata["version"],
                    tags=json.loads(metadata["tags"]),
                    embeddings={"default": results["embeddings"][0][i]}
                )
                entities.append(entity)
            
            return entities
        except Exception as e:
            print(f"Error searching in ChromaDB: {e}")
            return []
    
    async def update_entity(self, entity: KnowledgeEntity) -> bool:
        """Update existing entity in ChromaDB."""
        try:
            # First delete the existing entity
            await self.delete_entity(entity.id)
            # Then add the updated version
            return await self.add_entity(entity)
        except Exception as e:
            print(f"Error updating in ChromaDB: {e}")
            return False
    
    async def delete_entity(self, entity_id: UUID) -> bool:
        """Delete entity from ChromaDB."""
        try:
            self.collection.delete(ids=[str(entity_id)])
            return True
        except Exception as e:
            print(f"Error deleting from ChromaDB: {e}")
            return False
    
    def _convert_filter_to_where(self, filter_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Convert filter dictionary to ChromaDB where clause."""
        where = {}
        for key, value in filter_dict.items():
            if isinstance(value, list):
                where[key] = {"$in": value}
            else:
                where[key] = {"$eq": value}
        return where
