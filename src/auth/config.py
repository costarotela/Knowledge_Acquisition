"""
Configuración de autenticación y autorización.
"""
from typing import Dict, List
from .models import Role, Permission

# Configuración de permisos por rol
ROLE_PERMISSIONS: Dict[Role, List[Permission]] = {
    Role.OWNER: [
        Permission.MANAGE_KNOWLEDGE,
        Permission.MANAGE_AGENTS,
        Permission.EXECUTE_SEARCH,
        Permission.VALIDATE_INFO,
        Permission.SYNTHESIZE,
        Permission.EVALUATE,
        Permission.VIEW_KNOWLEDGE
    ],
    Role.RESEARCHER: [
        Permission.EXECUTE_SEARCH,
        Permission.VALIDATE_INFO,
        Permission.VIEW_KNOWLEDGE
    ],
    Role.VIEWER: [
        Permission.VIEW_KNOWLEDGE
    ]
}

# Configuración de JWT
JWT_CONFIG = {
    "SECRET_KEY": "your-secret-key",  # TODO: Mover a variables de entorno
    "ALGORITHM": "HS256",
    "ACCESS_TOKEN_EXPIRE_MINUTES": 30
}

# Configuración de endpoints protegidos
PROTECTED_ENDPOINTS = {
    # Endpoints que requieren autenticación y permisos específicos
    "/api/knowledge/manage": [Permission.MANAGE_KNOWLEDGE],
    "/api/agents/manage": [Permission.MANAGE_AGENTS],
    "/api/search/execute": [Permission.EXECUTE_SEARCH],
    "/api/validate": [Permission.VALIDATE_INFO],
    "/api/synthesize": [Permission.SYNTHESIZE],
    "/api/evaluate": [Permission.EVALUATE],
    "/api/knowledge/view": [Permission.VIEW_KNOWLEDGE]
}
