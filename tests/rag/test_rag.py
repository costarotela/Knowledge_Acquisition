import asyncio
from src.agent.models.rag_model import KnowledgeAgent
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_questions():
    # Inicializar el agente
    agent = KnowledgeAgent()
    
    # Lista de preguntas para probar
    questions = [
        "¿Cuándo es necesario tomar geles de carbohidratos durante el ejercicio?",
        "¿Qué papel juega la glutamina en el cuerpo y cuándo es importante suplementarla?",
        "¿Cómo afecta la motivación a los hábitos alimenticios y el ejercicio?",
        "¿Cuál es la relación entre el músculo y la mitocondria?",
        "¿En qué situaciones es importante la nutrición clínica versus la nutrición deportiva?"
    ]
    
    # Procesar cada pregunta
    for i, question in enumerate(questions, 1):
        print(f"\n=== Pregunta {i}: {question} ===")
        try:
            response = await agent.answer_question(question)
            
            print("\nRespuesta:")
            print(response["respuesta"])
            
            print("\nFuentes relacionadas:")
            for fuente in response["fuentes_relacionadas"][:2]:  # Mostrar solo las 2 primeras fuentes
                print(f"- {fuente[:200]}...")  # Mostrar solo los primeros 200 caracteres
            
            print("\nConceptos relacionados:")
            if "músculo" in question.lower():
                related = agent.get_related_concepts("músculo")
                for rel in related:
                    print(f"- {rel['concepto1']} → {rel['tipo_relacion']} → {rel['concepto2']}")
            
            print("\n" + "="*50)
            
        except Exception as e:
            logger.error(f"Error procesando pregunta: {str(e)}")
            continue

if __name__ == "__main__":
    asyncio.run(test_questions())
