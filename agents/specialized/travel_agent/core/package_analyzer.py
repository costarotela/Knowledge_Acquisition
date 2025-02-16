"""
Analizador avanzado de paquetes turísticos.

Características:
1. Scoring de paquetes basado en múltiples factores
2. Detección de promociones y ofertas
3. Análisis de tendencias de precios
4. Recomendaciones personalizadas
5. Comparación de valor por dinero
"""

from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
import numpy as np
from dataclasses import asdict
import logging
from sklearn.preprocessing import MinMaxScaler
from .schemas import TravelPackage, CustomerProfile, PriceHistory

logger = logging.getLogger(__name__)

class PackageAnalyzer:
    """
    Analizador avanzado de paquetes turísticos con scoring
    y detección de oportunidades.
    """
    
    def __init__(
        self,
        price_weight: float = 0.3,
        value_weight: float = 0.25,
        quality_weight: float = 0.25,
        relevance_weight: float = 0.2
    ):
        self.weights = {
            'price': price_weight,
            'value': value_weight,
            'quality': quality_weight,
            'relevance': relevance_weight
        }
        self.scaler = MinMaxScaler()
        
    def analyze_packages(
        self,
        packages: List[TravelPackage],
        customer_profile: CustomerProfile,
        price_history: Optional[List[PriceHistory]] = None
    ) -> List[Dict]:
        """
        Analiza una lista de paquetes y retorna resultados detallados.
        
        Args:
            packages: Lista de paquetes a analizar
            customer_profile: Perfil del cliente
            price_history: Historial de precios opcional
            
        Returns:
            Lista de resultados de análisis por paquete
        """
        if not packages:
            return []
            
        # Preparar datos para análisis
        analysis_data = []
        for package in packages:
            analysis = self._analyze_single_package(
                package,
                customer_profile,
                price_history
            )
            analysis_data.append(analysis)
            
        # Normalizar scores
        normalized_scores = self._normalize_scores(analysis_data)
        
        # Calcular score final
        for analysis, norm_scores in zip(analysis_data, normalized_scores):
            analysis['scores'].update(norm_scores)
            analysis['final_score'] = self._calculate_final_score(
                norm_scores
            )
            
        # Ordenar por score final
        return sorted(
            analysis_data,
            key=lambda x: x['final_score'],
            reverse=True
        )
    
    def _analyze_single_package(
        self,
        package: TravelPackage,
        customer_profile: CustomerProfile,
        price_history: Optional[List[PriceHistory]]
    ) -> Dict:
        """Analiza un paquete individual."""
        # Calcular duración
        duration = (
            (package.end_date - package.start_date).days
            if package.end_date and package.start_date
            else 0
        )
        
        # Calcular precio por día
        price_per_day = (
            package.price / duration if duration > 0
            else package.price
        )
        
        # Analizar tendencia de precios
        price_trend = self._analyze_price_trend(
            package,
            price_history
        ) if price_history else None
        
        # Detectar promociones
        promotions = self._detect_promotions(package, price_history)
        
        # Calcular scores individuales
        scores = {
            'price': self._calculate_price_score(
                package,
                price_per_day,
                customer_profile
            ),
            'value': self._calculate_value_score(
                package,
                price_per_day,
                duration
            ),
            'quality': self._calculate_quality_score(package),
            'relevance': self._calculate_relevance_score(
                package,
                customer_profile
            )
        }
        
        return {
            'package_id': package.id,
            'scores': scores,
            'metrics': {
                'price_per_day': price_per_day,
                'duration': duration,
                'activities_count': len(package.activities or []),
                'accommodation_quality': (
                    package.accommodation.stars
                    if package.accommodation
                    else 0
                )
            },
            'analysis': {
                'price_trend': price_trend,
                'promotions': promotions,
                'recommendations': self._generate_recommendations(
                    package,
                    scores,
                    customer_profile
                )
            }
        }
    
    def _normalize_scores(
        self,
        analysis_data: List[Dict]
    ) -> List[Dict[str, float]]:
        """Normaliza los scores usando Min-Max scaling."""
        score_matrix = np.array([
            [
                analysis['scores'][key]
                for key in self.weights.keys()
            ]
            for analysis in analysis_data
        ])
        
        # Evitar división por cero si todos los scores son iguales
        if score_matrix.std(axis=0).sum() == 0:
            return [
                {key: 1.0 for key in self.weights.keys()}
                for _ in analysis_data
            ]
            
        normalized = self.scaler.fit_transform(score_matrix)
        
        return [
            {
                key: score
                for key, score in zip(self.weights.keys(), row)
            }
            for row in normalized
        ]
    
    def _calculate_final_score(self, scores: Dict[str, float]) -> float:
        """Calcula el score final ponderado."""
        return sum(
            scores[key] * weight
            for key, weight in self.weights.items()
        )
    
    def _calculate_price_score(
        self,
        package: TravelPackage,
        price_per_day: float,
        customer_profile: CustomerProfile
    ) -> float:
        """
        Calcula el score de precio.
        Mayor score = mejor precio (más bajo).
        """
        # Base score inversamente proporcional al precio
        base_score = 1.0 / (1.0 + np.log1p(price_per_day))
        
        # Ajustar según tipo de cliente
        if customer_profile.type == 'premium':
            # Clientes premium valoran menos el precio bajo
            base_score = (base_score + 1) / 2
        elif customer_profile.type == 'corporate':
            # Corporativos tienen presupuestos más altos
            base_score = (base_score + 0.8) / 2
            
        return base_score
    
    def _calculate_value_score(
        self,
        package: TravelPackage,
        price_per_day: float,
        duration: int
    ) -> float:
        """
        Calcula el score de valor por dinero.
        Considera actividades, alojamiento y duración.
        """
        # Contar beneficios
        benefits = 0
        
        # Actividades
        if package.activities:
            benefits += len(package.activities) * 0.5
            
        # Calidad de alojamiento
        if package.accommodation:
            benefits += package.accommodation.stars or 0
            
        # Duración óptima (7-14 días suele ser ideal)
        duration_score = 1.0 - abs(duration - 10) / 10
        duration_score = max(0.0, min(1.0, duration_score))
        
        # Valor = beneficios / precio
        value_score = benefits / (1.0 + np.log1p(price_per_day))
        
        return (value_score + duration_score) / 2
    
    def _calculate_quality_score(self, package: TravelPackage) -> float:
        """
        Calcula el score de calidad general del paquete.
        """
        scores = []
        
        # Calidad de alojamiento
        if package.accommodation:
            accommodation_score = (package.accommodation.stars or 0) / 5.0
            scores.append(accommodation_score)
            
        # Calidad de actividades
        if package.activities:
            activity_score = min(len(package.activities) / 5.0, 1.0)
            scores.append(activity_score)
            
        # Completitud de información
        info_score = 0.0
        required_fields = [
            'title', 'description', 'price',
            'start_date', 'end_date'
        ]
        for field in required_fields:
            if getattr(package, field, None):
                info_score += 1
        info_score /= len(required_fields)
        scores.append(info_score)
        
        return sum(scores) / len(scores) if scores else 0.0
    
    def _calculate_relevance_score(
        self,
        package: TravelPackage,
        customer_profile: CustomerProfile
    ) -> float:
        """
        Calcula qué tan relevante es el paquete para el cliente.
        """
        score = 0.0
        total_factors = 0
        
        # Relevancia por tipo de cliente
        if customer_profile.type == 'premium':
            if package.accommodation and package.accommodation.stars >= 4:
                score += 1
            total_factors += 1
                
        elif customer_profile.type == 'family':
            if package.activities:
                family_activities = sum(
                    1 for a in package.activities
                    if 'niños' in a.title.lower() or 'familia' in a.title.lower()
                )
                score += min(family_activities / 2, 1.0)
            total_factors += 1
                
        elif customer_profile.type == 'corporate':
            if package.accommodation and 'business' in package.accommodation.type.lower():
                score += 1
            total_factors += 1
        
        # Factores generales
        if package.start_date and package.end_date:
            duration = (package.end_date - package.start_date).days
            ideal_duration = {
                'premium': 10,
                'family': 7,
                'corporate': 5,
                'default': 7
            }.get(customer_profile.type, 7)
            
            duration_score = 1.0 - abs(duration - ideal_duration) / ideal_duration
            score += max(0.0, duration_score)
            total_factors += 1
            
        return score / total_factors if total_factors > 0 else 0.0
    
    def _analyze_price_trend(
        self,
        package: TravelPackage,
        price_history: List[PriceHistory]
    ) -> Dict:
        """
        Analiza la tendencia de precios del paquete.
        """
        if not price_history:
            return None
            
        # Filtrar historial para este paquete
        package_history = [
            ph for ph in price_history
            if ph.package_id == package.id
        ]
        
        if not package_history:
            return None
            
        # Ordenar por fecha
        package_history.sort(key=lambda x: x.timestamp)
        
        # Calcular cambios
        price_changes = [
            (ph.price - package_history[i-1].price) / package_history[i-1].price
            for i, ph in enumerate(package_history[1:], 1)
        ]
        
        # Analizar tendencia
        if price_changes:
            avg_change = sum(price_changes) / len(price_changes)
            recent_change = price_changes[-1] if price_changes else 0
            
            return {
                'trend': 'up' if avg_change > 0.01 else 'down' if avg_change < -0.01 else 'stable',
                'avg_change_percent': avg_change * 100,
                'recent_change_percent': recent_change * 100,
                'volatility': np.std(price_changes) * 100 if len(price_changes) > 1 else 0
            }
            
        return None
    
    def _detect_promotions(
        self,
        package: TravelPackage,
        price_history: Optional[List[PriceHistory]]
    ) -> List[Dict]:
        """
        Detecta promociones y ofertas especiales.
        """
        promotions = []
        
        # Analizar precio actual vs histórico
        if price_history:
            package_history = [
                ph for ph in price_history
                if ph.package_id == package.id
            ]
            
            if package_history:
                avg_price = sum(ph.price for ph in package_history) / len(package_history)
                if package.price < avg_price * 0.9:  # 10% menos que promedio
                    promotions.append({
                        'type': 'price_drop',
                        'description': 'Precio por debajo del promedio histórico',
                        'savings_percent': ((avg_price - package.price) / avg_price) * 100
                    })
                    
        # Detectar ofertas por duración
        if package.start_date and package.end_date:
            duration = (package.end_date - package.start_date).days
            price_per_day = package.price / duration
            
            if duration >= 7 and price_per_day < package.price / 7 * 0.9:
                promotions.append({
                    'type': 'long_stay',
                    'description': 'Descuento por estadía prolongada',
                    'duration_days': duration
                })
                
        return promotions
    
    def _generate_recommendations(
        self,
        package: TravelPackage,
        scores: Dict[str, float],
        customer_profile: CustomerProfile
    ) -> List[str]:
        """
        Genera recomendaciones personalizadas basadas en el análisis.
        """
        recommendations = []
        
        # Recomendaciones por tipo de cliente
        if customer_profile.type == 'premium':
            if package.accommodation and package.accommodation.stars < 4:
                recommendations.append(
                    "Considerar hoteles de categoría superior para este cliente premium"
                )
        elif customer_profile.type == 'family':
            if not package.activities or not any(
                'niños' in a.title.lower() or 'familia' in a.title.lower()
                for a in package.activities
            ):
                recommendations.append(
                    "Sugerir actividades adicionales orientadas a familias"
                )
                
        # Recomendaciones por scores
        if scores['value'] < 0.4:
            recommendations.append(
                "El valor por dinero es bajo. Considerar agregar beneficios adicionales"
            )
            
        if scores['quality'] < 0.3:
            recommendations.append(
                "La calidad general del paquete podría mejorarse"
            )
            
        return recommendations
