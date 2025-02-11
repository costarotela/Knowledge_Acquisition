"""
Clase base para el agente y sus componentes.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
import logging
from dataclasses import dataclass
from .config import AGENT_CONFIG

@dataclass
class AgentContext:
    """Contexto compartido entre componentes del agente."""
    session_id: str
    user_id: Optional[str] = None
    language: str = AGENT_CONFIG["language"]
    metadata: Dict[str, Any] = None

class AgentComponent(ABC):
    """Clase base para todos los componentes del agente."""
    
    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(f"agent.{name}")
        self._is_initialized = False
    
    @abstractmethod
    async def initialize(self) -> None:
        """Inicializa el componente."""
        pass
    
    @abstractmethod
    async def shutdown(self) -> None:
        """Limpia recursos al cerrar el componente."""
        pass
    
    def is_initialized(self) -> bool:
        """Verifica si el componente está inicializado."""
        return self._is_initialized

class AgentInterface(AgentComponent):
    """Clase base para interfaces del agente (voz, web, etc)."""
    
    @abstractmethod
    async def start(self) -> None:
        """Inicia la interfaz."""
        pass
    
    @abstractmethod
    async def stop(self) -> None:
        """Detiene la interfaz."""
        pass
    
    @abstractmethod
    async def send_response(self, response: str, context: AgentContext) -> None:
        """Envía una respuesta al usuario."""
        pass

class AgentProcessor(AgentComponent):
    """Clase base para procesadores (RAG, LLM, etc)."""
    
    @abstractmethod
    async def process(self, input_data: Any, context: AgentContext) -> Any:
        """Procesa una entrada y retorna un resultado."""
        pass

class AgentModel(AgentComponent):
    """Clase base para modelos del agente."""
    
    @abstractmethod
    async def predict(self, input_data: Any, context: AgentContext) -> Any:
        """Realiza una predicción basada en la entrada."""
        pass
    
    @abstractmethod
    async def train(self, training_data: Any) -> None:
        """Entrena o fine-tunea el modelo."""
        pass

class Agent:
    """Clase principal del agente."""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or AGENT_CONFIG
        self.logger = logging.getLogger("agent")
        self.interfaces: Dict[str, AgentInterface] = {}
        self.processors: Dict[str, AgentProcessor] = {}
        self.models: Dict[str, AgentModel] = {}
    
    async def initialize(self) -> None:
        """Inicializa todos los componentes del agente."""
        for component_dict in [self.interfaces, self.processors, self.models]:
            for component in component_dict.values():
                await component.initialize()
    
    async def shutdown(self) -> None:
        """Limpia recursos al cerrar el agente."""
        for component_dict in [self.interfaces, self.processors, self.models]:
            for component in component_dict.values():
                await component.shutdown()
    
    def add_interface(self, name: str, interface: AgentInterface) -> None:
        """Agrega una interfaz al agente."""
        self.interfaces[name] = interface
    
    def add_processor(self, name: str, processor: AgentProcessor) -> None:
        """Agrega un procesador al agente."""
        self.processors[name] = processor
    
    def add_model(self, name: str, model: AgentModel) -> None:
        """Agrega un modelo al agente."""
        self.models[name] = model
