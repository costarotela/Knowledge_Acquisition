"""
Inicialización del paquete knowledge_acquisition.
"""

from .models import VideoContent
from .models.video_models import (
    VideoMetadata,
    VideoFrame,
    VideoFragment,
    KnowledgeDomain,
    EnhancedVideoKnowledge
)

__all__ = [
    'VideoMetadata',
    'VideoFrame',
    'VideoFragment',
    'KnowledgeDomain',
    'EnhancedVideoKnowledge',
    'VideoContent'
]
