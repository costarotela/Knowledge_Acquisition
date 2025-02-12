"""
Funcionalidades de seguridad y autenticación.
"""
from datetime import datetime, timedelta
from typing import Optional, List
import jwt
from jwt.exceptions import InvalidTokenError
from functools import wraps
from .models import User, Role, Permission, TokenPayload

# Configuración de JWT
JWT_SECRET = "your-secret-key"  # TODO: Mover a variables de entorno
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

def create_access_token(user: User) -> str:
    """Crea un token JWT para el usuario."""
    expires_delta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    expire = datetime.utcnow() + expires_delta
    
    payload = TokenPayload(
        sub=user.id,
        role=user.role,
        permissions=user.permissions,
        exp=int(expire.timestamp())
    )
    
    return jwt.encode(
        payload.dict(),
        JWT_SECRET,
        algorithm=JWT_ALGORITHM
    )

def decode_token(token: str) -> Optional[TokenPayload]:
    """Decodifica y valida un token JWT."""
    try:
        payload = jwt.decode(
            token,
            JWT_SECRET,
            algorithms=[JWT_ALGORITHM]
        )
        return TokenPayload(**payload)
    except InvalidTokenError:
        return None

def requires_auth(*required_permissions: Permission):
    """Decorador para proteger endpoints/funciones."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Obtener token del contexto (implementar según el framework)
            token = get_token_from_context()
            if not token:
                raise AuthError("Token no proporcionado")
            
            # Validar token
            payload = decode_token(token)
            if not payload:
                raise AuthError("Token inválido")
            
            # Verificar expiración
            if datetime.utcnow().timestamp() > payload.exp:
                raise AuthError("Token expirado")
            
            # Verificar permisos
            if payload.role != Role.OWNER and not all(
                perm in payload.permissions 
                for perm in required_permissions
            ):
                raise AuthError("Permisos insuficientes")
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator

class AuthError(Exception):
    """Error de autenticación/autorización."""
    pass

def get_token_from_context() -> Optional[str]:
    """
    Obtiene el token del contexto actual.
    TODO: Implementar según el framework utilizado (FastAPI, Flask, etc.)
    """
    return None  # Implementar
