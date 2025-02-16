"""
Sistema de seguimiento y análisis de oportunidades de venta.
Integra información contextual, seguimiento de interacciones
y análisis de patrones para maximizar conversiones.
"""

from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from dataclasses import dataclass
import logging
from .schemas import (
    TravelPackage,
    CustomerProfile,
    SaleRecord,
    Interaction
)

logger = logging.getLogger(__name__)

@dataclass
class OpportunityScore:
    """Puntuación detallada de una oportunidad."""
    total_score: float
    interest_level: float
    urgency_level: float
    budget_match: float
    timing_match: float
    context_relevance: float
    objections: List[str]
    next_actions: List[str]

class OpportunityTracker:
    """
    Sistema avanzado de seguimiento de oportunidades que integra:
    1. Análisis contextual (temporada, eventos, etc.)
    2. Seguimiento de interacciones
    3. Detección de patrones de interés
    4. Sugerencias de acción
    """
    
    def __init__(self):
        self.seasonal_patterns = {
            # Meses de alta demanda por tipo de destino
            'playa': [1, 2, 12],  # Verano
            'ski': [6, 7, 8],     # Invierno
            'ciudad': [3, 4, 9, 10],  # Temporada media
            'naturaleza': [4, 5, 9, 10]  # Primavera/Otoño
        }
        
        self.event_calendar = {
            # Eventos especiales que pueden afectar demanda
            'carnaval': {'month': 2, 'boost': 1.3},
            'semana_santa': {'month': 4, 'boost': 1.4},
            'vacaciones_invierno': {'month': 7, 'boost': 1.5},
            'fin_año': {'month': 12, 'boost': 1.6}
        }
        
    def analyze_opportunity(
        self,
        package: TravelPackage,
        customer: CustomerProfile,
        interactions: List[Interaction],
        similar_sales: List[SaleRecord],
        current_date: Optional[datetime] = None
    ) -> OpportunityScore:
        """
        Analiza una oportunidad de venta considerando múltiples factores.
        """
        current_date = current_date or datetime.now()
        
        # 1. Análisis de interés
        interest_level = self._analyze_interest(
            package,
            customer,
            interactions
        )
        
        # 2. Análisis de urgencia
        urgency_level = self._analyze_urgency(
            package,
            customer,
            interactions,
            current_date
        )
        
        # 3. Análisis de presupuesto
        budget_match = self._analyze_budget_match(
            package,
            customer,
            similar_sales
        )
        
        # 4. Análisis de timing
        timing_match = self._analyze_timing(
            package,
            current_date
        )
        
        # 5. Análisis contextual
        context_relevance = self._analyze_context(
            package,
            customer,
            current_date
        )
        
        # 6. Identificar objeciones
        objections = self._identify_objections(
            package,
            customer,
            interactions
        )
        
        # 7. Sugerir próximas acciones
        next_actions = self._suggest_next_actions(
            package,
            customer,
            interactions,
            objections
        )
        
        # Calcular score total
        total_score = (
            interest_level * 0.3 +
            urgency_level * 0.2 +
            budget_match * 0.2 +
            timing_match * 0.15 +
            context_relevance * 0.15
        )
        
        return OpportunityScore(
            total_score=total_score,
            interest_level=interest_level,
            urgency_level=urgency_level,
            budget_match=budget_match,
            timing_match=timing_match,
            context_relevance=context_relevance,
            objections=objections,
            next_actions=next_actions
        )
    
    def _analyze_interest(
        self,
        package: TravelPackage,
        customer: CustomerProfile,
        interactions: List[Interaction]
    ) -> float:
        """
        Analiza el nivel de interés basado en interacciones.
        """
        if not interactions:
            return 0.3  # Interés base
            
        # Pesos por tipo de interacción
        interaction_weights = {
            'view': 0.1,
            'query': 0.2,
            'compare': 0.3,
            'request_info': 0.4,
            'price_check': 0.5,
            'availability_check': 0.6
        }
        
        # Analizar patrones de interacción
        interest_signals = []
        for interaction in interactions:
            base_weight = interaction_weights.get(
                interaction.type,
                0.1
            )
            
            # Ajustar peso por recencia
            days_ago = (datetime.now() - interaction.timestamp).days
            recency_factor = 1.0 / (1.0 + (days_ago / 7))  # Decae con el tiempo
            
            # Ajustar por duración de interacción
            duration_factor = min(
                interaction.duration_seconds / 300,  # 5 minutos como referencia
                1.0
            )
            
            weighted_signal = (
                base_weight *
                recency_factor *
                duration_factor
            )
            interest_signals.append(weighted_signal)
            
        if not interest_signals:
            return 0.3
            
        # Combinar señales dando más peso a las más recientes
        return min(
            sum(interest_signals) / len(interest_signals),
            1.0
        )
    
    def _analyze_urgency(
        self,
        package: TravelPackage,
        customer: CustomerProfile,
        interactions: List[Interaction],
        current_date: datetime
    ) -> float:
        """
        Analiza el nivel de urgencia de la oportunidad.
        """
        urgency_factors = []
        
        # 1. Urgencia por fecha de viaje
        if package.start_date:
            days_to_trip = (package.start_date - current_date).days
            if days_to_trip < 0:
                return 0.0  # Viaje pasado
            elif days_to_trip < 7:
                urgency_factors.append(1.0)  # Muy urgente
            elif days_to_trip < 30:
                urgency_factors.append(0.7)
            elif days_to_trip < 90:
                urgency_factors.append(0.4)
            else:
                urgency_factors.append(0.2)
                
        # 2. Urgencia por patrón de interacciones
        if interactions:
            recent_interactions = [
                i for i in interactions
                if (current_date - i.timestamp).days < 7
            ]
            interaction_frequency = len(recent_interactions) / 7
            urgency_factors.append(min(interaction_frequency, 1.0))
            
        # 3. Urgencia por disponibilidad
        if hasattr(package, 'availability') and package.availability:
            availability_percent = package.availability
            if availability_percent < 30:
                urgency_factors.append(0.9)
            elif availability_percent < 50:
                urgency_factors.append(0.6)
            else:
                urgency_factors.append(0.3)
                
        # 4. Urgencia por tipo de cliente
        if customer.type == 'corporate':
            urgency_factors.append(0.8)  # Clientes corporativos suelen necesitar respuesta rápida
            
        return max(0.1, sum(urgency_factors) / len(urgency_factors))
    
    def _analyze_budget_match(
        self,
        package: TravelPackage,
        customer: CustomerProfile,
        similar_sales: List[SaleRecord]
    ) -> float:
        """
        Analiza qué tan bien se ajusta el paquete al presupuesto esperado.
        """
        if not similar_sales:
            return 0.5
            
        # Calcular rango de precios típico para este tipo de cliente
        relevant_sales = [
            sale for sale in similar_sales
            if sale.customer_profile.type == customer.type
        ]
        
        if not relevant_sales:
            return 0.5
            
        prices = [sale.price for sale in relevant_sales]
        avg_price = np.mean(prices)
        std_price = np.std(prices)
        
        # Calcular qué tan lejos está el precio del paquete del promedio
        price_distance = abs(package.price - avg_price)
        
        if std_price == 0:
            return 1.0 if price_distance == 0 else 0.0
            
        # Normalizar distancia
        normalized_distance = price_distance / std_price
        
        # Convertir a score (1.0 = precio ideal, 0.0 = muy fuera de rango)
        return max(0.0, 1.0 - (normalized_distance / 3.0))
    
    def _analyze_timing(
        self,
        package: TravelPackage,
        current_date: datetime
    ) -> float:
        """
        Analiza si es el momento adecuado para ofrecer el paquete.
        """
        if not package.start_date:
            return 0.5
            
        # 1. Análisis de temporada
        package_month = package.start_date.month
        destination_type = self._infer_destination_type(package)
        
        seasonal_score = 0.5
        if destination_type in self.seasonal_patterns:
            if package_month in self.seasonal_patterns[destination_type]:
                seasonal_score = 1.0
            else:
                seasonal_score = 0.3
                
        # 2. Análisis de eventos especiales
        event_score = 0.5
        for event, details in self.event_calendar.items():
            if package_month == details['month']:
                event_score = details['boost']
                break
                
        # 3. Tiempo de anticipación ideal
        days_to_trip = (package.start_date - current_date).days
        anticipation_score = 0.0
        
        if days_to_trip > 0:
            if destination_type == 'playa':
                # Playas: 3-6 meses de anticipación
                ideal_days = 120
            elif destination_type == 'ski':
                # Ski: 4-8 meses de anticipación
                ideal_days = 180
            else:
                # Otros: 2-4 meses de anticipación
                ideal_days = 90
                
            anticipation_score = 1.0 - min(
                abs(days_to_trip - ideal_days) / ideal_days,
                1.0
            )
            
        return (seasonal_score * 0.4 + event_score * 0.3 + anticipation_score * 0.3)
    
    def _analyze_context(
        self,
        package: TravelPackage,
        customer: CustomerProfile,
        current_date: datetime
    ) -> float:
        """
        Analiza relevancia contextual del paquete.
        """
        context_scores = []
        
        # 1. Contexto temporal
        month = current_date.month
        destination_type = self._infer_destination_type(package)
        
        if destination_type in self.seasonal_patterns:
            temporal_relevance = (
                1.0 if month in self.seasonal_patterns[destination_type]
                else 0.3
            )
            context_scores.append(temporal_relevance)
            
        # 2. Contexto del cliente
        if customer.type == 'family':
            # Verificar si coincide con vacaciones escolares
            if month in [1, 2, 7, 12]:  # Vacaciones típicas
                context_scores.append(1.0)
            else:
                context_scores.append(0.4)
                
        elif customer.type == 'corporate':
            # Evitar temporada alta para corporativos
            if month in [1, 2, 7, 12]:
                context_scores.append(0.4)
            else:
                context_scores.append(0.8)
                
        # 3. Contexto de eventos
        for event, details in self.event_calendar.items():
            if month == details['month']:
                context_scores.append(details['boost'])
                break
                
        return sum(context_scores) / len(context_scores) if context_scores else 0.5
    
    def _identify_objections(
        self,
        package: TravelPackage,
        customer: CustomerProfile,
        interactions: List[Interaction]
    ) -> List[str]:
        """
        Identifica posibles objeciones basadas en interacciones.
        """
        objections = []
        
        # Analizar interacciones para detectar patrones de objeción
        if interactions:
            price_checks = sum(
                1 for i in interactions
                if i.type == 'price_check'
            )
            if price_checks > 2:
                objections.append("Posible preocupación por precio")
                
            availability_checks = sum(
                1 for i in interactions
                if i.type == 'availability_check'
            )
            if availability_checks > 2:
                objections.append("Preocupación por disponibilidad")
                
        # Analizar ajuste de precio
        if customer.type == 'premium':
            if package.accommodation and package.accommodation.stars < 4:
                objections.append(
                    "Calidad de alojamiento puede ser insuficiente para cliente premium"
                )
                
        elif customer.type == 'family':
            if not package.activities or not any(
                'niños' in a.title.lower() or 'familia' in a.title.lower()
                for a in package.activities
            ):
                objections.append("Falta de actividades familiares")
                
        return objections
    
    def _suggest_next_actions(
        self,
        package: TravelPackage,
        customer: CustomerProfile,
        interactions: List[Interaction],
        objections: List[str]
    ) -> List[str]:
        """
        Sugiere próximas acciones basadas en el análisis.
        """
        actions = []
        
        # Acciones basadas en objeciones
        for objection in objections:
            if "precio" in objection.lower():
                actions.append(
                    "Presentar desglose de valor y beneficios incluidos"
                )
                actions.append(
                    "Explorar opciones de financiamiento"
                )
            elif "disponibilidad" in objection.lower():
                actions.append(
                    "Verificar disponibilidad en fechas alternativas"
                )
            elif "actividades" in objection.lower():
                actions.append(
                    "Proponer actividades adicionales personalizadas"
                )
                
        # Acciones basadas en interacciones
        if interactions:
            last_interaction = max(
                interactions,
                key=lambda x: x.timestamp
            )
            
            days_since_last = (
                datetime.now() - last_interaction.timestamp
            ).days
            
            if days_since_last > 7:
                actions.append(
                    "Realizar seguimiento proactivo"
                )
                
            if days_since_last > 14:
                actions.append(
                    "Presentar alternativas actualizadas"
                )
                
        # Acciones basadas en tipo de cliente
        if customer.type == 'premium':
            actions.append(
                "Destacar servicios exclusivos y personalizados"
            )
        elif customer.type == 'corporate':
            actions.append(
                "Presentar beneficios corporativos y facilidades de gestión"
            )
        elif customer.type == 'family':
            actions.append(
                "Enfatizar actividades familiares y facilidades para niños"
            )
            
        return actions
    
    def _infer_destination_type(self, package: TravelPackage) -> str:
        """
        Infiere el tipo de destino basado en descripción y actividades.
        """
        keywords = {
            'playa': ['playa', 'mar', 'costa', 'caribe', 'isla'],
            'ski': ['ski', 'nieve', 'montaña', 'invierno'],
            'ciudad': ['ciudad', 'urbano', 'metropolitan'],
            'naturaleza': ['parque', 'natural', 'eco', 'aventura']
        }
        
        text_to_analyze = (
            f"{package.title} {package.description} " +
            " ".join(
                a.title for a in package.activities
                if a.title
            )
        ).lower()
        
        scores = {
            dest_type: sum(
                1 for keyword in keywords
                if keyword in text_to_analyze
            )
            for dest_type, keywords in keywords.items()
        }
        
        max_score = max(scores.values())
        if max_score == 0:
            return 'otro'
            
        return max(
            scores.items(),
            key=lambda x: x[1]
        )[0]
