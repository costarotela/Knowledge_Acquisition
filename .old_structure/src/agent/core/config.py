"""
Configuración central del agente.
"""
from pathlib import Path
from typing import Dict, Any
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Directorios base
BASE_DIR = Path(__file__).parent.parent.parent.parent
CONFIG_DIR = BASE_DIR / "config"
KNOWLEDGE_DIR = BASE_DIR / "knowledge_base"
CACHE_DIR = BASE_DIR / "cache"
LOGS_DIR = BASE_DIR / "logs"

# Asegurar que existan los directorios necesarios
for dir_path in [CONFIG_DIR, KNOWLEDGE_DIR, CACHE_DIR, LOGS_DIR]:
    dir_path.mkdir(exist_ok=True, parents=True)

# Configuración del agente
AGENT_CONFIG: Dict[str, Any] = {
    "name": "NutritionAgent",
    "version": "1.0.0",
    "description": "Agente de asistencia nutricional con capacidades de voz",
    "language": "es",
    "models": {
        "whisper": {
            "model": "tiny",
            "language": "es"
        },
        "llm": {
            "model": "gpt-4",
            "temperature": 0
        }
    },
    "interfaces": {
        "voice": {
            "enabled": True,
            "sample_rate": 16000,
            "chunk_size": 1024
        },
        "web": {
            "enabled": True,
            "port": 8501
        }
    }
}

# Configuración de logging
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        },
    },
    "handlers": {
        "default": {
            "level": "INFO",
            "formatter": "standard",
            "class": "logging.StreamHandler",
        },
        "file": {
            "level": "INFO",
            "formatter": "standard",
            "class": "logging.FileHandler",
            "filename": str(LOGS_DIR / "agent.log"),
            "mode": "a",
        },
    },
    "loggers": {
        "": {  # Root logger
            "handlers": ["default", "file"],
            "level": "INFO",
            "propagate": True
        },
    }
}
