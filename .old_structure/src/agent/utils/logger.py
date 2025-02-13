"""
Configuración y utilidades de logging.
"""
import logging
import logging.config
from pathlib import Path
from ..core.config import LOGGING_CONFIG, LOGS_DIR

def setup_logging():
    """Configura el sistema de logging."""
    # Asegurar que existe el directorio de logs
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Aplicar configuración
    logging.config.dictConfig(LOGGING_CONFIG)
    
    # Crear logger principal
    logger = logging.getLogger("agent")
    logger.info("Sistema de logging inicializado")
