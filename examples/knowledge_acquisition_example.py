"""
Ejemplo de uso del sistema de adquisición de conocimiento.
"""
import os
import asyncio
from dotenv import load_dotenv
import openai

from src.agent.orchestrator import KnowledgeOrchestrator, AcquisitionTask

async def main():
    # Cargar variables de entorno
    load_dotenv()
    
    # Configurar OpenAI
    openai.api_key = os.getenv("OPENAI_API_KEY")
    
    # Configurar el orquestador
    orchestrator = KnowledgeOrchestrator(
        config={
            'model_name': 'gpt-4-turbo-preview',
            'scraping_config': {
                'max_results': 5,
                'timeout': 30
            }
        }
    )
    
    # Definir la tarea de adquisición
    task = AcquisitionTask(
        query="¿Cuáles son las mejores prácticas actuales en Prompt Engineering?",
        context={
            'domain': 'AI/ML',
            'purpose': 'educational',
            'depth': 'comprehensive'
        }
    )
    
    # Ejecutar la tarea
    print("Iniciando adquisición de conocimiento...")
    result = await orchestrator.execute(task)
    
    if result.success:
        print("\n=== Conocimiento Adquirido ===")
        print("\nNodos de Conocimiento:")
        for node in result.data.nodes:
            print(f"- [{node.id}] {node.type}: {node.content}")
        
        print("\nRelaciones:")
        for rel in result.data.relationships:
            print(f"- {rel['source']} --({rel['type']})--> {rel['target']}")
        
        print("\nEvaluación:")
        evaluation = result.metadata.get('evaluation', {})
        print(f"Score: {evaluation.get('score', 0)}")
        print("\nFortalezas:")
        for strength in evaluation.get('strengths', []):
            print(f"- {strength}")
        print("\nÁreas de Mejora:")
        for weakness in evaluation.get('weaknesses', []):
            print(f"- {weakness}")
    else:
        print("Error:", result.error)

if __name__ == "__main__":
    asyncio.run(main())
