"""
Configuración centralizada del Travel Agent.
"""

import os
from pathlib import Path
from typing import Optional
from pydantic import BaseSettings, Field
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

class Settings(BaseSettings):
    """Configuración global del agente."""
    
    # Directorios
    BASE_DIR: Path = Path(__file__).parent.parent
    CACHE_DIR: Path = BASE_DIR / "data" / "cache"
    TEMPLATES_DIR: Path = BASE_DIR / "config" / "templates"
    
    # API Keys
    OPENAI_API_KEY: str = Field(..., env="OPENAI_API_KEY")
    SUPABASE_URL: str = Field(..., env="SUPABASE_URL")
    SUPABASE_KEY: str = Field(..., env="SUPABASE_KEY")
    
    # Supabase
    SUPABASE_BUCKET: str = Field("travel_agent_data", env="SUPABASE_BUCKET")
    
    # Cache
    CACHE_TTL: int = 3600  # 1 hora
    
    # Navegador
    BROWSER_HEADLESS: bool = True
    BROWSER_TIMEOUT: int = 30000  # 30 segundos
    
    # RAG
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    SIMILARITY_THRESHOLD: float = 0.7
    MAX_RAG_RESULTS: int = 5
    
    # Análisis
    MIN_SAMPLES: int = 5
    PRICE_ALERT_THRESHOLD: float = 0.1  # 10% de cambio
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# Instancia global de configuración
settings = Settings()

# Crear directorios necesarios
settings.CACHE_DIR.mkdir(parents=True, exist_ok=True)
settings.TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
