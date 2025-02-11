from src.agent.interfaces.voice_interface import VoiceInterface
from agentic_rag import AgenticNutritionRAG
import asyncio
import os
import time

# Inicializar componentes globalmente
vi = VoiceInterface()
rag = AgenticNutritionRAG()

async def initialize_system():
    """Inicializa el sistema una sola vez"""
    print("\n Inicializando el sistema...")
    knowledge_base_path = os.path.join(os.path.dirname(__file__), "knowledge_base.json")
    await rag.load_knowledge_base(knowledge_base_path)
    print(" Sistema inicializado y listo!")
    time.sleep(1)  # Pausa para que el usuario pueda leer el mensaje

async def test():
    # Inicializar sistema
    await initialize_system()
    
    # Mensaje de bienvenida
    await vi.speak("Hola! Soy tu asistente nutricional. Puedes hacerme preguntas sobre nutrición deportiva.")
    
    while True:
        # Esperar un momento antes de escuchar
        time.sleep(0.5)
        
        # Escuchar pregunta
        text = await vi.listen()
        
        if not text:
            await vi.speak("No pude entender lo que dijiste. ¿Podrías repetirlo?")
            continue
            
        # Verificar si el usuario quiere salir
        if "salir" in text.lower():
            await vi.speak("¡Hasta luego! Que tengas un excelente día.")
            break
        
        try:
            # Procesar la pregunta con el RAG
            response = await rag.answer_question(text)
            
            if response and not response.get("error"):
                answer = response["análisis"]
                await vi.speak(answer)
            else:
                await vi.speak("Lo siento, no pude procesar tu pregunta. ¿Podrías reformularla?")
        except Exception as e:
            print(f"\n Error: {str(e)}")
            await vi.speak("Lo siento, hubo un error procesando tu pregunta.")
        
        # Esperar un momento antes de continuar
        time.sleep(0.5)

if __name__ == "__main__":
    try:
        asyncio.run(test())
    except KeyboardInterrupt:
        print("\n\n ¡Hasta luego!")
    except Exception as e:
        print(f"\n Error inesperado: {str(e)}")
    finally:
        # Limpiar archivos temporales al salir
        temp_dir = "temp_audio"
        if os.path.exists(temp_dir):
            for file in os.listdir(temp_dir):
                try:
                    os.remove(os.path.join(temp_dir, file))
                except:
                    pass
