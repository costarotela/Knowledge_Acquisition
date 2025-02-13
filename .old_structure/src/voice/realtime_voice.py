from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
import whisper
import numpy as np
import asyncio
from typing import List, Optional
import sounddevice as sd
import json
import logging
from datetime import datetime
import os

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Asistente Nutricional en Tiempo Real",
    description="Interfaz de voz en tiempo real para consultas nutricionales"
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AudioProcessor:
    def __init__(self):
        self.buffer: List[bytes] = []
        self.processing = False
        self.sample_rate = 16000
        self.channels = 1
        self.model = whisper.load_model("tiny")
        logger.info("🔄 Modelo Whisper inicializado")
        
    async def process_audio(self, audio_chunk: bytes) -> Optional[str]:
        self.buffer.append(audio_chunk)
        
        # Procesar cuando el buffer alcance cierto tamaño
        if len(self.buffer) >= 5 and not self.processing:
            self.processing = True
            try:
                # Convertir buffer a numpy array
                audio_data = np.frombuffer(b''.join(self.buffer), dtype=np.float32)
                
                # Procesar con Whisper
                result = self.model.transcribe(audio_data, language="es")
                
                # Limpiar buffer
                self.buffer = []
                return result["text"]
            except Exception as e:
                logger.error(f"Error procesando audio: {e}")
                return None
            finally:
                self.processing = False
        return None

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.audio_processor = AudioProcessor()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"Nueva conexión establecida. Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        logger.info(f"Conexión cerrada. Total: {len(self.active_connections)}")

    async def process_audio_stream(self, websocket: WebSocket):
        try:
            while True:
                # Recibir chunk de audio
                audio_chunk = await websocket.receive_bytes()
                
                # Procesar audio
                transcription = await self.audio_processor.process_audio(audio_chunk)
                
                if transcription:
                    # Enviar transcripción al cliente
                    await websocket.send_json({
                        "type": "transcription",
                        "text": transcription
                    })
                    
                    # TODO: Procesar con el RAG y enviar respuesta
                    response = f"Procesando tu pregunta: {transcription}"
                    await websocket.send_json({
                        "type": "response",
                        "text": response
                    })
                    
        except Exception as e:
            logger.error(f"Error en el stream de audio: {e}")

manager = ConnectionManager()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        await manager.process_audio_stream(websocket)
    except Exception as e:
        logger.error(f"Error en la conexión WebSocket: {e}")
    finally:
        manager.disconnect(websocket)

@app.on_event("startup")
async def startup_event():
    logger.info("🚀 Servidor iniciado y listo para procesar audio")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
