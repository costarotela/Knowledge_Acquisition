import streamlit as st
import asyncio
from src.agent.models.youtube_processor import YouTubeProcessor
from src.agent.core.context import AgentContext
from src.auth.supabase_auth import init_auth
import os

# Configuración de la página
st.set_page_config(
    page_title="Procesador de YouTube",
    page_icon="▶️",
    layout="wide"
)

# Inicializar autenticación
init_auth()

# Inicializar YouTubeProcessor
if 'youtube_processor' not in st.session_state:
    api_key = os.getenv('YOUTUBE_API_KEY')
    if api_key:
        st.session_state.youtube_processor = YouTubeProcessor(api_key)
    else:
        st.error("No se encontró la clave de API de YouTube. Por favor, configura la variable de entorno YOUTUBE_API_KEY.")
        st.stop()

async def initialize_processor():
    """Inicializa el procesador de YouTube si no está inicializado."""
    if not st.session_state.youtube_processor.is_initialized():
        await st.session_state.youtube_processor.initialize()

async def process_youtube_url(url: str, context: AgentContext):
    """Procesa una URL de YouTube y retorna los resultados."""
    try:
        result = await st.session_state.youtube_processor.process(url, context)
        # Convertir HttpUrl a string antes de pasarlo a Streamlit
        if result and hasattr(result, 'url'):
            result.url = str(result.url)
        return result
    except ValueError as e:
        st.error(f"Error: {str(e)}")
        return None
    except Exception as e:
        st.error(f"Error inesperado: {str(e)}")
        return None

# Interfaz de usuario
st.title("▶️ Procesador de YouTube")

# Login
if not st.session_state.user:
    with st.form("login_form"):
        st.subheader(" Iniciar Sesión")
        email = st.text_input("Email")
        password = st.text_input("Contraseña", type="password")
        col1, col2 = st.columns(2)
        
        with col1:
            login = st.form_submit_button("Iniciar Sesión")
        with col2:
            register = st.form_submit_button("Registrarse")
        
        if login and email and password:
            success, message, user_data = asyncio.run(
                st.session_state.auth.sign_in(email, password)
            )
            if success:
                st.session_state.user = user_data
                st.success(message)
                st.experimental_rerun()
            else:
                st.error(message)
        
        elif register and email and password:
            success, message = asyncio.run(
                st.session_state.auth.sign_up(email, password)
            )
            if success:
                st.success(message)
                st.info("Por favor, verifica tu email y luego inicia sesión.")
            else:
                st.error(message)
    st.stop()

# Área principal (solo visible para usuarios autenticados)
st.write(f" Usuario: {st.session_state.user['email']}")
st.write("Ingresa una URL de YouTube para procesar su contenido.")

with st.form("youtube_form"):
    url = st.text_input("URL de YouTube")
    process = st.form_submit_button("Procesar")
    
    if process and url:
        # Crear un placeholder para el spinner
        with st.spinner("Procesando video..."):
            # Inicializar el procesador
            asyncio.run(initialize_processor())
            
            # Crear contexto
            context = AgentContext(session_id=st.session_state.user['id'])
            
            # Procesar URL
            result = asyncio.run(process_youtube_url(url, context))
            
            if result:
                # Mostrar resultados
                st.subheader(" Información del Video")
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write("**Título:**", result["title"])
                    st.write("**Canal:**", result["channel"])
                
                with col2:
                    st.write("**Vistas:**", result["views"])
                    st.write("**Likes:**", result["likes"])
                
                if result.get("error"):
                    st.warning(f" Advertencia: {result['error']}")
                
                if result.get("transcript"):
                    st.subheader(" Transcripción")
                    with st.expander("Ver transcripción completa"):
                        st.write(result["transcript"])
                else:
                    st.error("No se pudo obtener la transcripción del video")

# Botón de cierre de sesión
if st.sidebar.button("Cerrar Sesión"):
    success, message = asyncio.run(st.session_state.auth.sign_out())
    if success:
        st.session_state.user = None
        st.success(message)
        st.experimental_rerun()
    else:
        st.error(message)
