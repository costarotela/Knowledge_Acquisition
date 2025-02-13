"""
Advanced search engine for the knowledge base system.
Implements hybrid search combining vector similarity and graph traversal.
"""

from typing import List, Dict, Any, Optional, Tuple
from uuid import UUID
import asyncio
from datetime import datetime
import numpy as np
from pydantic import BaseModel

from .storage.base import HybridStore
from .models import KnowledgeEntity, ContentType
from .config import SearchSettings


class SearchQuery(BaseModel):
    """Structure for complex search queries."""
    text: Optional[str] = None
    content_types: List[ContentType] = []
    tags: List[str] = []
    min_confidence: float = 0.5
    date_range: Optional[Tuple[datetime, datetime]] = None
    require_all_tags: bool = False
    exclude_tags: List[str] = []
    related_to: Optional[UUID] = None
    relation_depth: int = 2


class SearchResult(BaseModel):
    """Structure for search results."""
    direct_matches: List[KnowledgeEntity]
    related_entities: List[KnowledgeEntity]
    graph_paths: List[List[UUID]]
    relevance_scores: Dict[UUID, float]
    metadata: Dict[str, Any]


class AdvancedSearchEngine:
    """Advanced search implementation combining vector and graph capabilities."""
    
    def __init__(
        self,
        store: HybridStore,
        settings: SearchSettings
    ):
        self.store = store
        self.settings = settings
        self._query_cache: Dict[str, Tuple[SearchResult, datetime]] = {}
    
    async def semantic_search(
        self,
        query: SearchQuery,
        limit: int = None
    ) -> SearchResult:
        """
        Perform advanced semantic search using both vector and graph capabilities.
        """
        limit = min(limit or self.settings.default_limit, self.settings.max_limit)
        
        # Check cache first
        cache_key = self._generate_cache_key(query, limit)
        cached_result = self._get_from_cache(cache_key)
        if cached_result:
            return cached_result
        
        # Parallel execution of vector and graph searches
        vector_task = self._vector_search(query, limit)
        graph_task = self._graph_search(query) if query.related_to else None
        
        # Wait for both searches
        direct_matches = await vector_task
        graph_results = await graph_task if graph_task else ([], [])
        
        # Combine and rank results
        result = await self._combine_results(
            direct_matches,
            graph_results[0],  # related entities
            graph_results[1],  # paths
            query
        )
        
        # Cache result
        self._cache_result(cache_key, result)
        
        return result
    
    async def _vector_search(
        self,
        query: SearchQuery,
        limit: int
    ) -> List[KnowledgeEntity]:
        """Perform vector similarity search with filters."""
        # Prepare filter dictionary
        filters = self._build_filters(query)
        
        # Get vector for text query
        if query.text:
            vector = await self._get_query_vector(query.text)
        else:
            return []
        
        # Search with filters
        matches = await self.store.vector_store.search_similar(
            query_vector=vector,
            limit=limit,
            filter_dict=filters
        )
        
        return matches
    
    async def _graph_search(
        self,
        query: SearchQuery
    ) -> Tuple[List[KnowledgeEntity], List[List[UUID]]]:
        """Perform graph-based search."""
        if not query.related_to:
            return [], []
        
        # Get relations within specified depth
        relations = await self.store.graph_store.get_relations(
            query.related_to,
            max_depth=query.relation_depth
        )
        
        # Collect unique entity IDs from relations
        entity_ids = {rel.target_id for rel in relations}
        
        # Fetch entities
        entities = []
        paths = []
        for entity_id in entity_ids:
            entity = await self.store.get_entity(entity_id)
            if entity and self._matches_filters(entity, query):
                entities.append(entity)
                # Get paths to this entity
                entity_paths = await self.store.graph_store.search_path(
                    query.related_to,
                    entity_id,
                    max_depth=query.relation_depth
                )
                paths.extend(entity_paths)
        
        return entities, paths
    
    async def _combine_results(
        self,
        direct_matches: List[KnowledgeEntity],
        related_entities: List[KnowledgeEntity],
        paths: List[List[UUID]],
        query: SearchQuery
    ) -> SearchResult:
        """Combine and rank results from different search methods."""
        # Calculate relevance scores
        relevance_scores = {}
        
        # Score direct matches
        for i, entity in enumerate(direct_matches):
            score = 1.0 - (i / len(direct_matches))  # Decay by position
            score *= entity.confidence  # Factor in confidence
            relevance_scores[entity.id] = score
        
        # Score related entities
        for entity in related_entities:
            base_score = 0.7  # Lower base score for related entities
            score = base_score * entity.confidence
            
            # Boost score based on path length
            for path in paths:
                if entity.id in [UUID(node) for node in path]:
                    path_penalty = len(path) * 0.1  # Longer paths reduce score
                    score = max(score, base_score - path_penalty)
            
            relevance_scores[entity.id] = score
        
        # Prepare metadata
        metadata = {
            "total_results": len(direct_matches) + len(related_entities),
            "direct_matches": len(direct_matches),
            "related_matches": len(related_entities),
            "paths_found": len(paths),
            "query_time": datetime.utcnow().isoformat()
        }
        
        return SearchResult(
            direct_matches=direct_matches,
            related_entities=related_entities,
            graph_paths=paths,
            relevance_scores=relevance_scores,
            metadata=metadata
        )
    
    def _build_filters(self, query: SearchQuery) -> Dict[str, Any]:
        """Build filter dictionary from query parameters."""
        filters = {}
        
        if query.content_types:
            filters["content_type"] = [ct.value for ct in query.content_types]
        
        if query.min_confidence > 0:
            filters["confidence"] = {"$gte": query.min_confidence}
        
        if query.tags:
            if query.require_all_tags:
                filters["tags"] = {"$all": query.tags}
            else:
                filters["tags"] = {"$in": query.tags}
        
        if query.exclude_tags:
            filters["tags"] = {"$nin": query.exclude_tags}
        
        if query.date_range:
            start, end = query.date_range
            filters["created_at"] = {
                "$gte": start.isoformat(),
                "$lte": end.isoformat()
            }
        
        return filters
    
    def _matches_filters(self, entity: KnowledgeEntity, query: SearchQuery) -> bool:
        """Check if entity matches query filters."""
        if query.content_types and entity.content_type not in query.content_types:
            return False
        
        if entity.confidence < query.min_confidence:
            return False
        
        if query.tags:
            if query.require_all_tags:
                if not all(tag in entity.tags for tag in query.tags):
                    return False
            elif not any(tag in entity.tags for tag in query.tags):
                return False
        
        if query.exclude_tags and any(tag in entity.tags for tag in query.exclude_tags):
            return False
        
        if query.date_range:
            start, end = query.date_range
            if not (start <= entity.created_at <= end):
                return False
        
        return True
    
    async def _get_query_vector(self, text: str) -> List[float]:
        """Convert text query to vector using the same model as storage."""
        # Use ChromaDB's embedding function
        return self.store.vector_store.embedding_function([text])[0]
    
    def _generate_cache_key(self, query: SearchQuery, limit: int) -> str:
        """Generate cache key for query."""
        return f"{hash(query.json())}-{limit}"
    
    def _get_from_cache(self, key: str) -> Optional[SearchResult]:
        """Get result from cache if still valid."""
        if not self.settings.cache_ttl:
            return None
            
        if key in self._query_cache:
            result, timestamp = self._query_cache[key]
            age = (datetime.utcnow() - timestamp).total_seconds()
            
            if age < self.settings.cache_ttl:
                return result
            
            # Clean up expired cache entry
            del self._query_cache[key]
        
        return None
    
    def _cache_result(self, key: str, result: SearchResult) -> None:
        """Cache search result."""
        if self.settings.cache_ttl:
            self._query_cache[key] = (result, datetime.utcnow())
