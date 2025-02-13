"""
Modelos Pydantic para la base de conocimientos.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, validator
import numpy as np

class ContentType(str, Enum):
    """Tipos de contenido soportados."""
    VIDEO = "video"
    ARTICLE = "article"
    RESEARCH = "research"
    BOOK = "book"

class SourceMetadata(BaseModel):
    """Metadatos de la fuente de información."""
    url: str
    title: str
    author: Optional[str] = None
    published_date: Optional[datetime] = None
    language: str = "es"
    content_type: ContentType
    duration: Optional[int] = None  # En segundos para videos
    channel: Optional[str] = None   # Para videos
    publisher: Optional[str] = None # Para artículos/libros
    
class KnowledgeFragment(BaseModel):
    """Fragmento atómico de conocimiento."""
    id: Optional[str] = None
    content: str
    start_time: Optional[float] = None  # Para videos
    end_time: Optional[float] = None    # Para videos
    embedding: Optional[List[float]] = None
    keywords: List[str] = Field(default_factory=list)
    topics: List[str] = Field(default_factory=list)
    confidence_score: float = Field(ge=0.0, le=1.0)
    relevance_score: Optional[float] = None
    created_at: datetime = Field(default_factory=datetime.now)
    
    @validator("embedding")
    def validate_embedding(cls, v):
        """Valida que el embedding tenga la dimensión correcta."""
        if v is not None and len(v) != 384:  # Dimensión del modelo all-MiniLM-L6-v2
            raise ValueError("El embedding debe tener 384 dimensiones")
        return v

class Citation(BaseModel):
    """Citación o referencia."""
    text: str
    source_url: str
    context: Optional[str] = None
    page_number: Optional[int] = None
    accessed_date: datetime = Field(default_factory=datetime.now)

class KnowledgeItem(BaseModel):
    """Item completo de conocimiento."""
    id: Optional[str] = None
    source: SourceMetadata
    fragments: List[KnowledgeFragment]
    summary: str
    main_topics: List[str]
    citations: List[Citation] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    quality_metrics: Dict[str, float] = Field(default_factory=dict)
    processed_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None
    
    def calculate_quality_metrics(self) -> None:
        """Calcula métricas de calidad del item."""
        # Coherencia entre fragmentos
        fragment_similarities = []
        for i, frag1 in enumerate(self.fragments):
            for frag2 in self.fragments[i+1:]:
                if frag1.embedding and frag2.embedding:
                    sim = np.dot(frag1.embedding, frag2.embedding)
                    fragment_similarities.append(sim)
        
        if fragment_similarities:
            self.quality_metrics["coherence"] = float(np.mean(fragment_similarities))
            
        # Confianza promedio
        confidences = [f.confidence_score for f in self.fragments]
        self.quality_metrics["avg_confidence"] = float(np.mean(confidences))
        
        # Completitud
        self.quality_metrics["completeness"] = min(1.0, len(self.fragments) / 10)
        
        # Riqueza de metadatos
        metadata_fields = len([f for f in self.source.dict().values() if f is not None])
        self.quality_metrics["metadata_richness"] = metadata_fields / len(self.source.__fields__)

class KnowledgeQuery(BaseModel):
    """Query para buscar conocimiento."""
    query: str
    embedding: Optional[List[float]] = None
    filters: Dict[str, Any] = Field(default_factory=dict)
    min_confidence: float = 0.7
    max_results: int = 5
    include_metadata: bool = True
    
    @validator("max_results")
    def validate_max_results(cls, v):
        """Valida el número máximo de resultados."""
        if v < 1 or v > 20:
            raise ValueError("max_results debe estar entre 1 y 20")
        return v

class SearchResult(BaseModel):
    """Resultado de búsqueda."""
    item: KnowledgeItem
    relevance_score: float
    matching_fragments: List[KnowledgeFragment]
    context: Optional[str] = None
