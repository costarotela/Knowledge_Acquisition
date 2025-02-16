"""
Generador de contenido para marketing.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import logging
import json
from openai import OpenAI
from ...core.config import config
from ...core.schemas import TravelPackage, Opportunity

class ContentGenerator:
    """
    Generador de contenido para marketing.
    
    Características:
    1. Generación de reseñas de temporada
    2. Creación de contenido promocional
    3. Resúmenes de oportunidades
    4. Material para redes sociales
    """
    
    def __init__(self):
        """Inicializar cliente OpenAI."""
        self.client = OpenAI(api_key=config.OPENAI_API_KEY)
        self.logger = logging.getLogger(__name__)
    
    async def generate_season_review(
        self,
        destination: str,
        season: str,
        packages: List[TravelPackage]
    ) -> Dict[str, Any]:
        """Generar reseña de temporada."""
        try:
            # Preparar contexto
            context = {
                "destination": destination,
                "season": season,
                "packages": [
                    {
                        "type": p.type.value,
                        "price": p.price,
                        "includes": p.includes,
                        "availability": p.availability
                    }
                    for p in packages
                ]
            }
            
            # Generar reseña con OpenAI
            response = await self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": "Eres un experto en turismo generando una reseña de temporada."
                    },
                    {
                        "role": "user",
                        "content": f"Genera una reseña detallada para {destination} en temporada {season} basada en esta información: {json.dumps(context)}"
                    }
                ]
            )
            
            review = response.choices[0].message.content
            
            return {
                "destination": destination,
                "season": season,
                "review": review,
                "data": context,
                "created_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error generando reseña: {str(e)}")
            raise
    
    async def generate_promotion(
        self,
        opportunity: Opportunity,
        style: str = "social_media"
    ) -> Dict[str, Any]:
        """Generar contenido promocional."""
        try:
            # Preparar contexto
            context = {
                "type": opportunity.type,
                "savings": opportunity.savings,
                "valid_until": opportunity.valid_until.isoformat(),
                "score": opportunity.score
            }
            
            # Seleccionar prompt según estilo
            prompts = {
                "social_media": "Crea un post atractivo para redes sociales",
                "email": "Redacta un email promocional persuasivo",
                "website": "Escribe una descripción para el sitio web"
            }
            
            # Generar contenido con OpenAI
            response = await self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": "Eres un experto en marketing turístico."
                    },
                    {
                        "role": "user",
                        "content": f"{prompts.get(style, prompts['social_media'])} para esta oportunidad: {json.dumps(context)}"
                    }
                ]
            )
            
            content = response.choices[0].message.content
            
            return {
                "opportunity_id": opportunity.id,
                "style": style,
                "content": content,
                "context": context,
                "created_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error generando promoción: {str(e)}")
            raise
    
    async def generate_package_summary(
        self,
        package: TravelPackage,
        target: str = "customer"
    ) -> Dict[str, Any]:
        """Generar resumen de paquete."""
        try:
            # Preparar contexto
            context = {
                "type": package.type.value,
                "destination": package.destination,
                "price": package.price,
                "includes": package.includes,
                "dates": {
                    "start": package.start_date.isoformat(),
                    "end": package.end_date.isoformat()
                }
            }
            
            # Seleccionar prompt según target
            prompts = {
                "customer": "Crea una descripción atractiva para el cliente",
                "agent": "Genera un resumen técnico para el agente",
                "marketing": "Escribe una descripción promocional"
            }
            
            # Generar resumen con OpenAI
            response = await self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": "Eres un experto en descripción de paquetes turísticos."
                    },
                    {
                        "role": "user",
                        "content": f"{prompts.get(target, prompts['customer'])} para este paquete: {json.dumps(context)}"
                    }
                ]
            )
            
            summary = response.choices[0].message.content
            
            return {
                "package_id": package.id,
                "target": target,
                "summary": summary,
                "context": context,
                "created_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error generando resumen: {str(e)}")
            raise
