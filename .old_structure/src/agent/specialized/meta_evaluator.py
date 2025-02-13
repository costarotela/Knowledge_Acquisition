"""
Agente especializado en auto-evaluación y meta-cognición.
"""
from typing import List, Dict, Any
import json
import openai
from pydantic import BaseModel, Field

from .base_agent import BaseSpecializedAgent, AgentResult
from .knowledge_synthesizer import SynthesizedKnowledge, KnowledgeNode
from ...auth.security import requires_auth
from ...auth.models import Permission

class EvaluationResult(BaseModel):
    """Resultado de evaluación."""
    score: float = Field(description="Puntuación general de calidad")
    strengths: List[str] = Field(description="Puntos fuertes identificados")
    weaknesses: List[str] = Field(description="Áreas de mejora identificadas")
    gaps: List[str] = Field(description="Vacíos de conocimiento detectados")
    suggestions: List[str] = Field(description="Sugerencias de mejora")
    metadata: Dict[str, Any] = Field(default_factory=dict)

class MetaEvaluator(BaseSpecializedAgent):
    """Agente especializado en evaluación y meta-cognición."""

    def __init__(self, config: Dict[str, Any]):
        """Inicializa el agente."""
        super().__init__(config)
        self.evaluation_prompt = """
        Evalúa la calidad y completitud del siguiente conocimiento sintetizado:
        
        RESUMEN:
        {summary}
        
        NODOS DE CONOCIMIENTO:
        {nodes}
        
        RELACIONES:
        {relationships}
        
        INSTRUCCIONES:
        1. Evalúa la calidad y profundidad del conocimiento
        2. Identifica puntos fuertes y débiles
        3. Detecta vacíos o áreas incompletas
        4. Sugiere mejoras específicas
        
        IMPORTANTE: Responde SOLO con un objeto JSON válido que tenga esta estructura exacta:
        {{
            "score": 0.85,
            "strengths": [
                "fortaleza1",
                "fortaleza2"
            ],
            "weaknesses": [
                "debilidad1",
                "debilidad2"
            ],
            "gaps": [
                "vacío1",
                "vacío2"
            ],
            "suggestions": [
                "sugerencia1",
                "sugerencia2"
            ]
        }}
        """
    
    async def execute(self, knowledge: SynthesizedKnowledge) -> AgentResult:
        """Ejecuta la evaluación del conocimiento."""
        try:
            # Preparar datos para evaluación
            nodes_text = "\n".join([
                f"- [{node.id}] {node.type}: {node.content}"
                for node in knowledge.nodes
            ])
            
            relationships_text = "\n".join([
                f"- {rel['source']} --({rel['type']})--> {rel['target']}"
                for rel in knowledge.relationships
            ])
            
            # Generar evaluación
            response = await openai.ChatCompletion.acreate(
                model=self.config.get('model_name', 'gpt-4-turbo-preview'),
                messages=[
                    {
                        "role": "system",
                        "content": "Eres un experto en evaluación y meta-análisis de conocimiento. Responde SOLO con JSON válido."
                    },
                    {
                        "role": "user",
                        "content": self.evaluation_prompt.format(
                            summary=knowledge.summary,
                            nodes=nodes_text,
                            relationships=relationships_text
                        )
                    }
                ],
                temperature=0,
                response_format={"type": "json_object"}
            )
            
            evaluation_text = response.choices[0].message.content.strip()
            try:
                evaluation_data = json.loads(evaluation_text)
                evaluation = EvaluationResult(
                    score=evaluation_data['score'],
                    strengths=evaluation_data['strengths'],
                    weaknesses=evaluation_data['weaknesses'],
                    gaps=evaluation_data['gaps'],
                    suggestions=evaluation_data['suggestions'],
                    metadata={
                        'total_nodes': len(knowledge.nodes),
                        'total_relationships': len(knowledge.relationships)
                    }
                )
            except Exception as e:
                return AgentResult(
                    success=False,
                    error=f"Error procesando evaluación: {str(e)}"
                )
            
            return AgentResult(
                success=True,
                data=evaluation
            )
            
        except Exception as e:
            return AgentResult(
                success=False,
                error=f"Error en la evaluación: {str(e)}"
            )
