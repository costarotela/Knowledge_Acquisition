"""
Interfaz web del agente nutricional usando Streamlit.
"""
from typing import Dict, Any, Optional
import streamlit as st
import queue
import threading
import logging
import os
import asyncio
from ...core.base import AgentInterface, AgentContext
from ...core.config import AGENT_CONFIG
from ...models.rag_model import AgenticNutritionRAG
from ..voice.audio_processor import AudioProcessor

logger = logging.getLogger(__name__)

class StreamlitInterface(AgentInterface):
    """Interfaz web usando Streamlit."""
    
    def __init__(self):
        """Inicializa la interfaz web."""
        super().__init__("web_interface")
        self.rag_model = AgenticNutritionRAG()
        self.audio_processor = AudioProcessor()
        
        # Estado de la aplicación
        if 'session_context' not in st.session_state:
            st.session_state.session_context = AgentContext(
                session_id=str(hash(threading.current_thread())),
                language=AGENT_CONFIG["language"]
            )
        
        if 'is_recording' not in st.session_state:
            st.session_state.is_recording = False
        
        if 'debug_queue' not in st.session_state:
            st.session_state.debug_queue = queue.Queue()
            
        if 'audio_queue' not in st.session_state:
            st.session_state.audio_queue = queue.Queue()
            
        if 'transcription' not in st.session_state:
            st.session_state.transcription = ""
            
        if 'response' not in st.session_state:
            st.session_state.response = ""
            
        if 'debug_info' not in st.session_state:
            st.session_state.debug_info = ""
            
        if 'is_admin' not in st.session_state:
            st.session_state.is_admin = False
    
    async def initialize(self) -> None:
        """Inicializa la interfaz y sus componentes."""
        try:
            await self.rag_model.initialize()
            await self.audio_processor.initialize()
            self._is_initialized = True
            logger.info("Interfaz web inicializada")
        except Exception as e:
            logger.error(f"Error inicializando interfaz web: {str(e)}")
            raise
    
    async def shutdown(self) -> None:
        """Limpia recursos."""
        try:
            await self.rag_model.shutdown()
            await self.audio_processor.shutdown()
            self._is_initialized = False
            logger.info("Interfaz web cerrada")
        except Exception as e:
            logger.error(f"Error cerrando interfaz web: {str(e)}")
            raise
    
    async def start(self) -> None:
        """Inicia la interfaz web."""
        try:
            # Configuración de la página
            st.set_page_config(
                page_title="Asistente Nutricional",
                page_icon="🎙️",
                layout="wide"
            )
            
            # Interfaz principal
            st.title("🎙️ Asistente Nutricional")
            
            # Tabs para diferentes funcionalidades
            tab1, tab2 = st.tabs(["💬 Consultas", "🔧 Administración"])
            
            with tab1:
                await self._render_query_interface()
            
            with tab2:
                await self._render_admin_interface()
            
            # Información adicional
            with st.expander("ℹ️ Instrucciones"):
                self._render_instructions()
                
        except Exception as e:
            logger.error(f"Error iniciando interfaz web: {str(e)}")
            raise
    
    async def stop(self) -> None:
        """Detiene la interfaz web."""
        try:
            if st.session_state.is_recording:
                st.session_state.is_recording = False
                if hasattr(st.session_state, 'recording_thread'):
                    st.session_state.recording_thread.do_run = False
                    st.session_state.recording_thread.join()
        except Exception as e:
            logger.error(f"Error deteniendo interfaz web: {str(e)}")
            raise
    
    async def _render_query_interface(self):
        """Renderiza la interfaz de consultas."""
        st.write("Haz tus preguntas sobre nutrición deportiva y te responderé al instante.")
        
        # Columnas para organizar la interfaz
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🎤 Entrada de Voz")
            
            # Botón de grabación
            if st.button("🎙️ " + ("Detener Grabación" if st.session_state.is_recording else "Iniciar Grabación")):
                if not st.session_state.is_recording:
                    await self._start_recording()
                else:
                    await self._stop_recording()
            
            # Mostrar estado de grabación
            if st.session_state.is_recording:
                st.info("🎤 Grabando... Habla ahora!")
            else:
                st.write("⏸️ Listo para grabar")
            
            # Mostrar información de depuración
            with st.expander("🔍 Información de Depuración", expanded=True):
                await self._update_debug_info()
        
        with col2:
            st.subheader("💬 Transcripción y Respuesta")
            
            # Mostrar transcripción
            if st.session_state.transcription:
                st.write("**Tu pregunta:**")
                st.write(st.session_state.transcription)
            
            # Mostrar respuesta
            if st.session_state.response:
                st.write("**Respuesta:**")
                st.write(st.session_state.response)
    
    async def _render_admin_interface(self):
        """Renderiza la interfaz de administración."""
        st.subheader("🔐 Acceso Administrativo")
        
        # Login de administrador
        if not st.session_state.is_admin:
            with st.form("login_form"):
                password = st.text_input("Contraseña de Administrador", type="password")
                submit = st.form_submit_button("Acceder")
                if submit:
                    if password == os.getenv("ADMIN_PASSWORD", "admin"):
                        st.session_state.is_admin = True
                        st.rerun()
                    else:
                        st.error("Contraseña incorrecta")
        else:
            st.success("✅ Acceso concedido")
            await self._render_knowledge_management()
    
    async def _render_knowledge_management(self):
        """Renderiza la gestión de conocimiento."""
        st.subheader("📚 Gestión de Conocimiento")
        
        # Agregar video de YouTube
        with st.expander("🎥 Agregar Video de YouTube"):
            with st.form("youtube_form"):
                video_url = st.text_input("URL del Video")
                process = st.form_submit_button("Procesar Video")
                if process and video_url:
                    await self._process_youtube_video(video_url)
        
        # Ver estadísticas
        with st.expander("📊 Estadísticas de Conocimiento"):
            await self._show_knowledge_stats()
        
        # Explorar conocimiento
        with st.expander("🔍 Explorar Base de Conocimientos"):
            await self._explore_knowledge()
    
    def _render_instructions(self):
        """Renderiza las instrucciones."""
        st.write("""
        1. Haz clic en "Iniciar Grabación"
        2. Haz tu pregunta sobre nutrición deportiva
        3. Haz clic en "Detener Grabación"
        4. Espera a que se procese tu pregunta
        5. Lee la respuesta del asistente
        
        Para administradores:
        1. Accede a la pestaña "Administración"
        2. Ingresa con tu contraseña
        3. Agrega nuevos videos o explora la base de conocimientos
        """)
    
    async def _start_recording(self):
        """Inicia la grabación de audio."""
        st.session_state.is_recording = True
        st.session_state.debug_queue = queue.Queue()
        st.session_state.audio_queue = queue.Queue()
        
        recording_thread = threading.Thread(
            target=self.audio_processor.record_audio,
            args=(st.session_state.audio_queue, st.session_state.debug_queue),
            daemon=True
        )
        recording_thread.do_run = True
        recording_thread.start()
        st.session_state.recording_thread = recording_thread
    
    async def _stop_recording(self):
        """Detiene la grabación y procesa el audio."""
        st.session_state.is_recording = False
        if hasattr(st.session_state, 'recording_thread'):
            st.session_state.recording_thread.do_run = False
            st.session_state.recording_thread.join()
            
            try:
                audio_data = st.session_state.audio_queue.get_nowait()
                transcription = await self.audio_processor.transcribe(audio_data)
                if transcription:
                    st.session_state.transcription = transcription
                    response = await self.rag_model.predict(
                        transcription,
                        st.session_state.session_context
                    )
                    st.session_state.response = response.get("response", "")
            except queue.Empty:
                st.error("No se pudo obtener el audio grabado")
    
    async def _update_debug_info(self):
        """Actualiza la información de depuración."""
        while not st.session_state.debug_queue.empty():
            try:
                st.session_state.debug_info += st.session_state.debug_queue.get_nowait()
            except queue.Empty:
                break
        st.code(st.session_state.debug_info)
    
    async def _process_youtube_video(self, video_url: str):
        """Procesa un video de YouTube."""
        try:
            from ...models.youtube_processor import YouTubeProcessor
            processor = YouTubeProcessor(os.getenv("YOUTUBE_API_KEY"))
            await processor.initialize()
            
            with st.spinner("Procesando video..."):
                result = await processor.process(
                    video_url,
                    st.session_state.session_context
                )
                
                if "error" in result:
                    st.error(f"Error procesando video: {result['error']}")
                else:
                    st.success(f"Video procesado: {result['info']['title']}")
                    
            await processor.shutdown()
            
        except Exception as e:
            st.error(f"Error: {str(e)}")
    
    async def _show_knowledge_stats(self):
        """Muestra estadísticas de la base de conocimientos."""
        try:
            from ...models.knowledge_base import KnowledgeBase
            kb = KnowledgeBase()
            await kb.initialize()
            
            stats = await kb.get_statistics()
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Videos Procesados", stats.get("total_videos", 0))
            with col2:
                st.metric("Conceptos Extraídos", stats.get("total_concepts", 0))
            with col3:
                st.metric("Última Actualización", stats.get("last_update", "N/A"))
                
            await kb.shutdown()
            
        except Exception as e:
            st.error(f"Error obteniendo estadísticas: {str(e)}")
    
    async def _explore_knowledge(self):
        """Explora la base de conocimientos."""
        try:
            search = st.text_input("Buscar concepto o tema")
            if search:
                from ...models.knowledge_base import KnowledgeBase
                kb = KnowledgeBase()
                await kb.initialize()
                
                results = await kb.search(search)
                for item in results:
                    with st.container():
                        st.markdown(f"**{item['concept']}**")
                        st.write(item['content'])
                        st.caption(f"Fuente: {item['source_url']}")
                        st.divider()
                        
                await kb.shutdown()
                
        except Exception as e:
            st.error(f"Error buscando: {str(e)}")
