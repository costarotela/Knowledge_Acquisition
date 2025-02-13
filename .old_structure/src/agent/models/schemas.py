from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

class VideoSegment(BaseModel):
    """Segmento de video con su contexto y metadatos."""
    content: str = Field(..., description="Contenido del segmento")
    start_time: float = Field(..., description="Tiempo de inicio en segundos")
    end_time: float = Field(..., description="Tiempo final en segundos")
    embedding: List[float] = Field(..., description="Vector de embedding del contenido")
    keywords: List[str] = Field(default_factory=list, description="Palabras clave extraídas")
    topics: List[str] = Field(default_factory=list, description="Temas identificados")
    sentiment: Optional[float] = Field(None, description="Puntuación de sentimiento (-1 a 1)")

class VideoKnowledge(BaseModel):
    """Conocimiento estructurado extraído de un video."""
    title: str = Field(..., description="Título del video")
    channel: str = Field(..., description="Canal del video")
    url: str = Field(..., description="URL del video")
    segments: List[VideoSegment] = Field(..., description="Segmentos del video")
    summary: str = Field(..., description="Resumen general del video")
    main_topics: List[str] = Field(..., description="Temas principales del video")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadatos adicionales")
    processed_at: datetime = Field(default_factory=datetime.now, description="Fecha de procesamiento")

class SearchQuery(BaseModel):
    """Consulta de búsqueda estructurada."""
    query: str = Field(..., description="Consulta original del usuario")
    intent: str = Field(..., description="Intención detectada de la consulta")
    keywords: List[str] = Field(..., description="Palabras clave extraídas")
    topics: List[str] = Field(..., description="Temas relacionados")
    constraints: Dict[str, Any] = Field(default_factory=dict, description="Restricciones de búsqueda")

class SearchResult(BaseModel):
    """Resultado de búsqueda estructurado."""
    video: VideoKnowledge = Field(..., description="Video fuente")
    relevant_segments: List[VideoSegment] = Field(..., description="Segmentos relevantes")
    score: float = Field(..., description="Puntuación de relevancia")
    explanation: str = Field(..., description="Explicación de por qué es relevante")

class RAGResponse(BaseModel):
    """Respuesta estructurada del sistema RAG."""
    answer: str = Field(..., description="Respuesta generada")
    sources: List[SearchResult] = Field(..., description="Fuentes utilizadas")
    confidence: float = Field(..., description="Confianza en la respuesta (0-1)")
    reasoning: str = Field(..., description="Razonamiento detrás de la respuesta")
    follow_up: List[str] = Field(default_factory=list, description="Preguntas de seguimiento sugeridas")
