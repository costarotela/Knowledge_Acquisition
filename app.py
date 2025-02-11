import streamlit as st
import logging
from src.auth.supabase_auth import SupabaseAuth
from src.supabase_knowledge_base import SupabaseKnowledgeBase
from src.youtube_processor import YouTubeProcessor
from src.agent.models.rag_model import AgenticNutritionRAG
import os
from dotenv import load_dotenv

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Cargar variables de entorno
load_dotenv()

# Configuración de la página
st.set_page_config(
    page_title="Knowledge Acquisition",
    page_icon="🧠",
    layout="wide"
)

# Inicializar estado de la sesión
if 'initialized' not in st.session_state:
    st.session_state.initialized = False

if not st.session_state.initialized:
    logger.info("Inicializando estado de la aplicación...")
    # Inicializar Supabase Auth
    if 'auth' not in st.session_state:
        logger.info("Inicializando autenticación de Supabase")
        st.session_state.auth = SupabaseAuth()
    
    # Inicializar YouTube Processor
    if 'youtube_processor' not in st.session_state:
        youtube_api_key = os.getenv('YOUTUBE_API_KEY')
        if not youtube_api_key:
            raise ValueError("YOUTUBE_API_KEY debe estar definida en .env")
        st.session_state.youtube_processor = YouTubeProcessor(youtube_api_key)
    
    # Inicializar Knowledge Base
    if 'knowledge_base' not in st.session_state:
        st.session_state.knowledge_base = SupabaseKnowledgeBase()
    
    # Inicializar RAG Agent
    if 'rag_agent' not in st.session_state:
        try:
            logger.info("Inicializando RAG Agent...")
            st.session_state.rag_agent = AgenticNutritionRAG()
            st.session_state.rag_agent.initialize()
            logger.info("RAG Agent inicializado correctamente")
        except Exception as e:
            logger.error(f"Error inicializando RAG Agent: {str(e)}", exc_info=True)
            st.error(f"Error inicializando el agente: {str(e)}")
            st.stop()
    
    st.session_state.initialized = True
    logger.info("Inicialización completada")

# Verificar si hay una sesión activa
if 'user' not in st.session_state:
    # Obtener usuario actual
    current_user = st.session_state.auth.get_current_user()
    if current_user:
        st.session_state.user = current_user
        st.session_state.is_admin = True
        logger.info(f"Sesión restaurada para: {current_user['email']}")

# Interfaz de usuario
st.title("🧠 Knowledge Acquisition")

# Tabs principales
tab1, tab2 = st.tabs(["🔍 Base de Conocimiento", "⚙️ Administración"])

with tab1:
    st.header("Base de Conocimiento")
    
    # Chat con el agente
    col1, col2 = st.columns([4, 1])
    
    with col1:
        query = st.text_area("💭 Consulta al Agente", height=100, 
                            placeholder="Escribe tu pregunta aquí...")
    with col2:
        submit = st.button("🔍 Buscar", type="primary")
    
    if submit and query:
        with st.spinner("Analizando tu pregunta..."):
            try:
                import asyncio
                
                # Obtener contexto relevante
                results = st.session_state.knowledge_base.search_knowledge(query, top_k=5)
                
                # Generar respuesta usando el agente RAG
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                response = loop.run_until_complete(st.session_state.rag_agent.get_response(query, results))
                loop.close()
                
                if results and response:
                    st.success("¡He encontrado información relevante!")
                    
                    # Mostrar la respuesta del agente
                    st.write("### 🤖 Respuesta del Agente")
                    st.write(response)
                    
                    # Mostrar fuentes de información
                    st.write("### 📚 Fuentes de Información")
                    for result in results:
                        with st.expander(f"📺 {result['title']} (Score: {result['score']:.2f})"):
                            st.write(f"**Canal:** {result['channel']}")
                            st.write(f"**Ver Video:** [{result['url']}]({result['url']})")
                            st.write("**Contexto Relevante:**")
                            st.write(result['context'])
                else:
                    st.warning("No encontré información específica sobre eso en mi base de conocimiento.")
                        
            except Exception as e:
                st.error(f"Error al procesar tu pregunta: {str(e)}")
                logger.error(f"Error procesando pregunta: {str(e)}", exc_info=True)
    
    # Videos Disponibles
    st.subheader("📚 Videos Disponibles")
    try:
        videos = st.session_state.knowledge_base.get_videos()
        
        if videos:
            for video in videos:
                with st.expander(f"📺 {video['title']}"):
                    st.write(f"**Canal:** {video['channel']}")
                    st.write(f"**Ver Video:** [{video['url']}]({video['url']})")
        else:
            st.info("No hay videos procesados aún")
    except Exception as e:
        st.error(f"Error al cargar videos: {str(e)}")

