"""
Unified knowledge store that combines vector and graph databases.
"""
from typing import List, Dict, Any, Optional, Tuple
import logging
from datetime import datetime

from .base import (
    BaseKnowledgeStore,
    BaseKnowledgeGraph,
    KnowledgeItem,
    KnowledgeQuery
)
from .vector_db.chroma_store import ChromaStore
from .graph_db.neo4j_store import Neo4jGraph

logger = logging.getLogger(__name__)

class UnifiedKnowledgeStore:
    """
    Unified knowledge store that combines vector and graph storage.
    
    This store:
    1. Stores raw content and embeddings in ChromaDB
    2. Stores concept relationships in Neo4j
    3. Provides unified search across both stores
    4. Maintains consistency between stores
    """
    
    def __init__(
        self,
        vector_store: BaseKnowledgeStore,
        graph_store: BaseKnowledgeGraph
    ):
        """Initialize the unified store."""
        self.vector_store = vector_store
        self.graph_store = graph_store
    
    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> 'UnifiedKnowledgeStore':
        """Create a UnifiedKnowledgeStore from configuration."""
        # Initialize vector store
        vector_config = config.get("vector_db", {})
        vector_store = ChromaStore(
            collection_name=vector_config.get("collection_name", "knowledge_collection"),
            embedding_model=vector_config.get("embedding_model", "all-MiniLM-L6-v2"),
            persist_directory=vector_config.get("persist_directory")
        )
        
        # Initialize graph store
        graph_config = config.get("graph_db", {})
        graph_store = Neo4jGraph(
            uri=graph_config["uri"],
            user=graph_config["user"],
            password=graph_config["password"],
            database=graph_config.get("database", "neo4j")
        )
        
        return cls(vector_store, graph_store)
    
    async def store_knowledge(
        self,
        item: KnowledgeItem,
        extract_concepts: bool = True
    ) -> Tuple[str, List[str]]:
        """
        Store knowledge in both vector and graph stores.
        
        Args:
            item: Knowledge item to store
            extract_concepts: Whether to extract and store concepts
            
        Returns:
            Tuple of (item_id, concept_ids)
        """
        try:
            # Store in vector database
            item_id = await self.vector_store.store_item(item)
            
            # Extract and store concepts if requested
            concept_ids = []
            if extract_concepts:
                # Extract main concepts (simplified)
                concepts = item.topics
                
                # Store concepts and their relationships
                for concept in concepts:
                    concept_id = await self.graph_store.add_concept(
                        concept=concept,
                        properties={
                            "source_id": item_id,
                            "confidence": item.confidence_score,
                            "source_type": item.source_type
                        }
                    )
                    concept_ids.append(concept_id)
                
                # Add relationships between concepts
                for relation in item.relations:
                    await self.graph_store.add_relation(
                        from_concept=relation["from"],
                        to_concept=relation["to"],
                        relation_type=relation["type"],
                        properties={
                            "source_id": item_id,
                            "confidence": item.confidence_score
                        }
                    )
            
            return item_id, concept_ids
            
        except Exception as e:
            logger.error(f"Error storing knowledge: {e}")
            raise
    
    async def search_knowledge(
        self,
        query: KnowledgeQuery,
        include_related: bool = True
    ) -> List[KnowledgeItem]:
        """
        Search for knowledge using both vector and graph capabilities.
        
        Args:
            query: Search parameters
            include_related: Whether to include related concepts
            
        Returns:
            List of relevant knowledge items
        """
        try:
            # Search in vector store
            vector_results = await self.vector_store.search(query)
            
            if include_related:
                # Search for related concepts in graph
                for topic in (query.topics or []):
                    related = await self.graph_store.get_related_concepts(topic)
                    
                    # Add related topics to search
                    if related:
                        new_query = KnowledgeQuery(
                            query=query.query,
                            topics=[r["name"] for r in related],
                            source_types=query.source_types,
                            min_confidence=query.min_confidence,
                            max_results=query.max_results
                        )
                        
                        # Get additional results
                        additional = await self.vector_store.search(new_query)
                        vector_results.extend(additional)
            
            # Remove duplicates and sort by confidence
            seen = set()
            unique_results = []
            for item in vector_results:
                if item.id not in seen:
                    seen.add(item.id)
                    unique_results.append(item)
            
            return sorted(
                unique_results,
                key=lambda x: x.confidence_score,
                reverse=True
            )[:query.max_results]
            
        except Exception as e:
            logger.error(f"Error searching knowledge: {e}")
            raise
    
    async def get_knowledge_graph(
        self,
        concept: Optional[str] = None,
        max_depth: int = 2
    ) -> Dict[str, Any]:
        """
        Get a knowledge graph centered on a concept.
        
        Args:
            concept: Central concept (optional)
            max_depth: Maximum traversal depth
            
        Returns:
            Graph structure with nodes and edges
        """
        try:
            if concept:
                # Get concept and related concepts up to max_depth
                related = await self.graph_store.get_related_concepts(concept)
                
                # TODO: Implement breadth-first traversal up to max_depth
                return {
                    "central_concept": concept,
                    "related_concepts": related
                }
            else:
                # Get overall graph statistics and sample
                concepts = await self.graph_store.search_concepts("")
                return {
                    "total_concepts": len(concepts),
                    "sample_concepts": concepts[:10]
                }
                
        except Exception as e:
            logger.error(f"Error getting knowledge graph: {e}")
            raise
