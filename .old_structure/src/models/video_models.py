"""
Modelos para representar el conocimiento extraído de videos.
"""

from typing import List, Dict, Optional
from pydantic import BaseModel

class KnowledgeDomain(BaseModel):
    """Dominio de conocimiento."""
    name: str
    confidence: float
    sub_domains: List[str] = []
    key_concepts: List[str] = []
    description: str = ""

class VideoMetadata(BaseModel):
    """Metadatos de un video."""
    title: str
    channel: str
    duration: float
    views: int
    likes: int
    description: str

class VideoFrame(BaseModel):
    """Frame de un video."""
    timestamp: float
    image_path: str
    objects: List[str] = []
    text: str = ""
    relevance_score: float = 0.0

class VideoFragment(BaseModel):
    """Fragmento de un video."""
    text: str
    start_time: float
    end_time: float
    knowledge_domains: List[KnowledgeDomain] = []
    knowledge_graph: Dict = {}
    semantic_type: str = ""  # e.g., "definition", "example", "procedure"
    importance_score: float = 0.0

class EnhancedVideoKnowledge(BaseModel):
    """Conocimiento extraído de un video."""
    url: str
    video_id: str
    transcript: str
    fragments: List[VideoFragment] = []
    knowledge_domains: List[KnowledgeDomain] = []
    knowledge_graph: Dict = {}
