"""
Utilidades para el manejo de modelos de lenguaje.
"""
from typing import Optional
from ..config import LLM_CONFIG
from .llm_router import LLMRouter, TaskType

def create_llm_router() -> LLMRouter:
    """
    Crea y configura un router de LLM basado en la configuración.
    
    Returns:
        Router configurado con los proveedores y rutas definidos
    """
    router = LLMRouter()
    
    # Registrar proveedores
    for name, config in LLM_CONFIG["providers"].items():
        router.add_provider(
            name=name,
            model_type=config["type"],
            model_name=config["name"],
            temperature=config["temperature"]
        )
    
    # Configurar rutas
    for task_str, provider_name in LLM_CONFIG["routes"].items():
        router.set_route(TaskType(task_str), provider_name)
    
    # Configurar fallback
    if LLM_CONFIG["fallback"]:
        router.set_fallback(LLM_CONFIG["fallback"])
    
    return router

def get_llm_for_task(task_type: Optional[TaskType] = None):
    """
    Obtiene el modelo de lenguaje más apropiado para una tarea.
    
    Args:
        task_type: Tipo de tarea a realizar
        
    Returns:
        Modelo de lenguaje configurado para la tarea
    """
    router = create_llm_router()
    return router.get_provider(task_type).llm

# Ejemplo de uso:
"""
# Crear router con toda la configuración
router = create_llm_router()

# O simplemente obtener el LLM apropiado para una tarea
code_llm = get_llm_for_task(TaskType.CODE)      # GPT-4
chat_llm = get_llm_for_task(TaskType.CHAT)      # Mixtral
default_llm = get_llm_for_task()                # Fallback (Mixtral)
"""
