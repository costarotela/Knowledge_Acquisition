"""
Modelos de datos para el sistema.
"""

from .video_models import (
    VideoMetadata,
    VideoFrame,
    VideoFragment,
    KnowledgeDomain,
    EnhancedVideoKnowledge
)

class VideoContent:
    """Contenido extraído de un video."""
    def __init__(self, url: str, transcript: str = "", key_frames: list = None,
                 duration: float = 0.0, relevance_score: float = 0.0,
                 knowledge_domains: list = None):
        self.url = url
        self.transcript = transcript
        self.key_frames = key_frames or []
        self.duration = duration
        self.relevance_score = relevance_score
        self.knowledge_domains = knowledge_domains or []

__all__ = [
    'VideoContent',
    'VideoMetadata',
    'VideoFrame',
    'VideoFragment',
    'KnowledgeDomain',
    'EnhancedVideoKnowledge'
]
