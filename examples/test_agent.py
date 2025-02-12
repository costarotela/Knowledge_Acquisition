"""
Script de prueba para el agente de adquisición de conocimiento.
"""
import asyncio
import logging
from dotenv import load_dotenv
import os
import openai

from src.agent.orchestrator import KnowledgeOrchestrator, AcquisitionTask, TaskType, TaskPriority
from src.config import AGENT_CONFIG

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Cargar variables de entorno
load_dotenv()

# Configurar OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY")

async def test_knowledge_acquisition():
    """Prueba el sistema de adquisición de conocimiento."""
    try:
        # Inicializar orquestador
        config = AGENT_CONFIG.copy()
        config.update({
            "openai_api_key": os.getenv("OPENAI_API_KEY"),
            "model_name": "gpt-4-turbo-preview",
            "temperature": 0.7
        })
        
        orchestrator = KnowledgeOrchestrator(config)
        
        # Ejemplo 1: Procesar artículo web
        article_task = AcquisitionTask(
            query="https://www.nature.com/articles/d41586-024-00115-7",
            task_type=TaskType.RESEARCH,
            priority=TaskPriority.HIGH,
            requirements={
                "extract_concepts": True,
                "generate_summary": True,
                "identify_key_findings": True
            }
        )
        
        logger.info("Procesando artículo...")
        article_result = await orchestrator.execute(article_task)
        
        if article_result.success:
            logger.info("Artículo procesado exitosamente")
            logger.info("Conocimiento extraído:")
            if isinstance(article_result.data, dict):
                logger.info(f"- Conceptos: {article_result.data.get('concepts', [])}")
                logger.info(f"- Resumen: {article_result.data.get('summary', '')}")
                logger.info(f"- Hallazgos clave: {article_result.data.get('key_findings', [])}")
            else:
                logger.info(f"- Evaluación: {article_result.data}")
        else:
            logger.error(f"Error procesando artículo: {article_result.error}")
        
        # Ejemplo 2: Consultar conocimiento
        query_task = AcquisitionTask(
            query="¿Cuáles son las principales implicaciones de los hallazgos del artículo para el campo de la IA?",
            task_type=TaskType.SYNTHESIS,
            priority=TaskPriority.MEDIUM,
            requirements={
                "provide_context": True,
                "include_examples": True
            },
            context={"article_knowledge": article_result.data}  # Agregamos el contexto del artículo
        )
        
        logger.info("\nConsultando conocimiento...")
        query_result = await orchestrator.execute(query_task)
        
        if query_result.success:
            logger.info("Consulta procesada exitosamente")
            logger.info("Respuesta:")
            if isinstance(query_result.data, dict):
                logger.info(query_result.data.get('response', ''))
            else:
                logger.info(query_result.data)
        else:
            logger.error(f"Error en consulta: {query_result.error}")
            
    except Exception as e:
        logger.error(f"Error inesperado: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_knowledge_acquisition())
