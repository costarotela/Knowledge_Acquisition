"""
Orquestador para el proceso de adquisición de conocimiento.
Coordina y decide el flujo de trabajo entre los agentes especializados.
"""
from typing import Dict, Any, Optional, List
import json
import logging
from pydantic import BaseModel, Field
from enum import Enum

from .specialized import (
    KnowledgeScout,
    FactValidator,
    KnowledgeSynthesizer,
    MetaEvaluator
)
from .specialized.base_agent import AgentResult

logger = logging.getLogger(__name__)

class TaskPriority(Enum):
    """Prioridad de la tarea."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class TaskType(Enum):
    """Tipo de tarea de adquisición."""
    RESEARCH = "research"  # Investigación profunda
    VALIDATION = "validation"  # Solo validación
    SYNTHESIS = "synthesis"  # Solo síntesis
    EVALUATION = "evaluation"  # Solo evaluación

class AcquisitionTask(BaseModel):
    """Tarea de adquisición de conocimiento."""
    query: str = Field(description="Consulta o pregunta a investigar")
    task_type: TaskType = Field(default=TaskType.RESEARCH)
    priority: TaskPriority = Field(default=TaskPriority.MEDIUM)
    context: Dict[str, Any] = Field(default_factory=dict)
    requirements: Dict[str, Any] = Field(default_factory=dict)

class ExecutionStep(BaseModel):
    """Paso de ejecución en el proceso."""
    agent: str
    status: str
    result: Optional[AgentResult] = None
    metrics: Dict[str, Any] = Field(default_factory=dict)

class KnowledgeOrchestrator:
    """Orquestador inteligente del proceso de adquisición de conocimiento."""

    def __init__(self, config: Dict[str, Any]):
        """Inicializa el orquestador."""
        self.config = config
        self.scout = KnowledgeScout(config)
        self.validator = FactValidator(config)
        self.synthesizer = KnowledgeSynthesizer(config)
        self.evaluator = MetaEvaluator(config)
        self.execution_history: List[ExecutionStep] = []
    
    def _plan_execution(self, task: AcquisitionTask) -> List[str]:
        """Planifica la secuencia de agentes basada en el tipo de tarea."""
        if task.task_type == TaskType.RESEARCH:
            return ["scout", "validator", "synthesizer", "evaluator"]
        elif task.task_type == TaskType.VALIDATION:
            return ["validator", "evaluator"]
        elif task.task_type == TaskType.SYNTHESIS:
            return ["synthesizer", "evaluator"]
        elif task.task_type == TaskType.EVALUATION:
            return ["evaluator"]
        
        return ["scout", "validator", "synthesizer", "evaluator"]
    
    def _should_retry(self, step: ExecutionStep, task: AcquisitionTask) -> bool:
        """Determina si un paso fallido debe reintentarse."""
        if task.priority == TaskPriority.HIGH:
            return True
        if step.agent in ["validator", "evaluator"]:
            return True
        return False
    
    async def _execute_step(self, agent_name: str, data: Any, task: AcquisitionTask) -> ExecutionStep:
        """Ejecuta un paso específico del proceso."""
        step = ExecutionStep(agent=agent_name, status="running")
        
        try:
            agent = getattr(self, agent_name)
            if agent_name == "scout":
                result = await agent.execute(task.query)
            elif agent_name == "validator":
                result = await agent.execute(data)
            elif agent_name == "synthesizer":
                # Si es una tarea de síntesis y tenemos un EvaluationResult,
                # lo convertimos a un formato que el sintetizador pueda usar
                if task.task_type == TaskType.SYNTHESIS and hasattr(data, 'metadata'):
                    from .specialized.fact_validator import ValidationResult
                    validated_facts = [
                        ValidationResult(
                            content=data.metadata.get('summary', ''),
                            source=task.query,
                            confidence=data.score,
                            validation_notes=data.strengths + data.weaknesses
                        )
                    ]
                    result = await agent.execute(validated_facts, task.context)
                else:
                    result = await agent.execute(data, task.context)
            elif agent_name == "evaluator":
                result = await agent.execute(data)
            
            step.result = result
            step.status = "completed" if result.success else "failed"
            step.metrics = agent.get_metrics().dict()
            
        except Exception as e:
            logger.error(f"Error en {agent_name}: {str(e)}")
            step.status = "failed"
            step.result = AgentResult(success=False, error=str(e))
            
        self.execution_history.append(step)
        return step
    
    async def execute(self, task: AcquisitionTask) -> AgentResult:
        """Ejecuta el proceso de adquisición de conocimiento."""
        logger.info(f"Iniciando tarea: {task.query} (Tipo: {task.task_type}, Prioridad: {task.priority})")
        
        # Planificar ejecución
        execution_plan = self._plan_execution(task)
        current_data = None
        
        try:
            # Ejecutar cada paso
            for agent_name in execution_plan:
                logger.info(f"Ejecutando agente: {agent_name}")
                
                # Ejecutar paso
                step = await self._execute_step(agent_name, current_data, task)
                
                # Manejar resultado
                if not step.result.success:
                    if self._should_retry(step, task):
                        logger.info(f"Reintentando {agent_name}...")
                        step = await self._execute_step(agent_name, current_data, task)
                    
                    if not step.result.success:
                        return step.result
                
                current_data = step.result.data
            
            # Preparar resultado final
            return AgentResult(
                success=True,
                data=current_data,
                metadata={
                    'execution_history': [step.dict() for step in self.execution_history],
                    'task_info': task.dict(),
                    'context': task.context
                }
            )
            
        except Exception as e:
            logger.error(f"Error en orquestación: {str(e)}")
            return AgentResult(
                success=False,
                error=str(e),
                metadata={'execution_history': [step.dict() for step in self.execution_history]}
            )
