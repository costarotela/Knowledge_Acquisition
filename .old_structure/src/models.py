from pydantic import BaseModel, HttpUrl
from typing import List, Optional, Dict
from enum import Enum
from datetime import datetime

class NutritionCategory(str, Enum):
    MACRONUTRIENTES = "macronutrientes"
    DIETAS_ESPECIALES = "dietas_especiales"
    SUPLEMENTACION = "suplementacion"
    RECETAS = "recetas_saludables"

class VideoContent(BaseModel):
    url: str  # Cambiado de HttpUrl a str
    transcript: str
    key_frames: List[str]  # URLs de imágenes clave
    duration: float
    relevance_score: float
    processed_at: datetime = datetime.now()

    @classmethod
    def from_url(cls, url: HttpUrl, **kwargs):
        """Crea una instancia usando HttpUrl y la convierte a str"""
        return cls(url=str(url), **kwargs)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class NutritionKnowledge(BaseModel):
    summary: str
    raw_data: str
    categories: List[NutritionCategory]
    visual_aids: List[str]  # Imágenes procesadas
    source: str  # Cambiado de HttpUrl a str
    metadata: Dict = {}
    created_at: datetime = datetime.now()
    updated_at: datetime = datetime.now()

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
