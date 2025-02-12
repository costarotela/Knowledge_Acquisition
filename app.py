"""
Aplicación Streamlit para el sistema de adquisición de conocimiento.
"""
import streamlit as st
import logging
from src.auth.security import requires_auth, create_access_token
from src.auth.models import User, Role, Permission
from src.agent.models.rag_model import KnowledgeAcquisitionRAG
from src.config import validate_config
import os
from dotenv import load_dotenv

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Cargar variables de entorno
load_dotenv()
validate_config()

# Configuración de la página
st.set_page_config(
    page_title="Knowledge Acquisition System",
    page_icon="🧠",
    layout="wide"
)

# Inicializar estado de la sesión
if 'initialized' not in st.session_state:
    st.session_state.initialized = False

if not st.session_state.initialized:
    logger.info("Inicializando estado de la aplicación...")
    
    # Inicializar RAG Agent
    if 'rag_agent' not in st.session_state:
        try:
            logger.info("Inicializando RAG Agent...")
            st.session_state.rag_agent = KnowledgeAcquisitionRAG()
            st.session_state.rag_agent.initialize()
        except Exception as e:
            st.error(f"Error inicializando RAG Agent: {e}")
            st.stop()
    
    st.session_state.initialized = True

# Título principal
st.title("Sistema de Adquisición de Conocimiento")

# Crear pestañas
tab1, tab2 = st.tabs(["Base de Conocimiento", "Administración"])

with tab1:
    st.header("Base de Conocimiento")
    
    # Entrada de fuente de información
    source = st.text_input("Ingrese la URL o ruta del archivo:")
    source_type = st.selectbox(
        "Tipo de fuente",
        ["auto", "video", "document", "web"],
        index=0
    )
    
    if st.button("Procesar"):
        if source:
            try:
                with st.spinner("Procesando fuente de información..."):
                    result = st.session_state.rag_agent.process_source(
                        source,
                        source_type if source_type != "auto" else None
                    )
                    
                    # Mostrar resultados
                    st.success("Procesamiento completado")
                    st.json(result)
            except Exception as e:
                st.error(f"Error procesando fuente: {e}")
        else:
            st.warning("Por favor ingrese una fuente de información")

with tab2:
    # Si no hay usuario, mostrar login
    if 'user' not in st.session_state:
        with st.form("login_form"):
            st.info("Para administrar el sistema, es necesario iniciar sesión como administrador")
            username = st.text_input("Usuario")
            password = st.text_input("Contraseña", type="password")
            
            if st.form_submit_button("Iniciar Sesión"):
                # TODO: Implementar autenticación real
                if username == os.getenv("ADMIN_USERNAME") and password == os.getenv("ADMIN_PASSWORD"):
                    st.session_state.user = User(
                        username=username,
                        role=Role.OWNER,
                        permissions=[p for p in Permission]
                    )
                    st.success("Sesión iniciada correctamente")
                    st.rerun()
                else:
                    st.error("Credenciales inválidas")
    
    # Si hay usuario, mostrar panel de administración
    else:
        st.header(f"Bienvenido, {st.session_state.user.username}")
        
        # Mostrar estadísticas y configuración
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Estadísticas")
            # TODO: Implementar estadísticas
            
        with col2:
            st.subheader("Configuración")
            # TODO: Implementar configuración
        
        if st.button("Cerrar Sesión"):
            del st.session_state.user
            st.rerun()

# Footer
st.markdown("---")
st.markdown("Desarrollado con ❤️ usando Streamlit y Supabase")
