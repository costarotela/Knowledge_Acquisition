"""
Clase base para todos los agentes especializados.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field

class AgentMetrics(BaseModel):
    """Métricas de rendimiento del agente."""
    execution_time: float = Field(description="Tiempo de ejecución en segundos")
    success_rate: float = Field(description="Tasa de éxito (0-1)")
    confidence_score: float = Field(description="Puntuación de confianza (0-1)")
    error_count: int = Field(description="Número de errores encontrados")
    timestamp: datetime = Field(default_factory=datetime.now)

class AgentResult(BaseModel):
    """Resultado base para todas las operaciones de agentes."""
    success: bool = Field(description="Indica si la ejecución fue exitosa")
    data: Optional[Any] = Field(default=None, description="Datos resultantes")
    error: Optional[str] = Field(default=None, description="Mensaje de error si hubo fallo")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadatos adicionales")

class BaseSpecializedAgent(ABC):
    """Clase base para todos los agentes especializados."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.name = self.__class__.__name__
        
    @abstractmethod
    async def execute(self, *args, **kwargs) -> AgentResult:
        """Ejecuta la tarea principal del agente."""
        pass
    
    async def validate_input(self, *args, **kwargs) -> bool:
        """Valida los inputs antes de la ejecución."""
        return True
    
    async def preprocess(self, *args, **kwargs) -> Any:
        """Preprocesa los inputs antes de la ejecución principal."""
        return args, kwargs
    
    async def postprocess(self, result: Any) -> AgentResult:
        """Postprocesa los resultados antes de retornarlos."""
        return result
    
    def get_metrics(self) -> AgentMetrics:
        """Obtiene las métricas actuales del agente."""
        return AgentMetrics(
            execution_time=0.0,
            success_rate=1.0,
            confidence_score=1.0,
            error_count=0
        )
    
    async def handle_error(self, error: Exception) -> AgentResult:
        """Maneja errores durante la ejecución."""
        return AgentResult(
            success=False,
            data=None,
            error=str(error)
        )
