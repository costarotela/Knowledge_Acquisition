"""
Configuración global del sistema.
"""
from typing import Dict, Any
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Configuración de OpenAI
OPENAI_CONFIG = {
    "api_key": os.getenv("OPENAI_API_KEY"),
    "model": os.getenv("OPENAI_MODEL", "gpt-4-turbo-preview")
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

# Configuración de procesadores
PROCESSOR_CONFIG = {
    "video_processor": {
        "model_name": OPENAI_CONFIG["model"],
        "youtube_api_key": os.getenv("YOUTUBE_API_KEY"),
        "whisper_model": "base",
        "supported_languages": ["es", "en"]
    },
    "document_processor": {
        "supported_extensions": [".pdf", ".xlsx", ".xls", ".docx", ".doc", ".txt"],
        "max_file_size": 10 * 1024 * 1024  # 10MB
    },
    "web_processor": {
        "github_token": os.getenv("GITHUB_TOKEN"),
        "user_agent": "KnowledgeAcquisition/1.0",
        "timeout": 30,
        "max_retries": 3
    }
}

# Configuración de agentes especializados
AGENT_CONFIG = {
    "knowledge_scout": {
        "model_name": OPENAI_CONFIG["model"],
        "temperature": 0.7,
        "max_tokens": 1000,
        "search_depth": 3,
        "min_relevance": 0.6
    },
    "fact_validator": {
        "model_name": OPENAI_CONFIG["model"],
        "temperature": 0.3,
        "max_tokens": 500,
        "min_confidence": 0.8,
        "cross_validation": True
    },
    "knowledge_synthesizer": {
        "model_name": OPENAI_CONFIG["model"],
        "temperature": 0.5,
        "max_tokens": 2000,
        "chunk_size": 1000,
        "chunk_overlap": 200
    },
    "meta_evaluator": {
        "model_name": OPENAI_CONFIG["model"],
        "temperature": 0.4,
        "max_tokens": 800,
        "evaluation_metrics": ["completeness", "accuracy", "coherence", "relevance"]
    }
}

# Configuración de embeddings
EMBEDDING_CONFIG = {
    "model_name": "text-embedding-3-large",
    "batch_size": 100,
    "cache_dir": ".embeddings_cache",
    "dimensions": 1536
}

# Configuración de la base de conocimientos
KNOWLEDGE_BASE_CONFIG = {
    "vector_store": "faiss",
    "index_path": "knowledge_base/vector_index",
    "metadata_db": "knowledge_base/metadata.sqlite",
    "backup_interval": 3600  # 1 hora
}

def validate_config():
    """Valida la configuración requerida."""
    required_vars = [
        "OPENAI_API_KEY",
        "JWT_SECRET_KEY"
    ]
    
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        raise ValueError(
            f"Faltan las siguientes variables de entorno requeridas: {', '.join(missing_vars)}"
        )

# Valida la configuración requerida.
validate_config()
