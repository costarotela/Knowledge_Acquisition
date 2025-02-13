"""
Validation system for knowledge entities.
Ensures consistency and quality of knowledge representations.
"""

from datetime import datetime
from typing import List, Optional
from .models import KnowledgeEntity, ContentType, RelationType


class ValidationResult:
    def __init__(self):
        self.is_valid: bool = True
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.suggestions: List[str] = []

    def add_error(self, error: str):
        self.is_valid = False
        self.errors.append(error)

    def add_warning(self, warning: str):
        self.warnings.append(warning)

    def add_suggestion(self, suggestion: str):
        self.suggestions.append(suggestion)


class EntityValidator:
    """Base validator for knowledge entities."""

    def validate(self, entity: KnowledgeEntity) -> ValidationResult:
        """Perform comprehensive validation of a knowledge entity."""
        result = ValidationResult()
        
        # Validate basic structure
        self._validate_content(entity, result)
        self._validate_metadata(entity, result)
        self._validate_embeddings(entity, result)
        self._validate_relations(entity, result)
        self._validate_temporal(entity, result)
        
        return result

    def _validate_content(self, entity: KnowledgeEntity, result: ValidationResult):
        """Validate content based on content_type."""
        if entity.content is None:
            result.add_error("Content cannot be None")
            return

        if entity.content_type == ContentType.TEXT:
            if not isinstance(entity.content, str):
                result.add_error("Text content must be string")
        elif entity.content_type in [ContentType.IMAGE, ContentType.AUDIO, ContentType.VIDEO]:
            if not isinstance(entity.content, bytes):
                result.add_error(f"{entity.content_type} content must be bytes")
        elif entity.content_type == ContentType.STRUCTURED:
            if not isinstance(entity.content, dict):
                result.add_error("Structured content must be dictionary")

    def _validate_metadata(self, entity: KnowledgeEntity, result: ValidationResult):
        """Validate metadata completeness and consistency."""
        if entity.metadata is None:
            result.add_error("Metadata cannot be None")
            return

        if entity.content_type in [ContentType.AUDIO, ContentType.VIDEO]:
            if entity.metadata.duration is None:
                result.add_warning(f"Duration should be specified for {entity.content_type} content")

        if entity.content_type == ContentType.IMAGE:
            if entity.metadata.resolution is None:
                result.add_warning("Resolution should be specified for image content")

    def _validate_embeddings(self, entity: KnowledgeEntity, result: ValidationResult):
        """Validate embedding vectors."""
        if not entity.embeddings:
            result.add_warning("Entity has no embeddings")
            return

        dimensions = None
        for model, embedding in entity.embeddings.items():
            if not embedding:
                result.add_error(f"Empty embedding vector for model {model}")
                continue

            if dimensions is None:
                dimensions = len(embedding)
            elif len(embedding) != dimensions:
                result.add_error(f"Inconsistent embedding dimensions for model {model}")

    def _validate_relations(self, entity: KnowledgeEntity, result: ValidationResult):
        """Validate entity relations."""
        seen_targets = set()
        for relation in entity.relations:
            if relation.target_id == entity.id:
                result.add_error("Self-referential relation detected")
                
            if relation.target_id in seen_targets:
                result.add_warning(f"Duplicate relation to target {relation.target_id}")
            seen_targets.add(relation.target_id)

            if relation.confidence < 0 or relation.confidence > 1:
                result.add_error(f"Invalid confidence value {relation.confidence} for relation")

    def _validate_temporal(self, entity: KnowledgeEntity, result: ValidationResult):
        """Validate temporal consistency."""
        now = datetime.utcnow()
        
        if entity.created_at > now:
            result.add_error("Creation date is in the future")
            
        if entity.updated_at > now:
            result.add_error("Update date is in the future")
            
        if entity.updated_at < entity.created_at:
            result.add_error("Update date is before creation date")
