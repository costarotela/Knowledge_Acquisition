"""
Script de prueba para el procesamiento de video.
"""

import os
import logging
from dotenv import load_dotenv
import pytest
from datetime import datetime

from src.processors.video_processor import EnhancedVideoProcessor
from src.storage.video_storage import VideoStorage

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_youtube_processing():
    """Prueba el procesamiento completo de un video de YouTube."""
    try:
        # Cargar variables de entorno
        load_dotenv()
        
        # Configurar directorios
        base_dir = os.path.dirname(os.path.dirname(__file__))
        frames_dir = os.path.join(base_dir, "data", "frames")
        os.makedirs(frames_dir, exist_ok=True)
        
        # Inicializar procesador y storage
        processor = EnhancedVideoProcessor(
            frames_output_dir=frames_dir,
            text_model="all-MiniLM-L6-v2",
            visual_model="google/vit-base-patch16-224"
        )
        storage = VideoStorage()
        
        # URL de prueba (un video corto de ejemplo)
        video_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"  # Reemplazar con URL real
        
        # Procesar video
        logger.info(f"Procesando video de YouTube: {video_url}")
        knowledge = processor.process_youtube_url(video_url)
        
        # Verificar estructura básica
        assert knowledge.title is not None
        assert knowledge.channel is not None
        assert knowledge.url == video_url
        assert len(knowledge.fragments) > 0
        
        # Verificar metadatos específicos de YouTube
        assert "description" in knowledge.metadata
        assert "views" in knowledge.metadata
        assert "publish_date" in knowledge.metadata
        
        # Almacenar en base de datos
        logger.info("Almacenando resultados...")
        video_id = storage.store_video_knowledge(knowledge)
        assert video_id is not None
        
        # Probar búsqueda
        logger.info("Probando búsqueda...")
        results = storage.search_video_fragments(
            query_text=knowledge.title,  # Buscar usando el título del video
            match_threshold=0.7,
            match_count=5
        )
        
        assert len(results) > 0
        logger.info(f"Encontrados {len(results)} fragmentos relevantes")
        
        return True
        
    except Exception as e:
        logger.error(f"Error en prueba: {str(e)}")
        raise

if __name__ == "__main__":
    test_youtube_processing()
