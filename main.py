"""
Punto de entrada principal para el sistema de adquisición de conocimiento.
"""
import asyncio
import logging
from src.agent.core.base import Agent
from src.agent.interfaces.web.streamlit_app import StreamlitInterface
from src.agent.models.rag_model import KnowledgeAcquisitionRAG
from src.agent.utils.logger import setup_logging
from src.config import validate_config

async def main():
    """Función principal del sistema."""
    # Configurar logging
    setup_logging()
    logger = logging.getLogger("main")
    logger.info("Iniciando sistema de adquisición de conocimiento...")
    
    try:
        # Validar configuración
        validate_config()
        
        # Crear instancia del agente principal
        agent = Agent()
        
        # Agregar componentes
        agent.add_interface("web", StreamlitInterface())
        agent.add_model("rag", KnowledgeAcquisitionRAG())
        
        # Inicializar agente
        await agent.initialize()
        logger.info("Sistema inicializado correctamente")
        
        # Iniciar interfaz web
        web_interface = agent.interfaces["web"]
        await web_interface.start()
        
    except Exception as e:
        logger.error(f"Error iniciando el sistema: {e}")
        raise
    finally:
        # Cleanup
        await agent.shutdown()
        logger.info("Sistema detenido")

if __name__ == "__main__":
    asyncio.run(main())
