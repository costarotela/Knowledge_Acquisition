"""
Procesador de videos de YouTube.
"""
import logging
from typing import Dict, Any, Optional
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import whisper
import yt_dlp
import os

logger = logging.getLogger(__name__)

class YouTubeProcessor:
    """Procesa videos de YouTube para extraer información."""
    
    def __init__(self, api_key: str):
        """Inicializa el procesador."""
        self.api_key = api_key
        self.youtube = build('youtube', 'v3', developerKey=api_key)
        self.formatter = TextFormatter()
        self.model = whisper.load_model("base")  # Modelo para transcripción
    
    async def process_video(self, video_url: str) -> Dict[str, Any]:
        """Procesa un video de YouTube."""
        try:
            # 1. Obtener ID del video
            video_id = self._extract_video_id(video_url)
            if not video_id:
                raise ValueError("URL de video inválida")
            
            # 2. Obtener metadata del video
            metadata = await self._get_video_metadata(video_id)
            
            # 3. Obtener transcripción
            transcript = await self._get_transcript(video_id)
            
            # 4. Si no hay transcripción oficial, usar whisper
            if not transcript:
                logger.info("No se encontró transcripción oficial, usando whisper")
                transcript = await self._transcribe_with_whisper(video_url)
            
            return {
                "video_id": video_id,
                "metadata": metadata,
                "transcript": transcript
            }
            
        except Exception as e:
            logger.error(f"Error procesando video: {str(e)}")
            raise
    
    def _extract_video_id(self, url: str) -> Optional[str]:
        """Extrae el ID del video de la URL."""
        # TODO: Implementar extracción de ID
        return None
    
    async def _get_video_metadata(self, video_id: str) -> Dict[str, Any]:
        """Obtiene metadata del video."""
        try:
            request = self.youtube.videos().list(
                part="snippet,contentDetails,statistics",
                id=video_id
            )
            response = request.execute()
            
            if not response["items"]:
                raise ValueError("Video no encontrado")
            
            video_data = response["items"][0]
            return {
                "title": video_data["snippet"]["title"],
                "description": video_data["snippet"]["description"],
                "channel": video_data["snippet"]["channelTitle"],
                "published_at": video_data["snippet"]["publishedAt"],
                "duration": video_data["contentDetails"]["duration"],
                "views": video_data["statistics"]["viewCount"],
                "likes": video_data["statistics"].get("likeCount", 0)
            }
            
        except HttpError as e:
            logger.error(f"Error de API de YouTube: {str(e)}")
            raise
    
    async def _get_transcript(self, video_id: str) -> Optional[str]:
        """Obtiene la transcripción oficial del video."""
        try:
            transcript_list = YouTubeTranscriptApi.get_transcript(
                video_id,
                languages=['es', 'en']
            )
            return self.formatter.format_transcript(transcript_list)
        except Exception as e:
            logger.warning(f"No se pudo obtener transcripción oficial: {str(e)}")
            return None
    
    async def _transcribe_with_whisper(self, video_url: str) -> str:
        """Transcribe el video usando whisper."""
        try:
            # 1. Descargar audio
            ydl_opts = {
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'outtmpl': 'temp_audio',
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([video_url])
            
            # 2. Transcribir audio
            result = self.model.transcribe("temp_audio.mp3")
            
            # 3. Limpiar archivos temporales
            os.remove("temp_audio.mp3")
            
            return result["text"]
            
        except Exception as e:
            logger.error(f"Error transcribiendo con whisper: {str(e)}")
            if os.path.exists("temp_audio.mp3"):
                os.remove("temp_audio.mp3")
            raise
