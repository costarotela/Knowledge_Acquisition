"""
Punto de entrada principal para el agente.
"""
import asyncio
import logging
from src.agent.core.base import Agent
from src.agent.interfaces.web.streamlit_app import StreamlitInterface
from src.agent.models.rag_model import NutritionRAG
from src.agent.utils.logger import setup_logging

async def main():
    """Función principal del agente."""
    # Configurar logging
    setup_logging()
    logger = logging.getLogger("main")
    logger.info("Iniciando agente...")
    
    try:
        # Crear instancia del agente
        agent = Agent()
        
        # Agregar componentes
        agent.add_interface("web", StreamlitInterface())
        agent.add_model("rag", NutritionRAG())
        
        # Inicializar agente
        await agent.initialize()
        logger.info("Agente inicializado correctamente")
        
        # Iniciar interfaz web
        web_interface = agent.interfaces["web"]
        await web_interface.start()
        
    except Exception as e:
        logger.error(f"Error iniciando el agente: {e}")
        raise
    finally:
        # Cleanup
        await agent.shutdown()
        logger.info("Agente detenido")

if __name__ == "__main__":
    asyncio.run(main())
