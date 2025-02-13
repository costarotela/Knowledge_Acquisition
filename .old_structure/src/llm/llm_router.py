"""
Router para manejar múltiples modelos de lenguaje y elegir el más apropiado según el caso.
"""
from typing import Dict, Optional, List
from enum import Enum

from .model_provider import ModelProvider, ModelType

class TaskType(Enum):
    """Tipos de tareas que pueden ser manejadas por los modelos."""
    CHAT = "chat"                    # Conversación general
    CODE = "code"                    # Generación/análisis de código
    CLASSIFICATION = "classification" # Clasificación de texto
    SUMMARY = "summary"              # Resúmenes
    EXTRACTION = "extraction"        # Extracción de información
    EMBEDDING = "embedding"          # Generación de embeddings

class LLMRouter:
    """
    Router para manejar múltiples modelos de lenguaje.
    Permite usar diferentes modelos según el tipo de tarea,
    presupuesto, y otros factores.
    """
    
    def __init__(self):
        self._providers: Dict[str, ModelProvider] = {}
        self._task_routes: Dict[TaskType, str] = {}
        self._fallback_provider: Optional[str] = None
    
    def add_provider(
        self,
        name: str,
        model_type: ModelType,
        model_name: str,
        temperature: float = 0.7,
        **kwargs
    ) -> None:
        """
        Agrega un nuevo proveedor de modelo.
        
        Args:
            name: Nombre único para identificar este proveedor
            model_type: Tipo de modelo (OpenAI, Groq, etc)
            model_name: Nombre del modelo a usar
            temperature: Temperatura para generación
            **kwargs: Argumentos adicionales para el proveedor
        """
        self._providers[name] = ModelProvider(
            model_type=model_type,
            model_name=model_name,
            temperature=temperature,
            **kwargs
        )
    
    def set_route(self, task_type: TaskType, provider_name: str) -> None:
        """
        Configura qué proveedor usar para cada tipo de tarea.
        
        Args:
            task_type: Tipo de tarea
            provider_name: Nombre del proveedor a usar
        """
        if provider_name not in self._providers:
            raise ValueError(f"Provider {provider_name} no está registrado")
        self._task_routes[task_type] = provider_name
    
    def set_fallback(self, provider_name: str) -> None:
        """
        Configura el proveedor de respaldo a usar cuando no hay una ruta específica.
        
        Args:
            provider_name: Nombre del proveedor de respaldo
        """
        if provider_name not in self._providers:
            raise ValueError(f"Provider {provider_name} no está registrado")
        self._fallback_provider = provider_name
    
    def get_provider(self, task_type: Optional[TaskType] = None) -> ModelProvider:
        """
        Obtiene el proveedor más apropiado para una tarea.
        
        Args:
            task_type: Tipo de tarea a realizar
            
        Returns:
            El proveedor de modelo más apropiado
        """
        if task_type and task_type in self._task_routes:
            return self._providers[self._task_routes[task_type]]
        
        if self._fallback_provider:
            return self._providers[self._fallback_provider]
        
        raise ValueError("No hay proveedor configurado para esta tarea")
    
    def get_all_providers(self) -> List[str]:
        """Retorna la lista de nombres de todos los proveedores registrados."""
        return list(self._providers.keys())

# Ejemplo de uso:
"""
# Crear el router
router = LLMRouter()

# Agregar proveedores
router.add_provider(
    name="gpt4",
    model_type=ModelType.OPENAI,
    model_name="gpt-4-turbo"
)

router.add_provider(
    name="mixtral",
    model_type=ModelType.GROQ,
    model_name="mixtral-groq",
    temperature=0.7
)

# Configurar rutas
router.set_route(TaskType.CODE, "gpt4")        # GPT-4 para código
router.set_route(TaskType.CHAT, "mixtral")     # Mixtral para chat
router.set_fallback("mixtral")                 # Mixtral como respaldo

# Usar el router
code_provider = router.get_provider(TaskType.CODE)    # Retorna GPT-4
chat_provider = router.get_provider(TaskType.CHAT)    # Retorna Mixtral
default_provider = router.get_provider()              # Retorna Mixtral
"""
