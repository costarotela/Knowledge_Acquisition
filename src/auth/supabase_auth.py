from typing import Dict, Optional
import streamlit as st
from st_supabase_connection import SupabaseConnection
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SupabaseAuth:
    def __init__(self):
        """Inicializa el cliente de autenticación de Supabase."""
        # Inicializar conexión usando st.connection
        self.supabase = st.connection("supabase", type=SupabaseConnection)
        
        logger.info("=== Supabase Debug Info ===")
        logger.info("Conexión inicializada")
        logger.info("=========================")
    
    def login(self, email: str, password: str) -> Dict:
        """
        Inicia sesión de un usuario.
        
        Args:
            email: Email del usuario
            password: Contraseña del usuario
            
        Returns:
            Dict con datos del usuario
        """
        try:
            logger.info(f"Intentando iniciar sesión para: {email}")
            
            # Primero intentamos obtener el usuario
            users = self.supabase.auth.admin.list_users()
            user_exists = any(user.email == email for user in users)
            
            if not user_exists:
                logger.info(f"Usuario {email} no existe, creándolo...")
                # Si no existe, lo creamos con la API de admin
                new_user = self.supabase.auth.admin.create_user({
                    "email": email,
                    "password": password,
                    "email_confirm": True,  # Auto-confirmar email
                    "user_metadata": {"role": "admin"}
                })
                logger.info(f"Usuario creado: {new_user.email}")
            
            # Ahora intentamos el login
            auth_response = self.supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
            
            if not auth_response.user:
                raise Exception("No se pudo obtener el usuario después del login")
                
            logger.info(f"Inicio de sesión exitoso para: {email}")
            
            # Crear objeto de usuario simplificado
            user_data = {
                'id': auth_response.user.id,
                'email': auth_response.user.email,
                'role': 'admin'
            }
            
            # Guardar en session_state
            st.session_state.user = user_data
            st.session_state.is_admin = True
            
            logger.info("Sesión guardada y establecida correctamente")
            return user_data
            
        except Exception as e:
            logger.error(f"Error en inicio de sesión: {str(e)}")
            raise

    def logout(self) -> None:
        """
        Cierra la sesión del usuario actual.
        """
        try:
            self.supabase.auth.sign_out()
            if 'user' in st.session_state:
                del st.session_state.user
            if 'is_admin' in st.session_state:
                st.session_state.is_admin = False
            logger.info("Sesión cerrada exitosamente")
        except Exception as e:
            logger.error(f"Error al cerrar sesión: {str(e)}")
            raise

    def get_current_user(self) -> Optional[Dict]:
        """
        Obtiene información del usuario actual.
        
        Returns:
            Dict con datos del usuario o None si no hay sesión
        """
        try:
            # Intentar obtener la sesión actual
            session = self.supabase.auth.get_session()
            
            if session and session.user:
                user_data = {
                    'id': session.user.id,
                    'email': session.user.email,
                    'role': 'admin'
                }
                
                # Actualizar en session_state
                st.session_state.user = user_data
                st.session_state.is_admin = True
                
                return user_data
                
            return None
            
        except Exception as e:
            logger.error(f"Error al obtener usuario actual: {str(e)}")
            return None

def init_auth():
    """
    Inicializa la autenticación en la sesión de Streamlit.
    Verifica si hay una sesión activa y la restaura.
    """
    if 'auth' not in st.session_state:
        st.session_state.auth = SupabaseAuth()
        
    # Verificar si hay una sesión activa
    if 'user' not in st.session_state:
        current_user = st.session_state.auth.get_current_user()
        if current_user:
            st.session_state.user = current_user
            st.session_state.is_admin = True
            logger.info(f"Sesión restaurada para: {current_user['email']}")

def restore_session(self, email: str) -> Optional[Dict]:
    """
    Restaura la sesión de un usuario usando su email.
    
    Args:
        email: Email del usuario
        
    Returns:
        Dict con datos del usuario o None si no se pudo restaurar
    """
    try:
        logger.info(f"Intentando restaurar sesión para: {email}")
        
        # Obtener usuario por email
        users = self.supabase.auth.admin.list_users()
        user = next((u for u in users if u.email == email), None)
        
        if user:
            # Generar un token de invitación
            invite_data = self.supabase.auth.admin.invite_user({
                "email": email,
                "data": {"role": "admin"}
            })
            
            if not invite_data:
                raise Exception("No se pudo generar la invitación")
            
            # Usar el token para iniciar sesión
            auth_response = self.supabase.auth.sign_in_with_password({
                "email": email,
                "password": st.session_state.get('last_password', '')  # Usar última contraseña usada
            })
            
            if not auth_response or not auth_response.user:
                raise Exception("No se pudo iniciar sesión con el token")
            
            # Crear objeto de usuario simplificado
            user_data = {
                'id': auth_response.user.id,
                'email': auth_response.user.email,
                'role': 'admin'
            }
            
            # Guardar en session_state
            st.session_state.user = user_data
            st.session_state.is_admin = True
            
            logger.info(f"Sesión restaurada exitosamente para: {email}")
            return user_data
            
        logger.error(f"No se encontró el usuario: {email}")
        return None
        
    except Exception as e:
        logger.error(f"Error restaurando sesión: {str(e)}")
        return None
