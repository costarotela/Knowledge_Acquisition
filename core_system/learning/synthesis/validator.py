"""
Knowledge validation system.
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

logger = logging.getLogger(__name__)


class ValidationRule(BaseModel):
    """Validation rule specification."""
    name: str
    description: str
    priority: int  # 1 (highest) to 5 (lowest)
    content_types: List[ContentType]
    threshold: float
    metadata: Dict


class ValidationResult(BaseModel):
    """Result of validation process."""
    finding: ResearchFinding
    rules_applied: List[str]
    scores: Dict[str, float]
    overall_score: float
    is_valid: bool
    confidence: float
    feedback: List[str]
    metadata: Dict
    timestamp: datetime


class KnowledgeValidator:
    """
    Validates research findings through multiple validation rules
    and cross-references with existing knowledge.
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
            "min_overall_score": 0.7,
            "min_confidence": 0.7,
            "max_concurrent_validations": 10,
            "validation_timeout": 30,  # seconds
            "language": "es"  # Spanish default
        }
        
        # Update with provided config
        if config:
            self.config.update(config)
        
        # Initialize validation rules
        self.rules = self._init_validation_rules()
        
        # Validation semaphore
        self._validation_semaphore = asyncio.Semaphore(
            self.config["max_concurrent_validations"]
        )
    
    def _init_validation_rules(self) -> List[ValidationRule]:
        """Initialize validation rules."""
        return [
            # Content quality rules
            ValidationRule(
                name="content_length",
                description="Validates content length and structure",
                priority=1,
                content_types=[ContentType.TEXT],
                threshold=0.7,
                metadata={"min_length": 50}
            ),
            ValidationRule(
                name="content_relevance",
                description="Validates content relevance to domain",
                priority=1,
                content_types=[
                    ContentType.TEXT,
                    ContentType.IMAGE,
                    ContentType.AUDIO
                ],
                threshold=0.8,
                metadata={}
            ),
            
            # Source validation rules
            ValidationRule(
                name="source_reliability",
                description="Validates source reliability",
                priority=2,
                content_types=[
                    ContentType.TEXT,
                    ContentType.IMAGE,
                    ContentType.AUDIO
                ],
                threshold=0.7,
                metadata={}
            ),
            ValidationRule(
                name="temporal_relevance",
                description="Validates temporal relevance",
                priority=2,
                content_types=[
                    ContentType.TEXT,
                    ContentType.IMAGE,
                    ContentType.AUDIO
                ],
                threshold=0.7,
                metadata={"max_age_days": 365}
            ),
            
            # Consistency rules
            ValidationRule(
                name="internal_consistency",
                description="Validates consistency with existing knowledge",
                priority=3,
                content_types=[
                    ContentType.TEXT,
                    ContentType.IMAGE,
                    ContentType.AUDIO
                ],
                threshold=0.8,
                metadata={}
            ),
            ValidationRule(
                name="cross_modal_consistency",
                description="Validates consistency across modalities",
                priority=3,
                content_types=[
                    ContentType.TEXT,
                    ContentType.IMAGE,
                    ContentType.AUDIO
                ],
                threshold=0.8,
                metadata={}
            ),
            
            # Quality rules
            ValidationRule(
                name="language_quality",
                description="Validates language quality and coherence",
                priority=4,
                content_types=[ContentType.TEXT],
                threshold=0.7,
                metadata={"language": "es"}
            ),
            ValidationRule(
                name="media_quality",
                description="Validates media quality",
                priority=4,
                content_types=[
                    ContentType.IMAGE,
                    ContentType.AUDIO
                ],
                threshold=0.7,
                metadata={}
            )
        ]
    
    async def validate(
        self,
        findings: List[ResearchFinding]
    ) -> List[ValidationResult]:
        """Validate multiple findings concurrently."""
        tasks = []
        for finding in findings:
            task = asyncio.create_task(
                self._validate_finding(finding)
            )
            tasks.append(task)
        
        try:
            results = await asyncio.gather(*tasks)
            return [r for r in results if r is not None]
        
        except Exception as e:
            logger.error(f"Error in batch validation: {e}")
            return []
    
    async def _validate_finding(
        self,
        finding: ResearchFinding
    ) -> Optional[ValidationResult]:
        """Validate a single finding."""
        async with self._validation_semaphore:
            try:
                # 1. Get applicable rules
                rules = self._get_applicable_rules(finding)
                
                # 2. Apply rules concurrently
                validation_tasks = []
                for rule in rules:
                    task = asyncio.create_task(
                        self._apply_rule(rule, finding)
                    )
                    validation_tasks.append((rule.name, task))
                
                # 3. Collect results with timeout
                scores = {}
                feedback = []
                
                for rule_name, task in validation_tasks:
                    try:
                        score, rule_feedback = await asyncio.wait_for(
                            task,
                            timeout=self.config["validation_timeout"]
                        )
                        scores[rule_name] = score
                        if rule_feedback:
                            feedback.extend(rule_feedback)
                    
                    except asyncio.TimeoutError:
                        logger.warning(
                            f"Validation timeout for rule {rule_name}"
                        )
                        scores[rule_name] = 0.0
                        feedback.append(
                            f"Timeout applying rule {rule_name}"
                        )
                
                # 4. Calculate overall score
                if scores:
                    overall_score = np.mean(list(scores.values()))
                    confidence = self._calculate_confidence(scores)
                    
                    return ValidationResult(
                        finding=finding,
                        rules_applied=list(scores.keys()),
                        scores=scores,
                        overall_score=overall_score,
                        is_valid=overall_score >= self.config["min_overall_score"],
                        confidence=confidence,
                        feedback=feedback,
                        metadata={
                            "validation_time": datetime.utcnow().isoformat()
                        },
                        timestamp=datetime.utcnow()
                    )
                
                return None
            
            except Exception as e:
                logger.error(
                    f"Error validating finding {finding.content}: {e}"
                )
                return None
    
    def _get_applicable_rules(
        self,
        finding: ResearchFinding
    ) -> List[ValidationRule]:
        """Get rules applicable to the finding."""
        return [
            rule for rule in self.rules
            if finding.content_type in rule.content_types
        ]
    
    async def _apply_rule(
        self,
        rule: ValidationRule,
        finding: ResearchFinding
    ) -> Tuple[float, List[str]]:
        """Apply a validation rule."""
        try:
            if rule.name == "content_length":
                return await self._validate_content_length(rule, finding)
            
            elif rule.name == "content_relevance":
                return await self._validate_content_relevance(rule, finding)
            
            elif rule.name == "source_reliability":
                return await self._validate_source_reliability(rule, finding)
            
            elif rule.name == "temporal_relevance":
                return await self._validate_temporal_relevance(rule, finding)
            
            elif rule.name == "internal_consistency":
                return await self._validate_internal_consistency(rule, finding)
            
            elif rule.name == "cross_modal_consistency":
                return await self._validate_cross_modal_consistency(rule, finding)
            
            elif rule.name == "language_quality":
                return await self._validate_language_quality(rule, finding)
            
            elif rule.name == "media_quality":
                return await self._validate_media_quality(rule, finding)
            
            else:
                logger.warning(f"Unknown rule: {rule.name}")
                return 0.0, [f"Unknown rule: {rule.name}"]
        
        except Exception as e:
            logger.error(f"Error applying rule {rule.name}: {e}")
            return 0.0, [f"Error in {rule.name}: {str(e)}"]
    
    async def _validate_content_length(
        self,
        rule: ValidationRule,
        finding: ResearchFinding
    ) -> Tuple[float, List[str]]:
        """Validate content length."""
        feedback = []
        
        if isinstance(finding.content, str):
            length = len(finding.content)
            min_length = rule.metadata["min_length"]
            
            if length < min_length:
                feedback.append(
                    f"Content length ({length}) below minimum ({min_length})"
                )
                return 0.0, feedback
            
            # Score based on length
            score = min(1.0, length / (min_length * 2))
            return score, []
        
        return 1.0, []  # Non-text content
    
    async def _validate_content_relevance(
        self,
        rule: ValidationRule,
        finding: ResearchFinding
    ) -> Tuple[float, List[str]]:
        """Validate content relevance."""
        try:
            # Get content embedding
            content_embedding = await self.alignment.align(
                finding.content,
                finding.content_type
            )
            
            # Search similar content
            similar = await self.store.vector_store.search_similar(
                content_embedding,
                limit=5,
                min_similarity=0.5
            )
            
            if not similar:
                return 0.5, ["No similar content found for comparison"]
            
            # Calculate average similarity
            similarities = [
                await self.alignment.compare(
                    finding.content,
                    entity.content,
                    finding.content_type,
                    entity.content_type
                )
                for entity in similar
            ]
            
            avg_similarity = np.mean(similarities)
            return avg_similarity, []
        
        except Exception as e:
            return 0.0, [f"Error in relevance check: {e}"]
    
    async def _validate_source_reliability(
        self,
        rule: ValidationRule,
        finding: ResearchFinding
    ) -> Tuple[float, List[str]]:
        """Validate source reliability."""
        score = 0.5  # Base score
        feedback = []
        
        # Check source
        if finding.source == "academic":
            score += 0.3
        elif finding.source == "web":
            if finding.source_url:
                # Could implement domain reputation check
                score += 0.1
        elif finding.source == "internal":
            score += 0.2
        
        # Check metadata
        if finding.metadata:
            if "authors" in finding.metadata:
                score += 0.1
            if "publish_date" in finding.metadata:
                score += 0.1
        
        return min(score, 1.0), feedback
    
    async def _validate_temporal_relevance(
        self,
        rule: ValidationRule,
        finding: ResearchFinding
    ) -> Tuple[float, List[str]]:
        """Validate temporal relevance."""
        max_age = rule.metadata["max_age_days"]
        
        # Check timestamp in metadata
        timestamp = None
        if "publish_date" in finding.metadata:
            try:
                timestamp = datetime.fromisoformat(
                    finding.metadata["publish_date"]
                )
            except (ValueError, TypeError):
                pass
        
        if not timestamp:
            timestamp = finding.timestamp
        
        age_days = (datetime.utcnow() - timestamp).days
        
        if age_days > max_age:
            return 0.0, [f"Content too old: {age_days} days"]
        
        score = 1.0 - (age_days / max_age)
        return score, []
    
    async def _validate_internal_consistency(
        self,
        rule: ValidationRule,
        finding: ResearchFinding
    ) -> Tuple[float, List[str]]:
        """Validate consistency with existing knowledge."""
        try:
            # Get content embedding
            content_embedding = await self.alignment.align(
                finding.content,
                finding.content_type
            )
            
            # Search contradicting content
            contradictions = await self.store.vector_store.search_similar(
                content_embedding,
                limit=5,
                min_similarity=0.5
            )
            
            if not contradictions:
                return 0.8, []  # No contradictions found
            
            # Check for semantic contradictions
            contradiction_scores = []
            for entity in contradictions:
                similarity = await self.alignment.compare(
                    finding.content,
                    entity.content,
                    finding.content_type,
                    entity.content_type
                )
                contradiction_scores.append(similarity)
            
            # High similarity is good (consistent)
            avg_consistency = np.mean(contradiction_scores)
            return avg_consistency, []
        
        except Exception as e:
            return 0.0, [f"Error in consistency check: {e}"]
    
    async def _validate_cross_modal_consistency(
        self,
        rule: ValidationRule,
        finding: ResearchFinding
    ) -> Tuple[float, List[str]]:
        """Validate consistency across modalities."""
        if finding.content_type == ContentType.TEXT:
            return 1.0, []  # Text doesn't need cross-modal validation
        
        try:
            # Get content embedding
            content_embedding = await self.alignment.align(
                finding.content,
                finding.content_type
            )
            
            # Search related text content
            text_entities = await self.store.vector_store.search_similar(
                content_embedding,
                limit=5,
                content_type=ContentType.TEXT
            )
            
            if not text_entities:
                return 0.5, ["No text content found for cross-modal validation"]
            
            # Check cross-modal consistency
            consistency_scores = []
            for entity in text_entities:
                score = await self.alignment.compare(
                    finding.content,
                    entity.content,
                    finding.content_type,
                    ContentType.TEXT
                )
                consistency_scores.append(score)
            
            avg_consistency = np.mean(consistency_scores)
            return avg_consistency, []
        
        except Exception as e:
            return 0.0, [f"Error in cross-modal check: {e}"]
    
    async def _validate_language_quality(
        self,
        rule: ValidationRule,
        finding: ResearchFinding
    ) -> Tuple[float, List[str]]:
        """Validate language quality."""
        if finding.content_type != ContentType.TEXT:
            return 1.0, []
        
        score = 0.5  # Base score
        feedback = []
        
        try:
            text = finding.content
            
            # Basic checks
            if len(text.split()) < 3:
                feedback.append("Text too short")
                return 0.0, feedback
            
            # Check sentence structure
            sentences = text.split(".")
            if len(sentences) < 2:
                feedback.append("Single sentence")
                score -= 0.1
            
            # Check language
            if finding.metadata.get("language") == self.config["language"]:
                score += 0.2
            
            # Could add more sophisticated checks
            
            return max(0.0, score), feedback
        
        except Exception as e:
            return 0.0, [f"Error in language check: {e}"]
    
    async def _validate_media_quality(
        self,
        rule: ValidationRule,
        finding: ResearchFinding
    ) -> Tuple[float, List[str]]:
        """Validate media quality."""
        if finding.content_type == ContentType.TEXT:
            return 1.0, []
        
        score = 0.5  # Base score
        feedback = []
        
        try:
            # Image-specific checks
            if finding.content_type == ContentType.IMAGE:
                if hasattr(finding.content, "size"):
                    width, height = finding.content.size
                    if width < 100 or height < 100:
                        feedback.append("Image too small")
                        score -= 0.2
                    elif width > 4000 or height > 4000:
                        feedback.append("Image too large")
                        score -= 0.1
            
            # Audio-specific checks
            elif finding.content_type == ContentType.AUDIO:
                if hasattr(finding.content, "shape"):
                    duration = finding.content.shape[0] / 16000  # Assuming 16kHz
                    if duration < 1.0:
                        feedback.append("Audio too short")
                        score -= 0.2
                    elif duration > 300:  # 5 minutes
                        feedback.append("Audio too long")
                        score -= 0.1
            
            return max(0.0, score), feedback
        
        except Exception as e:
            return 0.0, [f"Error in media check: {e}"]
    
    def _calculate_confidence(self, scores: Dict[str, float]) -> float:
        """Calculate overall confidence from rule scores."""
        if not scores:
            return 0.0
        
        # Weight scores by rule priority
        weighted_scores = []
        total_weight = 0
        
        for rule in self.rules:
            if rule.name in scores:
                weight = 1.0 / rule.priority  # Higher priority = higher weight
                weighted_scores.append(scores[rule.name] * weight)
                total_weight += weight
        
        if not weighted_scores:
            return 0.0
        
        return sum(weighted_scores) / total_weight
