"""
Modelos de autenticación y autorización.
"""
from enum import Enum
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field

class Role(str, Enum):
    """Roles de usuario."""
    OWNER = "owner"  # Administrador del agente y la base de conocimiento
    RESEARCHER = "researcher"  # Puede realizar búsquedas y consultas
    VIEWER = "viewer"  # Solo puede ver conocimiento existente

class Permission(str, Enum):
    """Permisos específicos."""
    MANAGE_KNOWLEDGE = "manage_knowledge"  # CRUD en la base de conocimiento
    MANAGE_AGENTS = "manage_agents"  # Configurar y administrar agentes
    EXECUTE_SEARCH = "execute_search"  # Ejecutar búsquedas
    VALIDATE_INFO = "validate_info"  # Validar información
    SYNTHESIZE = "synthesize"  # Sintetizar conocimiento
    EVALUATE = "evaluate"  # Evaluar conocimiento
    VIEW_KNOWLEDGE = "view_knowledge"  # Ver conocimiento existente

class User(BaseModel):
    """Usuario del sistema."""
    id: str = Field(description="ID único del usuario")
    username: str = Field(description="Nombre de usuario")
    email: str = Field(description="Correo electrónico")
    role: Role = Field(description="Rol principal del usuario")
    permissions: List[Permission] = Field(description="Permisos específicos")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = Field(default=None)

class TokenPayload(BaseModel):
    """Payload del token JWT."""
    sub: str = Field(description="ID del usuario (subject)")
    role: Role = Field(description="Rol del usuario")
    permissions: List[Permission] = Field(description="Permisos del usuario")
    exp: int = Field(description="Timestamp de expiración")
