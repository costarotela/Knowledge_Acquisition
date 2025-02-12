"""
Configuración para los scrapers.
"""
from typing import Dict, Any
from pydantic import BaseModel, Field

class ScrapingConfig(BaseModel):
    """Configuración para el scraping."""
    max_results: int = Field(default=5, description="Número máximo de resultados a obtener")
    timeout: int = Field(default=30, description="Tiempo máximo de espera en segundos")
    max_retries: int = Field(default=3, description="Número máximo de reintentos")
    user_agent: str = Field(
        default="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        description="User agent para las peticiones"
    )
    headers: Dict[str, str] = Field(
        default_factory=lambda: {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5"
        },
        description="Headers adicionales para las peticiones"
    )
