"""
Módulo de agentes especializados para diferentes aspectos de la adquisición de conocimiento.
Cada agente se enfoca en una tarea específica y trabaja en conjunto con los demás.
"""

from .knowledge_scout import KnowledgeScout
from .fact_validator import FactValidator
from .knowledge_synthesizer import KnowledgeSynthesizer
from .meta_evaluator import MetaEvaluator

__all__ = [
    'KnowledgeScout',
    'FactValidator',
    'KnowledgeSynthesizer',
    'MetaEvaluator'
]
