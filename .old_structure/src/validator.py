from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.runnables import RunnablePassthrough
import logging
from typing import Tuple, Dict, Any
import asyncio
from concurrent.futures import ThreadPoolExecutor
import json
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ContentMetrics:
    def __init__(self):
        self.chunks_analyzed = 0
        self.relevant_chunks = 0
        self.total_novelty_score = 0.0
        self.total_evidence_score = 0.0
        self.key_concepts = set()
        self.citations = set()
        self.start_time = datetime.now()
    
    def update(self, analysis_result: Dict[str, Any]):
        self.chunks_analyzed += 1
        if analysis_result.get("es_relevante", False):
            self.relevant_chunks += 1
            self.total_novelty_score += analysis_result.get("novedad", 0.0)
            self.total_evidence_score += analysis_result.get("evidencia_cientifica", 0.0)
            
            # Actualizar conceptos clave
            if "conceptos_clave" in analysis_result:
                self.key_concepts.update(analysis_result["conceptos_clave"])
            
            # Actualizar citas y referencias
            if "referencias" in analysis_result:
                self.citations.update(analysis_result["referencias"])
    
    def get_summary(self) -> Dict[str, Any]:
        duration = (datetime.now() - self.start_time).total_seconds()
        relevant_ratio = self.relevant_chunks / max(1, self.chunks_analyzed)
        avg_novelty = self.total_novelty_score / max(1, self.relevant_chunks)
        avg_evidence = self.total_evidence_score / max(1, self.relevant_chunks)
        
        return {
            "chunks_totales": self.chunks_analyzed,
            "chunks_relevantes": self.relevant_chunks,
            "ratio_relevancia": relevant_ratio,
            "novedad_promedio": avg_novelty,
            "evidencia_promedio": avg_evidence,
            "conceptos_clave": list(self.key_concepts),
            "total_referencias": len(self.citations),
            "tiempo_analisis": duration,
            "referencias": list(self.citations)
        }

class NutritionValidator:
    def __init__(self, openai_api_key: str):
        self.llm = ChatOpenAI(temperature=0, api_key=openai_api_key)
        self.prompt = PromptTemplate(
            input_variables=["transcript"],
            template="""Eres un experto en nutrición con amplio conocimiento del estado actual de la ciencia nutricional. 
Analiza este contenido y evalúa:

1. Relevancia nutricional
2. Novedad de la información
3. Respaldo científico
4. Conceptos clave
5. Referencias o citas mencionadas

Contenido a analizar:
{transcript}

Responde SOLO en formato JSON con este esquema exacto:
{{
    "es_relevante": true/false,
    "confiabilidad": float (0-1),
    "peligroso": true/false,
    "novedad": float (0-1),
    "evidencia_cientifica": float (0-1),
    "conceptos_clave": ["concepto1", "concepto2", ...],
    "referencias": ["referencia1", "referencia2", ...],
    "razones": "explicación detallada que incluya:\n- Por qué es o no relevante\n- Qué aporta de nuevo\n- Calidad de la evidencia presentada"
}}"""
        )
        self.chain = self.prompt | self.llm
        self.executor = ThreadPoolExecutor(max_workers=2)
        self.metrics = ContentMetrics()
    
    async def validate_content_async(self, transcript: str) -> Tuple[bool, float, str]:
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                self.executor,
                lambda: self.chain.invoke({"transcript": transcript})
            )
            
            try:
                content = response.content
                start = content.find('{')
                end = content.rfind('}') + 1
                if start >= 0 and end > start:
                    json_str = content[start:end]
                    result = json.loads(json_str)
                    
                    # Actualizar métricas
                    self.metrics.update(result)
                    
                    return (
                        result.get("es_relevante", False),
                        result.get("confiabilidad", 0.0),
                        result.get("razones", "No se proporcionaron razones")
                    )
                else:
                    logger.error("No se encontró JSON válido en la respuesta")
                    return False, 0.0, "Formato de respuesta inválido"
            except json.JSONDecodeError as e:
                logger.error(f"No se pudo parsear la respuesta como JSON: {e}")
                return False, 0.0, "Error al procesar la respuesta"
            
        except Exception as e:
            logger.error(f"Error en la validación: {e}")
            return False, 0.0, f"Error en la validación: {str(e)}"
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """
        Obtiene un resumen de las métricas del contenido analizado.
        
        Returns:
            Dict[str, Any]: Resumen de métricas incluyendo novedad, evidencia, conceptos clave, etc.
        """
        return self.metrics.get_summary()
    
    def validate_content(self, transcript: str) -> Tuple[bool, float, str]:
        try:
            response = self.chain.invoke({"transcript": transcript})
            try:
                content = response.content
                start = content.find('{')
                end = content.rfind('}') + 1
                if start >= 0 and end > start:
                    json_str = content[start:end]
                    result = json.loads(json_str)
                    
                    # Actualizar métricas
                    self.metrics.update(result)
                    
                    return (
                        result.get("es_relevante", False),
                        result.get("confiabilidad", 0.0),
                        result.get("razones", "No se proporcionaron razones")
                    )
                else:
                    logger.error("No se encontró JSON válido en la respuesta")
                    return False, 0.0, "Formato de respuesta inválido"
            except json.JSONDecodeError as e:
                logger.error(f"No se pudo parsear la respuesta como JSON: {e}")
                return False, 0.0, "Error al procesar la respuesta"
        except Exception as e:
            logger.error(f"Error en la validación: {e}")
            return False, 0.0, f"Error en la validación: {str(e)}"
