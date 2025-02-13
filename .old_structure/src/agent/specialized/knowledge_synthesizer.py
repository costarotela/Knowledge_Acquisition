"""
Agente especializado en síntesis de conocimiento.
"""
from typing import List, Dict, Any
import json
import openai
from pydantic import BaseModel, Field

from .base_agent import BaseSpecializedAgent, AgentResult
from .fact_validator import ValidationResult

class KnowledgeNode(BaseModel):
    """Nodo de conocimiento."""
    id: str = Field(description="Identificador único del nodo")
    type: str = Field(description="Tipo de nodo (concepto, técnica, etc)")
    content: str = Field(description="Contenido del nodo")
    confidence: float = Field(description="Nivel de confianza (0-1)")
    sources: List[str] = Field(description="Fuentes que respaldan el nodo")

class SynthesizedKnowledge(BaseModel):
    """Conocimiento sintetizado."""
    nodes: List[KnowledgeNode] = Field(description="Nodos de conocimiento")
    relationships: List[Dict[str, Any]] = Field(description="Relaciones entre nodos")
    summary: str = Field(description="Resumen del conocimiento")
    metadata: Dict[str, Any] = Field(default_factory=dict)

class KnowledgeSynthesizer(BaseSpecializedAgent):
    """Agente especializado en síntesis de conocimiento."""

    def __init__(self, config: Dict[str, Any]):
        """Inicializa el agente."""
        super().__init__(config)
        self.synthesis_prompt = """
        Sintetiza el siguiente conocimiento validado:
        
        HECHOS VALIDADOS:
        {facts}
        
        CONTEXTO:
        {context}
        
        INSTRUCCIONES:
        1. Identifica conceptos clave y sus relaciones
        2. Organiza el conocimiento de forma coherente
        3. Genera un resumen integrador
        4. Establece conexiones entre conceptos
        
        IMPORTANTE: Responde SOLO con un objeto JSON válido que tenga esta estructura exacta:
        {{
            "nodes": [
                {{
                    "id": "node1",
                    "type": "concepto|técnica|práctica|principio",
                    "content": "descripción del nodo",
                    "confidence": 0.95,
                    "sources": ["url1", "url2"]
                }}
            ],
            "relationships": [
                {{
                    "source": "node1",
                    "target": "node2",
                    "type": "tipo_de_relación",
                    "description": "descripción de la relación"
                }}
            ],
            "summary": "resumen integrador del conocimiento"
        }}
        """
    
    async def execute(
        self,
        validated_facts: List[ValidationResult],
        context: Dict[str, Any]
    ) -> AgentResult:
        """Ejecuta la síntesis de conocimiento."""
        try:
            # Si no hay hechos validados, usar el contexto directamente
            if not validated_facts and context:
                # Convertir objetos a diccionarios antes de serializar
                context_dict = {
                    k: v.dict() if hasattr(v, 'dict') else v
                    for k, v in context.items()
                }
                facts_text = json.dumps(context_dict, indent=2)
            else:
                # Preparar hechos validados para síntesis
                facts_text = "\n".join([
                    f"- [{fact.source}] ({fact.confidence:.2f}): {fact.content}"
                    for fact in validated_facts
                ])
            
            # Preparar contexto
            context_dict = {
                k: v.dict() if hasattr(v, 'dict') else v
                for k, v in context.items()
            }
            context_text = json.dumps(context_dict, indent=2)
            
            # Generar síntesis
            synthesis = await self._generate_synthesis(facts_text, context_text)
            
            # Crear resultado
            knowledge = SynthesizedKnowledge(
                nodes=synthesis['nodes'],
                relationships=synthesis['relationships'],
                summary=synthesis['summary'],
                metadata={
                    'context': context_dict,
                    'total_nodes': len(synthesis['nodes']),
                    'total_relationships': len(synthesis['relationships'])
                }
            )
            
            return AgentResult(
                success=True,
                data=knowledge
            )
            
        except Exception as e:
            return AgentResult(
                success=False,
                error=str(e)
            )
    
    async def _generate_synthesis(
        self,
        facts: str,
        context: str
    ) -> Dict[str, Any]:
        """Genera la síntesis usando OpenAI."""
        try:
            response = await openai.ChatCompletion.acreate(
                model=self.config.get('model_name', 'gpt-4-turbo-preview'),
                messages=[
                    {
                        "role": "system",
                        "content": "Eres un experto en síntesis y organización de conocimiento. Responde SOLO con JSON válido."
                    },
                    {
                        "role": "user",
                        "content": self.synthesis_prompt.format(
                            facts=facts,
                            context=context
                        )
                    }
                ],
                temperature=0,
                response_format={"type": "json_object"}
            )
            
            synthesis_text = response.choices[0].message.content.strip()
            try:
                return json.loads(synthesis_text)
            except json.JSONDecodeError:
                raise Exception(f"Respuesta no válida: {synthesis_text}")
            
        except Exception as e:
            raise Exception(f"Error generando síntesis: {str(e)}")