with tab2:
    # Si no hay usuario, mostrar login
    if 'user' not in st.session_state:
        with st.form("login_form"):
            st.info("Para administrar la base de conocimiento, es necesario iniciar sesión como administrador")
            st.subheader("🔐 Iniciar Sesión como Administrador")
            col1, col2, col3 = st.columns([1,2,1])
            with col2:
                email = st.text_input("Email")
                password = st.text_input("Contraseña", type="password")
                if st.form_submit_button("Iniciar Sesión"):
                    try:
                        user = st.session_state.auth.login(email, password)
                        if user:
                            st.session_state.is_admin = True
                            st.session_state.user = user
                            st.success("¡Inicio de sesión exitoso!")
                            st.rerun()
                    except Exception as e:
                        st.error(f"Error al iniciar sesión: {str(e)}")
        st.stop()
    
    # Mostrar información del usuario y botón de logout en la sidebar
    st.sidebar.write(f"👤 Usuario: {st.session_state.user['email']}")
    if st.sidebar.button("Cerrar Sesión"):
        st.session_state.auth.logout()
        st.rerun()
    
    # Sección de Administración
    st.header("Administración de la Base de Conocimiento")
    
    # Procesar Video
    st.subheader("📺 Procesar Nuevo Video")
    youtube_url = st.text_input("URL del video de YouTube")
    col1, col2 = st.columns([3, 1])
    
    with col1:
        if youtube_url:
            try:
                # Procesar video
                video_info = st.session_state.youtube_processor.get_video_info(youtube_url)
                
                if video_info:
                    st.write("### Información del Video")
                    st.write(f"**Título:** {video_info['title']}")
                    st.write(f"**Canal:** {video_info['channel']}")
                    st.write(f"**Duración:** {video_info['duration']}")
                
            except Exception as e:
                st.error(f"Error al procesar el video: {str(e)}")
                logger.error(f"Error procesando video: {str(e)}")
    
    with col2:
        if youtube_url and 'video_info' in locals():
            if st.button("🎯 Procesar", type="primary"):
                with st.spinner("Procesando video..."):
                    try:
                        # Obtener transcripción
                        transcript = st.session_state.youtube_processor.get_transcript(youtube_url)
                        
                        if transcript:
                            # Guardar en la base de conocimiento
                            st.session_state.knowledge_base.store_video_knowledge(
                                video_info['title'],
                                video_info['channel'],
                                youtube_url,
                                transcript
                            )
                            st.success("¡Video procesado y guardado exitosamente!")
                        else:
                            st.error("No se pudo obtener la transcripción del video")
                    except Exception as e:
                        st.error(f"Error al procesar el video: {str(e)}")
    
    # Estadísticas
    st.subheader("📊 Estadísticas de Conocimiento")
    try:
        stats = st.session_state.knowledge_base.get_statistics()
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Videos", stats["total_videos"])
        with col2:
            st.metric("Total Conceptos", stats["total_concepts"])
        with col3:
            st.metric("Última Actualización", stats["last_update"])
            
    except Exception as e:
        st.error(f"Error obteniendo estadísticas: {str(e)}")
    
    # Explorador de Conocimientos
    st.subheader("🔍 Explorar Base de Conocimientos")
    concept = st.text_input("Buscar concepto o tema")
    if concept:
        try:
            results = st.session_state.knowledge_base.search_knowledge(concept)
            if results:
                for result in results:
                    with st.expander(f"📺 {result['title']} (Score: {result['score']:.2f})"):
                        st.write(f"**Canal:** {result['channel']}")
                        st.write(f"**URL:** {result['url']}")
                        st.write("**Contexto Relevante:**")
                        st.write(result['context'])
            else:
                st.info("No se encontraron resultados para este concepto")
        except Exception as e:
            st.error(f"Error al buscar concepto: {str(e)}")

# Footer
st.markdown("---")
st.markdown("Desarrollado con ❤️ usando Streamlit y Supabase")
