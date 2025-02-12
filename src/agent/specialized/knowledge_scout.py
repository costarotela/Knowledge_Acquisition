"""
Agente especializado en búsqueda de información.
"""
from typing import List, Dict, Any
import json
import openai
from pydantic import BaseModel, Field

from .base_agent import BaseSpecializedAgent, AgentResult
from ...scrapers.config import ScrapingConfig
from ...auth.security import requires_auth
from ...auth.models import Permission

class SearchResult(BaseModel):
    """Resultado de búsqueda."""
    url: str = Field(description="URL de la fuente")
    title: str = Field(description="Título del contenido")
    snippet: str = Field(description="Extracto relevante del contenido")
    source_type: str = Field(description="Tipo de fuente (blog, docs, etc)")
    relevance_score: float = Field(description="Puntuación de relevancia (0-1)")

class KnowledgeScout(BaseSpecializedAgent):
    """Agente especializado en búsqueda de información."""

    def __init__(self, config: Dict[str, Any]):
        """Inicializa el agente."""
        super().__init__(config)
        self.scraping_config = ScrapingConfig(**config.get('scraping_config', {}))
        self.search_prompt = """
        Genera resultados de búsqueda simulados para la siguiente consulta:
        
        CONSULTA: {query}
        
        IMPORTANTE: Responde SOLO con un objeto JSON válido que tenga exactamente esta estructura:
        {{
            "results": [
                {{
                    "url": "https://example.com/article1",
                    "title": "Título descriptivo del artículo",
                    "snippet": "Extracto informativo que resume el contenido principal del artículo...",
                    "source_type": "blog",
                    "relevance_score": 0.95
                }}
            ]
        }}
        
        REGLAS:
        1. Genera al menos 3 resultados relevantes
        2. Los snippets deben ser informativos y relacionados con la consulta
        3. Los tipos de fuente deben ser: blog, documentation, academic, o news
        4. Las puntuaciones de relevancia deben estar entre 0.6 y 0.95
        5. Las URLs deben ser realistas pero ficticias
        """
    
    async def execute(self, query: str) -> AgentResult:
        """Ejecuta la búsqueda de información."""
        try:
            # Generar resultados simulados
            response = await openai.ChatCompletion.acreate(
                model=self.config.get('model_name', 'gpt-4-turbo-preview'),
                messages=[
                    {
                        "role": "system",
                        "content": "Eres un experto en búsqueda de información. Genera resultados simulados realistas y útiles."
                    },
                    {
                        "role": "user",
                        "content": self.search_prompt.format(query=query)
                    }
                ],
                temperature=0.2,
                response_format={"type": "json_object"}
            )
            
            results_text = response.choices[0].message.content.strip()
            try:
                results_data = json.loads(results_text)
                search_results = [
                    SearchResult(**result)
                    for result in results_data.get('results', [])
                ]
            except Exception as e:
                return AgentResult(
                    success=False,
                    error=f"Error procesando resultados: {str(e)}"
                )
            
            if not search_results:
                return AgentResult(
                    success=False,
                    error="No se encontraron resultados relevantes"
                )
            
            # Ordenar por relevancia
            search_results.sort(key=lambda x: x.relevance_score, reverse=True)
            
            return AgentResult(
                success=True,
                data=search_results,
                metadata={
                    'total_results': len(search_results),
                    'avg_relevance': sum(r.relevance_score for r in search_results) / len(search_results),
                    'source_types': list(set(r.source_type for r in search_results))
                }
            )
            
        except Exception as e:
            return AgentResult(
                success=False,
                error=f"Error en la búsqueda: {str(e)}"
            )
