"""
Internal knowledge base researcher implementation.
"""

import asyncio
from typing import Dict, List, Optional, Set, Tuple
from datetime import datetime
import logging
import json
import numpy as np
from pathlib import Path

from .base import (
    BaseResearcher,
    ResearchQuery,
    ResearchFinding,
    ResearchResult
)
from ...knowledge_base.models import (
    KnowledgeEntity,
    ContentType,
    Relation
)
from ...knowledge_base.storage.base import HybridStore
from ...multimodal_processor.alignment import CrossModalAlignment

logger = logging.getLogger(__name__)


class InternalResearcher(BaseResearcher):
    """
    Researcher that uses the internal knowledge base
    to discover new insights and connections.
    """
    
    def __init__(
        self,
        store: HybridStore,
        alignment: CrossModalAlignment,
        config: Optional[Dict] = None,
        **kwargs
    ):
        super().__init__(config, **kwargs)
        
        self.store = store
        self.alignment = alignment
        
        # Default config
        self.config.update({
            "min_similarity": 0.7,
            "max_hops": 3,
            "min_confidence": 0.7,
            "batch_size": 100,
            "language": "es"  # Spanish default
        })
        
        # Update with provided config
        if config:
            self.config.update(config)
    
    async def research(self, query: ResearchQuery) -> ResearchResult:
        """Conduct internal research."""
        start_time = datetime.utcnow()
        
        try:
            # 1. Check cache
            cache_key = self._get_cache_key(query)
            cached = self._load_cache(cache_key)
            if cached:
                return ResearchResult(**cached)
            
            # 2. Get initial entities
            seed_entities = await self._get_seed_entities(query)
            
            # 3. Expand graph exploration
            explored_entities = await self._explore_graph(
                seed_entities,
                query
            )
            
            # 4. Analyze patterns
            patterns = await self._analyze_patterns(explored_entities)
            
            # 5. Generate insights
            insights = await self._generate_insights(
                patterns,
                query
            )
            
            # 6. Convert insights to findings
            findings = []
            for insight in insights:
                finding = await self._create_finding(insight)
                if finding:
                    findings.append(finding)
            
            # 7. Create research result
            research_result = ResearchResult(
                query=query,
                findings=findings,
                total_findings=len(findings),
                processing_time=(
                    datetime.utcnow() - start_time
                ).total_seconds(),
                metadata={
                    "source": "internal",
                    "seed_entities": len(seed_entities),
                    "explored_entities": len(explored_entities),
                    "patterns": len(patterns)
                }
            )
            
            # 8. Cache result
            self._save_cache(cache_key, research_result.dict())
            
            return research_result
        
        except Exception as e:
            logger.error(f"Error in internal research: {e}", exc_info=True)
            raise
    
    async def _get_seed_entities(
        self,
        query: ResearchQuery
    ) -> List[KnowledgeEntity]:
        """Get initial seed entities for exploration."""
        try:
            # 1. Encode query
            query_embedding = await self.alignment.align(
                query.query,
                ContentType.TEXT
            )
            
            # 2. Search vector store
            entities = await self.store.vector_store.search_similar(
                query_embedding,
                limit=self.config["batch_size"],
                min_similarity=self.config["min_similarity"]
            )
            
            # 3. Filter by modalities
            if query.modalities:
                entities = [
                    e for e in entities
                    if e.content_type in query.modalities
                ]
            
            return entities
        
        except Exception as e:
            logger.error(f"Error getting seed entities: {e}")
            return []
    
    async def _explore_graph(
        self,
        seed_entities: List[KnowledgeEntity],
        query: ResearchQuery
    ) -> List[KnowledgeEntity]:
        """Explore knowledge graph from seed entities."""
        explored = set()
        to_explore = set(e.id for e in seed_entities)
        all_entities = {e.id: e for e in seed_entities}
        
        for _ in range(self.config["max_hops"]):
            if not to_explore:
                break
            
            current_batch = list(to_explore)
            to_explore.clear()
            
            # Get related entities
            for entity_id in current_batch:
                if entity_id in explored:
                    continue
                
                related = await self.store.graph_store.get_related_entities(
                    entity_id
                )
                
                for entity in related:
                    if (
                        entity.id not in explored and
                        entity.id not in to_explore and
                        entity.confidence >= self.config["min_confidence"]
                    ):
                        to_explore.add(entity.id)
                        all_entities[entity.id] = entity
                
                explored.add(entity_id)
        
        return list(all_entities.values())
    
    async def _analyze_patterns(
        self,
        entities: List[KnowledgeEntity]
    ) -> List[Dict]:
        """Analyze patterns in explored entities."""
        patterns = []
        
        try:
            # 1. Group by content type
            type_groups = {}
            for entity in entities:
                if entity.content_type not in type_groups:
                    type_groups[entity.content_type] = []
                type_groups[entity.content_type].append(entity)
            
            # 2. Analyze each group
            for content_type, group in type_groups.items():
                # Calculate statistics
                stats = {
                    "count": len(group),
                    "avg_confidence": np.mean([e.confidence for e in group]),
                    "temporal_range": self._get_temporal_range(group)
                }
                
                # Find common relations
                common_relations = self._find_common_relations(group)
                
                # Find content patterns
                content_patterns = await self._find_content_patterns(
                    group,
                    content_type
                )
                
                patterns.append({
                    "content_type": content_type,
                    "statistics": stats,
                    "relations": common_relations,
                    "content_patterns": content_patterns
                })
        
        except Exception as e:
            logger.error(f"Error analyzing patterns: {e}")
        
        return patterns
    
    def _get_temporal_range(
        self,
        entities: List[KnowledgeEntity]
    ) -> Optional[Dict]:
        """Get temporal range of entities."""
        try:
            timestamps = []
            for entity in entities:
                if "timestamp" in entity.metadata:
                    try:
                        ts = datetime.fromisoformat(
                            entity.metadata["timestamp"]
                        )
                        timestamps.append(ts)
                    except (ValueError, TypeError):
                        continue
            
            if timestamps:
                return {
                    "start": min(timestamps).isoformat(),
                    "end": max(timestamps).isoformat(),
                    "duration_days": (
                        max(timestamps) - min(timestamps)
                    ).days
                }
            
            return None
        
        except Exception as e:
            logger.error(f"Error getting temporal range: {e}")
            return None
    
    def _find_common_relations(
        self,
        entities: List[KnowledgeEntity]
    ) -> List[Dict]:
        """Find common relations between entities."""
        try:
            relation_counts = {}
            
            for entity in entities:
                for relation in entity.relations:
                    key = (relation.type, relation.target_type)
                    if key not in relation_counts:
                        relation_counts[key] = {
                            "type": relation.type,
                            "target_type": relation.target_type,
                            "count": 0,
                            "confidence_sum": 0
                        }
                    
                    relation_counts[key]["count"] += 1
                    relation_counts[key]["confidence_sum"] += relation.confidence
            
            # Calculate statistics
            common_relations = []
            for stats in relation_counts.values():
                if stats["count"] >= 2:  # At least 2 occurrences
                    common_relations.append({
                        "type": stats["type"],
                        "target_type": stats["target_type"],
                        "frequency": stats["count"] / len(entities),
                        "avg_confidence": (
                            stats["confidence_sum"] / stats["count"]
                        )
                    })
            
            return sorted(
                common_relations,
                key=lambda x: x["frequency"],
                reverse=True
            )
        
        except Exception as e:
            logger.error(f"Error finding common relations: {e}")
            return []
    
    async def _find_content_patterns(
        self,
        entities: List[KnowledgeEntity],
        content_type: ContentType
    ) -> List[Dict]:
        """Find patterns in entity content."""
        try:
            if content_type == ContentType.TEXT:
                return await self._find_text_patterns(entities)
            elif content_type == ContentType.IMAGE:
                return await self._find_image_patterns(entities)
            elif content_type == ContentType.AUDIO:
                return await self._find_audio_patterns(entities)
            else:
                return []
        
        except Exception as e:
            logger.error(f"Error finding content patterns: {e}")
            return []
    
    async def _find_text_patterns(
        self,
        entities: List[KnowledgeEntity]
    ) -> List[Dict]:
        """Find patterns in text content."""
        # Implementation would analyze text patterns
        return []
    
    async def _find_image_patterns(
        self,
        entities: List[KnowledgeEntity]
    ) -> List[Dict]:
        """Find patterns in image content."""
        # Implementation would analyze image patterns
        return []
    
    async def _find_audio_patterns(
        self,
        entities: List[KnowledgeEntity]
    ) -> List[Dict]:
        """Find patterns in audio content."""
        # Implementation would analyze audio patterns
        return []
    
    async def _generate_insights(
        self,
        patterns: List[Dict],
        query: ResearchQuery
    ) -> List[Dict]:
        """Generate insights from patterns."""
        insights = []
        
        try:
            for pattern in patterns:
                # Generate basic insights
                if pattern["statistics"]["count"] >= 3:
                    insights.append({
                        "type": "distribution",
                        "content": (
                            f"Found {pattern['statistics']['count']} "
                            f"entities of type {pattern['content_type']} "
                            f"with average confidence "
                            f"{pattern['statistics']['avg_confidence']:.2f}"
                        ),
                        "confidence": 0.8,
                        "evidence": {
                            "count": pattern["statistics"]["count"],
                            "avg_confidence": (
                                pattern["statistics"]["avg_confidence"]
                            )
                        }
                    })
                
                # Analyze temporal patterns
                if pattern["statistics"].get("temporal_range"):
                    temporal = pattern["statistics"]["temporal_range"]
                    insights.append({
                        "type": "temporal",
                        "content": (
                            f"Knowledge spans "
                            f"{temporal['duration_days']} days "
                            f"from {temporal['start']} to {temporal['end']}"
                        ),
                        "confidence": 0.9,
                        "evidence": temporal
                    })
                
                # Analyze relations
                for relation in pattern["relations"]:
                    if relation["frequency"] >= 0.5:  # At least 50% frequency
                        insights.append({
                            "type": "relation",
                            "content": (
                                f"Found common relation '{relation['type']}' "
                                f"to {relation['target_type']} "
                                f"with {relation['frequency']*100:.1f}% "
                                f"frequency"
                            ),
                            "confidence": relation["avg_confidence"],
                            "evidence": relation
                        })
                
                # Add content-specific insights
                for content_pattern in pattern["content_patterns"]:
                    insights.append({
                        "type": "content",
                        "content": content_pattern["description"],
                        "confidence": content_pattern["confidence"],
                        "evidence": content_pattern
                    })
        
        except Exception as e:
            logger.error(f"Error generating insights: {e}")
        
        return insights
    
    async def _create_finding(
        self,
        insight: Dict
    ) -> Optional[ResearchFinding]:
        """Convert insight to research finding."""
        try:
            return ResearchFinding(
                content=insight["content"],
                content_type=ContentType.TEXT,
                source="internal_analysis",
                source_url=None,
                confidence=insight["confidence"],
                metadata={
                    "type": insight["type"],
                    "evidence": insight["evidence"]
                },
                timestamp=datetime.utcnow()
            )
        
        except Exception as e:
            logger.error(f"Error creating finding: {e}")
            return None
