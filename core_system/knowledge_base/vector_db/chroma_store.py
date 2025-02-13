"""
ChromaDB-based vector store implementation.
"""
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions
import numpy as np

from ..base import BaseKnowledgeStore, KnowledgeItem, KnowledgeQuery

class ChromaStore(BaseKnowledgeStore):
    """ChromaDB-based knowledge store implementation."""
    
    def __init__(
        self,
        collection_name: str = "knowledge_collection",
        embedding_model: str = "all-MiniLM-L6-v2",
        persist_directory: Optional[str] = None
    ):
        """Initialize the ChromaDB store."""
        # Initialize ChromaDB client
        settings = Settings(
            persist_directory=persist_directory,
            anonymized_telemetry=False
        )
        
        self.client = chromadb.Client(settings)
        
        # Initialize embedding function
        self.embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=embedding_model
        )
        
        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            embedding_function=self.embedding_fn,
            metadata={"hnsw:space": "cosine"}
        )
    
    async def store_item(self, item: KnowledgeItem) -> str:
        """Store a knowledge item."""
        # Generate embeddings for the item and its fragments
        item_embedding = self.embedding_fn([item.content])[0]
        
        # Prepare metadata
        metadata = {
            "source_url": item.source_url,
            "source_type": item.source_type,
            "topics": ",".join(item.topics),
            "confidence_score": item.confidence_score,
            "created_at": item.created_at.isoformat(),
            **item.metadata
        }
        
        # Add to ChromaDB
        self.collection.add(
            ids=[item.id or str(len(self.collection.get()["ids"]) + 1)],
            embeddings=[item_embedding],
            documents=[item.content],
            metadatas=[metadata]
        )
        
        return item.id
    
    async def get_item(self, item_id: str) -> Optional[KnowledgeItem]:
        """Retrieve a knowledge item by ID."""
        result = self.collection.get(
            ids=[item_id],
            include=["embeddings", "documents", "metadatas"]
        )
        
        if not result["ids"]:
            return None
        
        metadata = result["metadatas"][0]
        return KnowledgeItem(
            id=item_id,
            content=result["documents"][0],
            source_url=metadata["source_url"],
            source_type=metadata["source_type"],
            topics=metadata["topics"].split(",") if metadata["topics"] else [],
            confidence_score=metadata["confidence_score"],
            metadata={k: v for k, v in metadata.items() if k not in {
                "source_url", "source_type", "topics", "confidence_score", "created_at"
            }}
        )
    
    async def search(self, query: KnowledgeQuery) -> List[KnowledgeItem]:
        """Search for knowledge items."""
        # Generate query embedding
        query_embedding = self.embedding_fn([query.query])[0]
        
        # Prepare where clause for filtering
        where = {}
        if query.source_types:
            where["source_type"] = {"$in": query.source_types}
        if query.min_confidence > 0:
            where["confidence_score"] = {"$gte": query.min_confidence}
        
        # Search in ChromaDB
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=query.max_results,
            where=where if where else None,
            include=["embeddings", "documents", "metadatas"]
        )
        
        # Convert results to KnowledgeItems
        items = []
        for i, doc_id in enumerate(results["ids"][0]):
            metadata = results["metadatas"][0][i]
            items.append(KnowledgeItem(
                id=doc_id,
                content=results["documents"][0][i],
                source_url=metadata["source_url"],
                source_type=metadata["source_type"],
                topics=metadata["topics"].split(",") if metadata["topics"] else [],
                confidence_score=metadata["confidence_score"],
                metadata={k: v for k, v in metadata.items() if k not in {
                    "source_url", "source_type", "topics", "confidence_score", "created_at"
                }}
            ))
        
        return items
    
    async def update_item(self, item_id: str, updates: Dict[str, Any]) -> bool:
        """Update a knowledge item."""
        try:
            # Get existing item
            existing = await self.get_item(item_id)
            if not existing:
                return False
            
            # Update fields
            for key, value in updates.items():
                setattr(existing, key, value)
            
            # Update in ChromaDB
            metadata = {
                "source_url": existing.source_url,
                "source_type": existing.source_type,
                "topics": ",".join(existing.topics),
                "confidence_score": existing.confidence_score,
                "created_at": existing.created_at.isoformat(),
                **existing.metadata
            }
            
            self.collection.update(
                ids=[item_id],
                embeddings=[self.embedding_fn([existing.content])[0]],
                documents=[existing.content],
                metadatas=[metadata]
            )
            
            return True
        except Exception:
            return False
    
    async def delete_item(self, item_id: str) -> bool:
        """Delete a knowledge item."""
        try:
            self.collection.delete(ids=[item_id])
            return True
        except Exception:
            return False
