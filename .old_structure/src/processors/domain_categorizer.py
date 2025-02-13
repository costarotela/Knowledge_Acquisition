"""
Categorizador de dominios de conocimiento usando técnicas ligeras y eficientes.
"""

from typing import List, Dict, Optional
import logging
import json
import os
from pathlib import Path
import re
from ..models.video_models import KnowledgeDomain

logger = logging.getLogger(__name__)

class DomainCategorizer:
    """Categoriza contenido en dominios de conocimiento usando técnicas ligeras."""
    
    def __init__(self):
        """Inicializa el categorizador con la jerarquía de dominios."""
        self.domain_hierarchy = self._load_domain_hierarchy()
        
    def _load_domain_hierarchy(self) -> Dict[str, Dict]:
        """
        Carga la jerarquía de dominios desde un archivo JSON si existe,
        sino usa la jerarquía por defecto.
        """
        default_hierarchy = {
            "nutrition": {
                "sub_domains": ["sports_nutrition", "dietary_supplements", "meal_planning"],
                "keywords": ["protein", "carbohydrates", "vitamins", "minerals", "diet",
                           "nutrition", "food", "meal", "supplement", "macro"],
                "patterns": [
                    r"\b(protein|carb|vitamin|mineral|nutrient)\w*\b",
                    r"\b(diet|nutrition|supplement)\w*\b",
                    r"\b(meal|food|eating)\s+(plan|prep|schedule)\b"
                ]
            },
            "fitness": {
                "sub_domains": ["strength_training", "cardio", "flexibility"],
                "keywords": ["exercise", "workout", "training", "muscles", "strength",
                           "cardio", "fitness", "gym", "resistance", "endurance"],
                "patterns": [
                    r"\b(exercise|workout|training|fitness)\w*\b",
                    r"\b(muscle|strength|power)\w*\b",
                    r"\b(cardio|endurance|stamina)\w*\b"
                ]
            },
            "health": {
                "sub_domains": ["preventive_care", "mental_health", "recovery"],
                "keywords": ["wellness", "health", "prevention", "lifestyle", "medical",
                           "recovery", "mental", "stress", "sleep", "mindfulness"],
                "patterns": [
                    r"\b(health|wellness|medical)\w*\b",
                    r"\b(prevention|preventive|preventative)\w*\b",
                    r"\b(mental|stress|anxiety|depression)\w*\b"
                ]
            }
        }
        
        # TODO: Cargar desde archivo JSON si existe
        return default_hierarchy
    
    def _calculate_domain_score(self, text: str, domain: str) -> float:
        """
        Calcula un score para un dominio basado en keywords y patrones.
        
        Args:
            text: Texto a analizar
            domain: Nombre del dominio
            
        Returns:
            Score entre 0 y 1
        """
        domain_data = self.domain_hierarchy[domain]
        text_lower = text.lower()
        
        # Contar keywords
        keyword_count = sum(1 for kw in domain_data["keywords"] 
                          if kw.lower() in text_lower)
        
        # Contar matches de patrones
        pattern_matches = sum(len(re.findall(pattern, text_lower)) 
                            for pattern in domain_data["patterns"])
        
        # Normalizar scores
        max_possible_keywords = len(domain_data["keywords"])
        max_possible_patterns = len(domain_data["patterns"]) * 5  # Asumimos máximo 5 matches por patrón
        
        keyword_score = keyword_count / max_possible_keywords
        pattern_score = min(1.0, pattern_matches / max_possible_patterns)
        
        # Combinar scores (damos más peso a los patrones)
        final_score = (0.4 * keyword_score + 0.6 * pattern_score)
        
        return final_score
    
    def _extract_key_concepts(self, text: str, domain: str) -> List[str]:
        """
        Extrae conceptos clave específicos del dominio.
        
        Args:
            text: Texto a analizar
            domain: Nombre del dominio
            
        Returns:
            Lista de conceptos clave encontrados
        """
        domain_data = self.domain_hierarchy[domain]
        text_lower = text.lower()
        
        # Encontrar keywords presentes
        concepts = [kw for kw in domain_data["keywords"] 
                   if kw.lower() in text_lower]
        
        # Encontrar matches únicos de patrones
        for pattern in domain_data["patterns"]:
            matches = re.findall(pattern, text_lower)
            concepts.extend([m[0] if isinstance(m, tuple) else m 
                           for m in matches])
        
        # Eliminar duplicados y ordenar
        return sorted(list(set(concepts)))
    
    def _detect_sub_domains(self, text: str, domain: str) -> List[str]:
        """
        Detecta sub-dominios relevantes.
        
        Args:
            text: Texto a analizar
            domain: Nombre del dominio principal
            
        Returns:
            Lista de sub-dominios detectados
        """
        domain_data = self.domain_hierarchy[domain]
        detected = []
        
        for sub_domain in domain_data["sub_domains"]:
            # Por ahora usamos un enfoque simple basado en keywords
            # TODO: Mejorar con patrones específicos para sub-dominios
            if sub_domain.replace("_", " ") in text.lower():
                detected.append(sub_domain)
        
        return detected
    
    def categorize(self, text: str) -> List[KnowledgeDomain]:
        """
        Categoriza el texto en dominios de conocimiento.
        
        Args:
            text: Texto a categorizar
            
        Returns:
            Lista de dominios de conocimiento detectados
        """
        try:
            detected_domains = []
            
            # Calcular scores para cada dominio
            domain_scores = {
                domain: self._calculate_domain_score(text, domain)
                for domain in self.domain_hierarchy.keys()
            }
            
            # Ordenar dominios por score
            sorted_domains = sorted(domain_scores.items(), 
                                 key=lambda x: x[1], 
                                 reverse=True)
            
            # Procesar dominios con score significativo
            for domain_name, score in sorted_domains:
                if score > 0.3:  # Umbral mínimo de confianza
                    # Extraer información adicional
                    key_concepts = self._extract_key_concepts(text, domain_name)
                    sub_domains = self._detect_sub_domains(text, domain_name)
                    
                    # Crear objeto de dominio
                    domain = KnowledgeDomain(
                        name=domain_name,
                        confidence=score,
                        sub_domains=sub_domains,
                        key_concepts=key_concepts,
                        description=f"Dominio detectado con score {score:.2f}"
                    )
                    
                    detected_domains.append(domain)
            
            return detected_domains
            
        except Exception as e:
            logger.error(f"Error al categorizar el texto: {e}")
            return []
