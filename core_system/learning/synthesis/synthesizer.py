"""
Knowledge synthesis system.
"""

from typing import List, Dict, Optional, Set, Tuple
from datetime import datetime
import logging
import asyncio
import numpy as np
from pydantic import BaseModel

from ...knowledge_base.models import (
    KnowledgeEntity,
    ContentType,
    Relation
)
from ...knowledge_base.storage.base import HybridStore
from ...multimodal_processor.alignment import CrossModalAlignment
from ..researchers.base import ResearchFinding
from .validator import ValidationResult

logger = logging.getLogger(__name__)


class SynthesisResult(BaseModel):
    """Result of knowledge synthesis."""
    entities: List[KnowledgeEntity]
    relations: List[Relation]
    confidence: float
    metadata: Dict
    timestamp: datetime


class KnowledgeSynthesizer:
    """
    Synthesizes validated findings into coherent knowledge
    entities and relations.
    """
    
    def __init__(
        self,
        store: HybridStore,
        alignment: CrossModalAlignment,
        config: Optional[Dict] = None
    ):
        self.store = store
        self.alignment = alignment
        
        # Default config
        self.config = {
            "min_confidence": 0.7,
            "max_concurrent_synthesis": 5,
            "batch_size": 100,
            "language": "es"  # Spanish default
        }
        
        # Update with provided config
        if config:
            self.config.update(config)
        
        # Synthesis semaphore
        self._synthesis_semaphore = asyncio.Semaphore(
            self.config["max_concurrent_synthesis"]
        )
    
    async def synthesize(
        self,
        validation_results: List[ValidationResult]
    ) -> SynthesisResult:
        """Synthesize validated findings into knowledge."""
        try:
            # 1. Filter valid findings
            valid_results = [
                r for r in validation_results
                if r.is_valid and r.confidence >= self.config["min_confidence"]
            ]
            
            if not valid_results:
                return SynthesisResult(
                    entities=[],
                    relations=[],
                    confidence=0.0,
                    metadata={
                        "status": "no_valid_findings",
                        "timestamp": datetime.utcnow().isoformat()
                    },
                    timestamp=datetime.utcnow()
                )
            
            # 2. Group by content type
            grouped_results = self._group_by_content_type(valid_results)
            
            # 3. Process groups concurrently
            synthesis_tasks = []
            for content_type, results in grouped_results.items():
                task = asyncio.create_task(
                    self._synthesize_group(content_type, results)
                )
                synthesis_tasks.append(task)
            
            group_results = await asyncio.gather(*synthesis_tasks)
            
            # 4. Combine results
            all_entities = []
            all_relations = []
            confidences = []
            
            for entities, relations, confidence in group_results:
                all_entities.extend(entities)
                all_relations.extend(relations)
                confidences.append(confidence)
            
            # 5. Create synthesis result
            return SynthesisResult(
                entities=all_entities,
                relations=all_relations,
                confidence=np.mean(confidences) if confidences else 0.0,
                metadata={
                    "total_findings": len(validation_results),
                    "valid_findings": len(valid_results),
                    "content_types": list(grouped_results.keys()),
                    "timestamp": datetime.utcnow().isoformat()
                },
                timestamp=datetime.utcnow()
            )
        
        except Exception as e:
            logger.error(f"Error in knowledge synthesis: {e}")
            raise
    
    def _group_by_content_type(
        self,
        results: List[ValidationResult]
    ) -> Dict[ContentType, List[ValidationResult]]:
        """Group validation results by content type."""
        grouped = {}
        for result in results:
            content_type = result.finding.content_type
            if content_type not in grouped:
                grouped[content_type] = []
            grouped[content_type].append(result)
        return grouped
    
    async def _synthesize_group(
        self,
        content_type: ContentType,
        results: List[ValidationResult]
    ) -> Tuple[List[KnowledgeEntity], List[Relation], float]:
        """Synthesize a group of validation results."""
        async with self._synthesis_semaphore:
            try:
                # 1. Create entities
                entities = []
                for result in results:
                    entity = await self._create_entity(result)
                    if entity:
                        entities.append(entity)
                
                if not entities:
                    return [], [], 0.0
                
                # 2. Find relations
                relations = await self._find_relations(entities)
                
                # 3. Calculate confidence
                confidence = np.mean([
                    result.confidence for result in results
                ])
                
                return entities, relations, confidence
            
            except Exception as e:
                logger.error(
                    f"Error synthesizing {content_type} group: {e}"
                )
                return [], [], 0.0
    
    async def _create_entity(
        self,
        result: ValidationResult
    ) -> Optional[KnowledgeEntity]:
        """Create knowledge entity from validation result."""
        try:
            # Generate embedding
            embedding = await self.alignment.align(
                result.finding.content,
                result.finding.content_type
            )
            
            # Create entity
            return KnowledgeEntity(
                id=result.finding.metadata.get(
                    "id",
                    str(uuid.uuid4())
                ),
                content_type=result.finding.content_type,
                content=result.finding.content,
                version=1,
                confidence=result.confidence,
                embeddings={"default": embedding.tolist()},
                metadata={
                    **result.finding.metadata,
                    "source": result.finding.source,
                    "source_url": result.finding.source_url,
                    "validation_scores": result.scores,
                    "validation_feedback": result.feedback,
                    "timestamp": datetime.utcnow().isoformat()
                },
                relations=[]
            )
        
        except Exception as e:
            logger.error(f"Error creating entity: {e}")
            return None
    
    async def _find_relations(
        self,
        entities: List[KnowledgeEntity]
    ) -> List[Relation]:
        """Find relations between entities."""
        relations = []
        
        try:
            # 1. Get existing related entities
            existing_entities = []
            for entity in entities:
                similar = await self.store.vector_store.search_similar(
                    np.array(entity.embeddings["default"]),
                    limit=self.config["batch_size"],
                    min_similarity=0.5
                )
                existing_entities.extend(similar)
            
            # 2. Find internal relations
            internal_relations = await self._find_internal_relations(
                entities
            )
            relations.extend(internal_relations)
            
            # 3. Find external relations
            external_relations = await self._find_external_relations(
                entities,
                existing_entities
            )
            relations.extend(external_relations)
            
            return relations
        
        except Exception as e:
            logger.error(f"Error finding relations: {e}")
            return []
    
    async def _find_internal_relations(
        self,
        entities: List[KnowledgeEntity]
    ) -> List[Relation]:
        """Find relations between new entities."""
        relations = []
        
        try:
            for i, entity1 in enumerate(entities):
                for entity2 in entities[i+1:]:
                    # Compare entities
                    similarity = await self.alignment.compare(
                        entity1.content,
                        entity2.content,
                        entity1.content_type,
                        entity2.content_type
                    )
                    
                    if similarity >= self.config["min_confidence"]:
                        # Create bidirectional relations
                        relations.extend([
                            Relation(
                                type="similar_to",
                                source_id=entity1.id,
                                target_id=entity2.id,
                                target_type=entity2.content_type,
                                confidence=similarity,
                                metadata={
                                    "similarity_score": similarity,
                                    "timestamp": datetime.utcnow().isoformat()
                                }
                            ),
                            Relation(
                                type="similar_to",
                                source_id=entity2.id,
                                target_id=entity1.id,
                                target_type=entity1.content_type,
                                confidence=similarity,
                                metadata={
                                    "similarity_score": similarity,
                                    "timestamp": datetime.utcnow().isoformat()
                                }
                            )
                        ])
            
            return relations
        
        except Exception as e:
            logger.error(f"Error finding internal relations: {e}")
            return []
    
    async def _find_external_relations(
        self,
        new_entities: List[KnowledgeEntity],
        existing_entities: List[KnowledgeEntity]
    ) -> List[Relation]:
        """Find relations with existing entities."""
        relations = []
        
        try:
            for new_entity in new_entities:
                for existing_entity in existing_entities:
                    # Skip self-relations
                    if new_entity.id == existing_entity.id:
                        continue
                    
                    # Compare entities
                    similarity = await self.alignment.compare(
                        new_entity.content,
                        existing_entity.content,
                        new_entity.content_type,
                        existing_entity.content_type
                    )
                    
                    if similarity >= self.config["min_confidence"]:
                        # Create relation
                        relations.append(
                            Relation(
                                type="similar_to",
                                source_id=new_entity.id,
                                target_id=existing_entity.id,
                                target_type=existing_entity.content_type,
                                confidence=similarity,
                                metadata={
                                    "similarity_score": similarity,
                                    "timestamp": datetime.utcnow().isoformat()
                                }
                            )
                        )
            
            return relations
        
        except Exception as e:
            logger.error(f"Error finding external relations: {e}")
            return []
