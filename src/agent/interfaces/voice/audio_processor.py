"""
Procesador de audio para la interfaz de voz.
"""
from typing import List, Optional, Dict, Any
import numpy as np
import whisper
import queue
import logging
from dataclasses import dataclass
from ...core.base import AgentProcessor, AgentContext
from ...core.config import AGENT_CONFIG

@dataclass
class AudioChunk:
    """Chunk de audio para procesar."""
    data: np.ndarray
    timestamp: float
    sample_rate: int

class WhisperProcessor(AgentProcessor):
    """Procesador de audio usando Whisper."""
    
    def __init__(self):
        super().__init__("whisper_processor")
        self.model = None
        self.audio_buffer: List[np.ndarray] = []
        self.text_queue = queue.Queue()
        self.config = AGENT_CONFIG["models"]["whisper"]
    
    async def initialize(self) -> None:
        """Inicializa el modelo Whisper."""
        self.logger.info(f"Cargando modelo Whisper {self.config['model']}...")
        self.model = whisper.load_model(self.config["model"])
        self._is_initialized = True
    
    async def shutdown(self) -> None:
        """Limpia recursos."""
        self.audio_buffer.clear()
        while not self.text_queue.empty():
            self.text_queue.get_nowait()
    
    async def process(self, audio_chunk: AudioChunk, context: AgentContext) -> Optional[str]:
        """Procesa un chunk de audio y retorna la transcripción si está disponible."""
        if not self.is_initialized():
            raise RuntimeError("WhisperProcessor no está inicializado")
        
        # Agregar chunk al buffer
        self.audio_buffer.append(audio_chunk.data)
        
        # Procesar si hay suficientes datos
        if len(self.audio_buffer) >= 30:  # ~1 segundo de audio
            audio_data = np.concatenate(self.audio_buffer)
            self.audio_buffer.clear()
            
            try:
                result = self.model.transcribe(
                    audio_data,
                    language=self.config["language"]
                )
                if result["text"].strip():
                    return result["text"]
            except Exception as e:
                self.logger.error(f"Error en transcripción: {e}")
        
        return None

class AudioManager(AgentProcessor):
    """Gestor de audio para la interfaz de voz."""
    
    def __init__(self):
        super().__init__("audio_manager")
        self.config = AGENT_CONFIG["interfaces"]["voice"]
        self.whisper = WhisperProcessor()
        self.is_listening = False
        self.current_context: Optional[AgentContext] = None
    
    async def initialize(self) -> None:
        """Inicializa el gestor de audio."""
        await self.whisper.initialize()
        self._is_initialized = True
    
    async def shutdown(self) -> None:
        """Limpia recursos."""
        await self.whisper.shutdown()
        self.is_listening = False
    
    async def start_listening(self, context: AgentContext) -> None:
        """Inicia la escucha de audio."""
        self.is_listening = True
        self.current_context = context
    
    async def stop_listening(self) -> None:
        """Detiene la escucha de audio."""
        self.is_listening = False
        self.current_context = None
    
    async def process(self, audio_data: np.ndarray, context: AgentContext) -> Optional[str]:
        """Procesa audio y retorna transcripción si está disponible."""
        if not self.is_listening or not self.is_initialized():
            return None
        
        chunk = AudioChunk(
            data=audio_data,
            timestamp=time.time(),
            sample_rate=self.config["sample_rate"]
        )
        
        return await self.whisper.process(chunk, context)
