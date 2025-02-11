"""
Interfaz web usando Streamlit.
"""
import streamlit as st
from streamlit_webrtc import webrtc_streamer, WebRtcMode
import av
import numpy as np
import logging
import asyncio
from typing import Optional
from ...core.base import AgentInterface, AgentContext
from ..voice.audio_processor import AudioManager
from ...core.config import AGENT_CONFIG

class StreamlitInterface(AgentInterface):
    """Interfaz web usando Streamlit."""
    
    def __init__(self):
        super().__init__("streamlit_interface")
        self.audio_manager = AudioManager()
        self.config = AGENT_CONFIG["interfaces"]["web"]
        
        # Configuración de la página
        st.set_page_config(
            page_title="Asistente Nutricional",
            page_icon="🎙️",
            layout="wide"
        )
    
    async def initialize(self) -> None:
        """Inicializa la interfaz."""
        await self.audio_manager.initialize()
        self._is_initialized = True
    
    async def shutdown(self) -> None:
        """Limpia recursos."""
        await self.audio_manager.shutdown()
    
    async def start(self) -> None:
        """Inicia la interfaz web."""
        if not self.is_initialized():
            await self.initialize()
        
        self._setup_session_state()
        self._render_interface()
    
    async def stop(self) -> None:
        """Detiene la interfaz."""
        await self.shutdown()
    
    async def send_response(self, response: str, context: AgentContext) -> None:
        """Muestra una respuesta en la interfaz."""
        if "responses" not in st.session_state:
            st.session_state.responses = []
        st.session_state.responses.append({
            "text": response,
            "timestamp": context.metadata.get("timestamp")
        })
    
    def _setup_session_state(self):
        """Configura el estado de la sesión."""
        if "context" not in st.session_state:
            st.session_state.context = AgentContext(
                session_id=str(hash(time.time())),
                language=AGENT_CONFIG["language"]
            )
        
        for key in ["transcription", "responses", "is_listening"]:
            if key not in st.session_state:
                st.session_state[key] = "" if key == "transcription" else []
    
    def _render_interface(self):
        """Renderiza la interfaz de usuario."""
        st.title("🎙️ Asistente Nutricional")
        st.write("Haz tus preguntas sobre nutrición deportiva y te responderé al instante.")
        
        # Columnas para organizar la interfaz
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🎤 Entrada de Voz")
            
            # WebRTC Streamer para captura de audio
            webrtc_ctx = webrtc_streamer(
                key="speech-to-text",
                mode=WebRtcMode.SENDONLY,
                audio_receiver_size=1024,
                video_frame_callback=self._video_frame_callback,
                audio_frame_callback=self._audio_frame_callback,
                rtc_configuration={"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]},
                media_stream_constraints={"video": False, "audio": True},
            )
            
            # Actualizar estado de escucha
            if webrtc_ctx.state.playing:
                asyncio.run(self.audio_manager.start_listening(st.session_state.context))
            else:
                asyncio.run(self.audio_manager.stop_listening())
            
            # Mostrar estado actual
            if webrtc_ctx.state.playing:
                st.info("🎤 Escuchando... Habla ahora!")
            else:
                st.warning("⏸️ Grabación pausada")
        
        with col2:
            st.subheader("💬 Transcripción y Respuesta")
            
            # Mostrar transcripción
            if st.session_state.transcription:
                st.text_area("Tu pregunta:", st.session_state.transcription, height=100)
            
            # Mostrar respuestas
            if st.session_state.responses:
                for response in st.session_state.responses:
                    st.text_area(
                        f"Respuesta ({response['timestamp']}):",
                        response["text"],
                        height=200
                    )
        
        # Información adicional
        with st.expander("ℹ️ Instrucciones"):
            st.write("""
            1. Haz clic en START para activar el micrófono
            2. Realiza tu pregunta sobre nutrición deportiva
            3. La transcripción aparecerá automáticamente
            4. Recibirás una respuesta basada en conocimiento especializado
            5. Haz clic en STOP cuando termines
            """)
    
    def _video_frame_callback(self, frame):
        """Callback para procesar frames de video (no usado)."""
        return frame
    
    async def _audio_frame_callback(self, frame):
        """Callback para procesar frames de audio."""
        if not st.session_state.is_listening:
            return frame
        
        try:
            # Procesar audio
            audio_data = frame.to_ndarray()
            text = await self.audio_manager.process(audio_data, st.session_state.context)
            
            # Actualizar transcripción si hay texto nuevo
            if text:
                st.session_state.transcription = text
                
        except Exception as e:
            self.logger.error(f"Error procesando audio: {e}")
        
        return frame
