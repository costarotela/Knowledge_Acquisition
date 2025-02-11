"""
Procesador de videos de YouTube.
"""

import logging
from typing import List, Dict, Optional
import json
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter

from .models.video_models import (
    VideoMetadata, 
    VideoFrame,
    VideoFragment,
    KnowledgeDomain,
    EnhancedVideoKnowledge
)
from .processors.domain_categorizer import DomainCategorizer
from .processors.concept_extractor import ConceptExtractor

logger = logging.getLogger(__name__)

class YouTubeProcessor:
    """Procesa videos de YouTube para extraer conocimiento."""
    
    def __init__(self):
        """Inicializa el procesador."""
        self.domain_categorizer = DomainCategorizer()
        self.concept_extractor = ConceptExtractor()
        self.transcript_formatter = TextFormatter()
    
    def _get_video_id(self, url: str) -> str:
        """
        Extrae el ID del video de la URL.
        
        Args:
            url: URL del video
            
        Returns:
            ID del video
        """
        # TODO: Mejorar la extracción del ID para diferentes formatos de URL
        if "v=" in url:
            return url.split("v=")[1].split("&")[0]
        return url.split("/")[-1]
    
    def _get_transcript(self, video_id: str, lang: str = "en") -> str:
        """
        Obtiene la transcripción del video.
        
        Args:
            video_id: ID del video
            lang: Código de idioma
            
        Returns:
            Transcripción del video
        """
        try:
            transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=[lang])
            return self.transcript_formatter.format_transcript(transcript)
        except Exception as e:
            logger.error(f"Error al obtener transcripción: {e}")
            return ""
    
    def _create_fragment(self, text: str, start_time: float, end_time: float) -> VideoFragment:
        """
        Crea un fragmento de video con conocimiento extraído.
        
        Args:
            text: Texto del fragmento
            start_time: Tiempo de inicio
            end_time: Tiempo final
            
        Returns:
            Fragmento de video
        """
        # 1. Categorizar el contenido
        domains = self.domain_categorizer.categorize(text)
        
        # 2. Extraer grafo de conocimiento
        knowledge_graph = self.concept_extractor.extract_knowledge_graph(text, domains)
        
        # 3. Crear fragmento
        return VideoFragment(
            text=text,
            start_time=start_time,
            end_time=end_time,
            knowledge_domains=domains,
            knowledge_graph=knowledge_graph
        )
    
    def _split_transcript(self, transcript: str, chunk_size: int = 500) -> List[Dict]:
        """
        Divide la transcripción en fragmentos.
        
        Args:
            transcript: Transcripción completa
            chunk_size: Tamaño de cada fragmento
            
        Returns:
            Lista de fragmentos
        """
        words = transcript.split()
        chunks = []
        current_chunk = []
        current_size = 0
        
        for word in words:
            word_size = len(word) + 1  # +1 por el espacio
            if current_size + word_size > chunk_size and current_chunk:
                chunks.append(" ".join(current_chunk))
                current_chunk = [word]
                current_size = word_size
            else:
                current_chunk.append(word)
                current_size += word_size
        
        if current_chunk:
            chunks.append(" ".join(current_chunk))
        
        return [{"text": chunk, "start": 0.0, "end": 0.0} for chunk in chunks]
    
    def process_video(self, url: str) -> Optional[EnhancedVideoKnowledge]:
        """
        Procesa un video de YouTube para extraer conocimiento.
        
        Args:
            url: URL del video
            
        Returns:
            Conocimiento extraído del video
        """
        try:
            # 1. Obtener ID del video
            video_id = self._get_video_id(url)
            
            # 2. Obtener transcripción
            transcript = self._get_transcript(video_id)
            if not transcript:
                logger.error(f"No se pudo obtener transcripción para {url}")
                return None
            
            # 3. Dividir en fragmentos
            chunks = self._split_transcript(transcript)
            
            # 4. Procesar cada fragmento
            fragments = []
            for chunk in chunks:
                fragment = self._create_fragment(
                    text=chunk["text"],
                    start_time=chunk["start"],
                    end_time=chunk["end"]
                )
                fragments.append(fragment)
            
            # 5. Categorizar todo el contenido
            all_domains = self.domain_categorizer.categorize(transcript)
            
            # 6. Extraer grafo de conocimiento completo
            knowledge_graph = self.concept_extractor.extract_knowledge_graph(transcript, all_domains)
            
            # 7. Crear objeto de conocimiento
            return EnhancedVideoKnowledge(
                url=url,
                video_id=video_id,
                transcript=transcript,
                fragments=fragments,
                knowledge_domains=all_domains,
                knowledge_graph=knowledge_graph
            )
            
        except Exception as e:
            logger.error(f"Error al procesar video {url}: {e}")
            return None
