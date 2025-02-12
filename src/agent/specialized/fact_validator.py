"""
Agente especializado en validación de información.
"""
from typing import List, Dict, Any
import json
import openai
from pydantic import BaseModel, Field

from .base_agent import BaseSpecializedAgent, AgentResult
from .knowledge_scout import SearchResult
from ...auth.security import requires_auth
from ...auth.models import Permission

class ValidationResult(BaseModel):
    """Resultado de validación."""
    content: str = Field(description="Contenido validado")
    source: str = Field(description="Fuente del contenido")
    confidence: float = Field(description="Nivel de confianza (0-1)")
    validation_notes: List[str] = Field(description="Notas de validación")

class FactValidator(BaseSpecializedAgent):
    """Agente especializado en validación de información."""

    def __init__(self, config: Dict[str, Any]):
        """Inicializa el agente."""
        super().__init__(config)
        self.min_confidence = config.get('min_confidence', 0.3)
        self.validation_prompt = """
        Valida la siguiente información y determina su confiabilidad:
        
        CONTENIDO:
        {content}
        
        FUENTE: {source}
        TIPO: {source_type}
        
        INSTRUCCIONES:
        1. Evalúa la credibilidad de la fuente
        2. Verifica la consistencia del contenido
        3. Identifica posibles sesgos o errores
        4. Asigna un nivel de confianza (0-1)
        
        REGLAS:
        - Asigna un nivel de confianza alto (>0.8) si la información es precisa y bien respaldada
        - Asigna un nivel medio (0.5-0.8) si la información es útil pero necesita verificación
        - Asigna un nivel bajo (<0.5) si la información es dudosa o poco confiable
        
        IMPORTANTE: Responde SOLO con un objeto JSON válido que tenga esta estructura exacta:
        {{
            "content": "contenido validado y refinado",
            "confidence": 0.95,
            "validation_notes": [
                "La fuente es confiable",
                "El contenido está bien documentado",
                "No se detectan sesgos significativos"
            ]
        }}
        """
    
    async def execute(self, search_results: List[SearchResult]) -> AgentResult:
        """Ejecuta la validación de información."""
        try:
            if not search_results:
                return AgentResult(
                    success=False,
                    error="No hay resultados para validar"
                )
            
            validated_results = []
            validation_errors = []
            
            for result in search_results:
                try:
                    validation = await self._validate_result(result)
                    if validation.get('confidence', 0) >= self.min_confidence:
                        validated_results.append(
                            ValidationResult(
                                content=validation.get('content', result.snippet),
                                source=result.url,
                                confidence=validation.get('confidence', 0.5),
                                validation_notes=validation.get('validation_notes', [])
                            )
                        )
                except Exception as e:
                    validation_errors.append(f"Error validando {result.url}: {str(e)}")
            
            if not validated_results:
                return AgentResult(
                    success=False,
                    error=(
                        "No se encontraron resultados con suficiente confianza. " +
                        (f"Errores: {'; '.join(validation_errors)}" if validation_errors else "")
                    )
                )
            
            return AgentResult(
                success=True,
                data=validated_results,
                metadata={
                    'total_validated': len(validated_results),
                    'avg_confidence': sum(r.confidence for r in validated_results) / len(validated_results),
                    'validation_errors': validation_errors
                }
            )
            
        except Exception as e:
            return AgentResult(
                success=False,
                error=f"Error en el proceso de validación: {str(e)}"
            )
    
    async def _validate_result(self, result: SearchResult) -> Dict[str, Any]:
        """Valida un resultado de búsqueda usando OpenAI."""
        try:
            response = await openai.ChatCompletion.acreate(
                model=self.config.get('model_name', 'gpt-4-turbo-preview'),
                messages=[
                    {
                        "role": "system",
                        "content": "Eres un experto en fact-checking y validación de información. Responde SOLO con JSON válido."
                    },
                    {
                        "role": "user",
                        "content": self.validation_prompt.format(
                            content=result.snippet,
                            source=result.url,
                            source_type=result.source_type
                        )
                    }
                ],
                temperature=0,
                response_format={"type": "json_object"}
            )
            
            validation_text = response.choices[0].message.content.strip()
            try:
                return json.loads(validation_text)
            except json.JSONDecodeError:
                raise Exception(f"Respuesta no válida: {validation_text}")
            
        except Exception as e:
            raise Exception(f"Error validando resultado: {str(e)}")
