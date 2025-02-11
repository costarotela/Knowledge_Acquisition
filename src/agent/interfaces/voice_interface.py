"""
Interfaz de voz para el agente.
"""
import numpy as np
import logging
from typing import Dict, Any, Optional
import whisper
from src.agent.core.base import AgentInterface, AgentContext

logger = logging.getLogger(__name__)

class WhisperProcessor:
    """Procesador de audio usando Whisper."""
    
    def __init__(self):
        self.model = None
        self._initialized = False
    
    async def initialize(self):
        """Inicializa el procesador."""
        try:
            self.model = whisper.load_model("base")
            self._initialized = True
        except Exception as e:
            logger.error(f"Error inicializando Whisper: {e}")
            raise
    
    async def shutdown(self):
        """Cierra el procesador."""
        self.model = None
        self._initialized = False
    
    def is_initialized(self):
        """Verifica si el procesador está inicializado."""
        return self._initialized
    
    async def transcribe(self, audio: np.ndarray) -> str:
        """Transcribe audio usando Whisper."""
        try:
            if not self.is_initialized():
                raise RuntimeError("Whisper no está inicializado")
            
            # Convertir a float32 y normalizar
            audio = audio.astype(np.float32)
            if audio.max() > 1.0:
                audio = audio / audio.max()
            
            # Transcribir
            result = self.model.transcribe(audio)
            return result["text"].strip()
            
        except Exception as e:
            logger.error(f"Error transcribiendo audio: {e}")
            raise

class AudioManager(AgentInterface):
    """Gestor de audio."""
    
    def __init__(self, whisper_processor: WhisperProcessor):
        super().__init__("audio_manager")
        self.whisper = whisper_processor
        self._listening = False
    
    async def initialize(self):
        """Inicializa el gestor."""
        try:
            if not self.whisper.is_initialized():
                await self.whisper.initialize()
            self._initialized = True
        except Exception as e:
            logger.error(f"Error inicializando gestor de audio: {e}")
            raise
    
    async def shutdown(self):
        """Cierra el gestor."""
        try:
            if self.whisper.is_initialized():
                await self.whisper.shutdown()
            self._initialized = False
            self._listening = False
        except Exception as e:
            logger.error(f"Error cerrando gestor de audio: {e}")
            raise
    
    def is_initialized(self):
        """Verifica si el gestor está inicializado."""
        return self._initialized
    
    def is_listening(self):
        """Verifica si el gestor está escuchando."""
        return self._listening
    
    async def start(self, context: AgentContext):
        """Inicia el gestor."""
        try:
            if not self.is_initialized():
                await self.initialize()
            logger.info("Iniciando gestor de audio")
        except Exception as e:
            logger.error(f"Error iniciando gestor: {e}")
            raise
    
    async def stop(self):
        """Detiene el gestor."""
        try:
            await self.shutdown()
            logger.info("Deteniendo gestor de audio")
        except Exception as e:
            logger.error(f"Error deteniendo gestor: {e}")
            raise
    
    async def send_response(self, response: str, context: AgentContext):
        """Envía una respuesta."""
        # Por ahora solo logueamos la respuesta
        logger.info(f"Respuesta: {response}")
    
    async def start_listening(self, context: AgentContext):
        """Inicia la escucha."""
        try:
            if not self.is_initialized():
                raise RuntimeError("Gestor no inicializado")
            
            self._listening = True
            logger.info("Iniciando escucha de audio")
            
        except Exception as e:
            logger.error(f"Error iniciando escucha: {e}")
            raise
    
    async def stop_listening(self):
        """Detiene la escucha."""
        try:
            self._listening = False
            logger.info("Deteniendo escucha de audio")
            
        except Exception as e:
            logger.error(f"Error deteniendo escucha: {e}")
            raise
    
    async def process(self, input_data: np.ndarray, context: AgentContext) -> Dict[str, Any]:
        """Procesa audio."""
        try:
            if not self.is_listening():
                return {
                    "error": "No se está escuchando audio"
                }
            
            if input_data is None or len(input_data) < 1000:
                return {
                    "error": "Audio inválido"
                }
            
            # Transcribir audio
            text = await self.whisper.transcribe(input_data)
            
            return {
                "text": text,
                "metadata": {
                    "interface": self.name,
                    "language": context.language
                }
            }
            
        except Exception as e:
            logger.error(f"Error procesando audio: {e}")
            return {
                "error": str(e)
            }
