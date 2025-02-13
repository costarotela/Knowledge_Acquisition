"""
Manejador de almacenamiento de videos en Supabase.
"""

import os
from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid
import logging
from supabase import create_client
import numpy as np

from ..models.video_models import (
    VideoMetadata,
    VideoFrame,
    VideoFragment,
    EnhancedVideoKnowledge
)

logger = logging.getLogger(__name__)

class VideoStorage:
    """Manejador de almacenamiento de videos."""
    
    def __init__(self):
        """Inicializa la conexión con Supabase."""
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")
        
        if not supabase_url or not supabase_key:
            raise ValueError("SUPABASE_URL y SUPABASE_KEY son requeridas")
            
        self.supabase = create_client(supabase_url, supabase_key)
        
    def store_video_knowledge(self, knowledge: EnhancedVideoKnowledge) -> str:
        """
        Almacena el conocimiento estructurado de un video.
        
        Args:
            knowledge: Conocimiento estructurado del video
            
        Returns:
            UUID del video almacenado
        """
        try:
            # 1. Crear entrada en knowledge_items
            knowledge_item = {
                "source_url": knowledge.url,
                "concept": knowledge.title,
                "content": knowledge.summary,
                "evidence_score": knowledge.quality_metrics.get("visual_coverage", 0.0),
                "novelty_score": knowledge.quality_metrics.get("scene_diversity", 0.0),
                "category": "video",
                "embedding": knowledge.fragments[0].embedding if knowledge.fragments else None
            }
            
            result = self.supabase.table("knowledge_items").insert(knowledge_item).execute()
            knowledge_item_id = result.data[0]["id"]
            
            # 2. Crear video_knowledge_item
            video_item = {
                "id": str(uuid.uuid4()),
                "knowledge_item_id": knowledge_item_id,
                "summary": knowledge.summary,
                "main_topics": knowledge.main_topics,
                "metadata": knowledge.metadata,
                "quality_metrics": knowledge.quality_metrics,
                "processed_at": knowledge.processed_at.isoformat(),
                "video_metadata": knowledge.video_metadata.dict()
            }
            
            result = self.supabase.table("video_knowledge_items").insert(video_item).execute()
            video_item_id = result.data[0]["id"]
            
            # 3. Procesar fragmentos
            for fragment in knowledge.fragments:
                fragment_data = {
                    "id": str(uuid.uuid4()),
                    "video_item_id": video_item_id,
                    "content": fragment.content,
                    "start_time": fragment.start_time,
                    "end_time": fragment.end_time,
                    "keywords": fragment.keywords,
                    "topics": fragment.topics,
                    "confidence_score": fragment.confidence_score,
                    "embedding": fragment.embedding,
                    "frame_count": fragment.frame_count,
                    "scene_change": fragment.scene_change,
                    "visual_features": fragment.visual_features,
                    "frame_embeddings": [f.embedding for f in fragment.frames],
                    "dominant_colors": fragment.dominant_colors,
                    "motion_intensity": fragment.motion_intensity
                }
                
                result = self.supabase.table("knowledge_fragments").insert(fragment_data).execute()
                fragment_id = result.data[0]["id"]
                
                # 4. Procesar frames
                for frame in fragment.frames:
                    frame_data = {
                        "id": str(uuid.uuid4()),
                        "fragment_id": fragment_id,
                        "timestamp": frame.timestamp,
                        "frame_path": frame.frame_path,
                        "embedding": frame.embedding,
                        "objects_detected": frame.objects_detected,
                        "scene_score": frame.scene_score,
                        "visual_features": frame.visual_features
                    }
                    
                    self.supabase.table("video_frames").insert(frame_data).execute()
            
            return video_item_id
            
        except Exception as e:
            logger.error(f"Error almacenando video: {str(e)}")
            raise
            
    def search_video_fragments(
        self,
        query_text: str,
        visual_query: Optional[np.ndarray] = None,
        match_threshold: float = 0.7,
        match_count: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Busca fragmentos de video por similitud.
        
        Args:
            query_text: Texto de búsqueda
            visual_query: Embedding visual opcional
            match_threshold: Umbral de similitud
            match_count: Número máximo de resultados
            
        Returns:
            Lista de fragmentos encontrados
        """
        try:
            # Convertir query a embedding
            query_embedding = self.text_encoder.encode(query_text)
            
            # Llamar a función de búsqueda
            result = self.supabase.rpc(
                'match_video_fragments',
                {
                    'query_embedding': query_embedding.tolist(),
                    'visual_query_embedding': visual_query.tolist() if visual_query is not None else None,
                    'match_threshold': match_threshold,
                    'match_count': match_count
                }
            ).execute()
            
            return result.data
            
        except Exception as e:
            logger.error(f"Error en búsqueda: {str(e)}")
            raise
