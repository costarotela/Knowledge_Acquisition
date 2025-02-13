"""
Procesador base para todas las fuentes de información.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class BaseProcessor(ABC):
    """Clase base para todos los procesadores de información."""
    
    def __init__(self, config: Dict[str, Any]):
        """Inicializa el procesador."""
        self.config = config
    
    @abstractmethod
    async def extract_content(self, source: str) -> Dict[str, Any]:
        """Extrae contenido de la fuente."""
        pass
    
    @abstractmethod
    async def process_content(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Procesa el contenido extraído."""
        pass
    
    @abstractmethod
    async def validate_source(self, source: str) -> bool:
        """Valida si la fuente es compatible con este procesador."""
        pass
