"""
Procesador de videos de YouTube.
"""
import asyncio
import logging
import re
from typing import Dict, List, Optional, Tuple, Any

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter
from youtube_transcript_api._errors import (
    TranscriptsDisabled,
    NoTranscriptFound,
    VideoUnavailable,
    TooManyRequests
)

from ..core.base import AgentProcessor
from ..core.context import AgentContext

logger = logging.getLogger(__name__)

class YouTubeProcessor(AgentProcessor):
    """Procesador de videos de YouTube."""

    def __init__(self, api_key: str, youtube_client=None, transcript_api=None):
        """Inicializa el procesador.
        
        Args:
            api_key: Clave de API de YouTube.
            youtube_client: Cliente de YouTube (para testing).
            transcript_api: API de transcripción (para testing).
        """
        super().__init__(name="youtube_processor")
        self.api_key = api_key
        self.youtube = youtube_client
        self.transcript_api = transcript_api or YouTubeTranscriptApi

    async def initialize(self):
        """Inicializa el procesador."""
        if not self.youtube:
            self.youtube = build('youtube', 'v3', developerKey=self.api_key)

    async def shutdown(self):
        """Cierra el procesador."""
        if self.youtube:
            await asyncio.get_event_loop().run_in_executor(
                None,
                self.youtube.close
            )
            self.youtube = None

    def is_initialized(self) -> bool:
        """Verifica si el procesador está inicializado."""
        return self.youtube is not None

    def extract_video_id(self, url: str) -> str:
        """Extrae el ID del video de una URL de YouTube.
        
        Args:
            url: URL del video.
            
        Returns:
            ID del video.
            
        Raises:
            ValueError: Si la URL no es válida.
        """
        # Patrones de URL soportados
        patterns = [
            r'(?:v=|\/)([0-9A-Za-z_-]{11}).*',
            r'youtu\.be\/([0-9A-Za-z_-]{11})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        raise ValueError("URL de YouTube inválida")

    async def _get_transcript(self, video_id: str, context: AgentContext) -> Dict[str, str]:
        """Obtiene la transcripción de un video.
        
        Args:
            video_id: ID del video.
            context: Contexto del agente.
            
        Returns:
            Dict con la transcripción y metadata de error si existe.
        """
        result = {
            "transcript": "",
            "error": None
        }
        
        try:
            # Obtener lista de transcripciones disponibles
            transcript_list = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.transcript_api.list_transcripts(video_id)
            )
            
            # Intentar obtener transcripción en el idioma del contexto
            try:
                transcript = transcript_list.find_transcript([context.language])
            except NoTranscriptFound:
                # Si no hay transcripción en el idioma del contexto, usar la primera disponible
                transcript = transcript_list.find_transcript(['en'])
            
            # Obtener el texto de la transcripción
            transcript_parts = await asyncio.get_event_loop().run_in_executor(
                None,
                transcript.fetch
            )
            
            # Unir todas las partes de la transcripción
            result["transcript"] = " ".join(part["text"] for part in transcript_parts)
            
        except NoTranscriptFound:
            logger.error(f"No se encontró transcripción para el video {video_id}")
            result["error"] = "No transcript found for this video"
        except TranscriptsDisabled:
            logger.error(f"Transcripciones deshabilitadas para el video {video_id}")
            result["error"] = "Transcripts are disabled for this video"
        except VideoUnavailable:
            logger.error(f"Video {video_id} no disponible")
            result["error"] = "Video is unavailable"
        except TooManyRequests:
            logger.error(f"Demasiadas peticiones para el video {video_id}")
            result["error"] = "Too many requests"
        except Exception as e:
            logger.error(f"Error inesperado obteniendo transcripción: {e}")
            result["error"] = f"Unexpected error: {str(e)}"
        
        return result

    async def _get_video_info(self, video_id: str) -> Dict[str, str]:
        """Obtiene información del video.
        
        Args:
            video_id: ID del video.
            
        Returns:
            Dict con información del video.
        """
        result = {
            "title": "",
            "channel": "",
            "views": "0",
            "likes": "0",
            "error": None
        }
        
        try:
            # Obtener información del video usando la API de YouTube
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.youtube.videos().list(
                    part="snippet,statistics",
                    id=video_id
                ).execute()
            )
            
            # Extraer información relevante
            if response and response.get("items"):
                video_info = response["items"][0]
                snippet = video_info.get("snippet", {})
                statistics = video_info.get("statistics", {})
                
                result.update({
                    "title": snippet.get("title", ""),
                    "channel": snippet.get("channelTitle", ""),
                    "views": statistics.get("viewCount", "0"),
                    "likes": statistics.get("likeCount", "0")
                })
            else:
                result["error"] = "Video not found"
            
        except HttpError as e:
            logger.error(f"HTTP error obteniendo información del video {video_id}: {e}")
            result["error"] = f"HTTP error: {str(e)}"
        except Exception as e:
            logger.error(f"Error inesperado obteniendo información del video {video_id}: {e}")
            result["error"] = f"Unexpected error: {str(e)}"
        
        return result

    async def process(self, input_data: str, context: AgentContext) -> Dict[str, Any]:
        """Procesa un video de YouTube.
        
        Args:
            input_data: URL del video.
            context: Contexto del agente.
            
        Returns:
            Dict con información del video y transcripción.
            
        Raises:
            ValueError: Si la URL no es válida.
        """
        # Extraer ID del video
        video_id = self.extract_video_id(input_data)
        
        # Obtener información del video y transcripción en paralelo
        video_info_task = asyncio.create_task(self._get_video_info(video_id))
        transcript_task = asyncio.create_task(self._get_transcript(video_id, context))
        
        # Esperar a que ambas tareas terminen
        video_info, transcript_result = await asyncio.gather(video_info_task, transcript_task)
        
        # Combinar resultados
        result = {
            "title": video_info["title"],
            "channel": video_info["channel"],
            "views": video_info["views"],
            "likes": video_info["likes"],
            "transcript": transcript_result["transcript"],
            "error": transcript_result["error"] or video_info["error"]
        }
        
        return result
