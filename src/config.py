"""
Configuración global del sistema.
"""
from typing import Dict, Any
import os
from dotenv import load_dotenv
from .llm.model_provider import ModelType
from .llm.llm_router import TaskType

# Cargar variables de entorno
load_dotenv()

# Configuración de LLM
LLM_CONFIG = {
    # Configuración por defecto para nuevos proveedores
    "default": {
        "type": ModelType(os.getenv("LLM_TYPE", "openai")),
        "name": os.getenv("LLM_NAME", "gpt-4-turbo"),
        "temperature": float(os.getenv("LLM_TEMPERATURE", "0.7")),
        "streaming": os.getenv("LLM_STREAMING", "False").lower() == "true"
    },
    
    # Proveedores predefinidos
    "providers": {
        "gpt4": {
            "type": ModelType.OPENAI,
            "name": "gpt-4-turbo",
            "temperature": 0.7
        },
        "gpt35": {
            "type": ModelType.OPENAI,
            "name": "gpt-3.5",
            "temperature": 0.7
        },
        "mixtral": {
            "type": ModelType.GROQ,
            "name": "mixtral-groq",
            "temperature": 0.7
        },
        "llama2": {
            "type": ModelType.GROQ,
            "name": "llama2-70b-groq",
            "temperature": 0.7
        }
    },
    
    # Rutas por tipo de tarea
    "routes": {
        TaskType.CODE.value: "gpt4",          # Código: GPT-4 por su precisión
        TaskType.CHAT.value: "mixtral",       # Chat: Mixtral por velocidad/costo
        TaskType.CLASSIFICATION.value: "gpt35",# Clasificación: GPT-3.5 suficiente
        TaskType.SUMMARY.value: "mixtral",    # Resúmenes: Mixtral buen balance
        TaskType.EXTRACTION.value: "gpt4",    # Extracción: GPT-4 por precisión
        TaskType.EMBEDDING.value: "gpt35"     # Embeddings: GPT-3.5 suficiente
    },
    
    # Proveedor de respaldo
    "fallback": "mixtral"
}

# Configuración de APIs
API_CONFIG = {
    "openai": {
        "api_key": os.getenv("OPENAI_API_KEY")
    },
    "deepinfra": {
        "api_key": os.getenv("DEEPINFRA_API_KEY")
    },
    "huggingface": {
        "api_key": os.getenv("HUGGINGFACE_API_KEY")
    },
    "groq": {
        "api_key": os.getenv("GROQ_API_KEY")
    }
}

# Configuración de JWT
JWT_CONFIG = {
    "secret_key": os.getenv("JWT_SECRET_KEY"),
    "algorithm": os.getenv("JWT_ALGORITHM", "HS256"),
    "access_token_expire_minutes": int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
}

# Configuración del servidor
SERVER_CONFIG = {
    "host": os.getenv("HOST", "0.0.0.0"),
    "port": int(os.getenv("PORT", "8000")),
    "debug": os.getenv("DEBUG", "True").lower() == "true"
}

# Configuración de logging
LOGGING_CONFIG = {
    "level": os.getenv("LOG_LEVEL", "INFO"),
    "file": os.getenv("LOG_FILE", "app.log")
}

# Configuración de scraping
SCRAPING_CONFIG = {
    "apis": {
        "youtube_api_key": os.getenv("YOUTUBE_API_KEY"),
        "github_token": os.getenv("GITHUB_TOKEN")
    },
    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

# Configuración de la base de datos
DATABASE_CONFIG = {
    "vector_store_path": os.getenv("VECTOR_STORE_PATH", "knowledge_base/vector_index"),
    "metadata_db_path": os.getenv("METADATA_DB_PATH", "knowledge_base/metadata.sqlite")
}

def validate_config():
    """Valida la configuración."""
    # Validar variables requeridas
    if not os.getenv("JWT_SECRET_KEY"):
        raise ValueError("JWT_SECRET_KEY es requerida")
    
    # Validar configuración de LLM
    providers = LLM_CONFIG["providers"]
    for provider_name, provider_config in providers.items():
        model_type = provider_config["type"]
        api_key = API_CONFIG.get(model_type.value, {}).get("api_key")
        
        if not api_key:
            raise ValueError(f"API key requerida para el proveedor {provider_name} ({model_type.value})")
    
    # Validar rutas de LLM
    routes = LLM_CONFIG["routes"]
    for task, provider_name in routes.items():
        if provider_name not in providers:
            raise ValueError(f"Proveedor {provider_name} no encontrado para la tarea {task}")
    
    # Validar fallback
    if LLM_CONFIG["fallback"] not in providers:
        raise ValueError(f"Proveedor de fallback {LLM_CONFIG['fallback']} no encontrado")

# Valida la configuración requerida.
validate_config()
