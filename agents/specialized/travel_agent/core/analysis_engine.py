"""
Motor de análisis y procesamiento de información turística.
"""

from typing import List, Dict, Optional, Any
import numpy as np
from datetime import datetime
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from typing import Dict, List, Optional, Tuple
import pandas as pd
import logging
from dataclasses import dataclass
from .schemas import TravelPackage, SalesQuery
from .browser_manager import BrowserManager

@dataclass
class AnalysisResult:
    """Resultado del análisis de paquetes."""
    packages: List[TravelPackage]
    metrics: Dict[str, float]
    segments: Dict[str, List[TravelPackage]]
    recommendations: List[TravelPackage]
    insights: Dict[str, str]
    price_trends: Dict[str, List[float]]

class AnalysisEngine:
    """Motor de análisis de paquetes turísticos."""
    
    def __init__(
        self,
        browser_manager: BrowserManager,
        min_samples: int = 5,
        cache_ttl: int = 3600
    ):
        self.browser = browser_manager
        self.min_samples = min_samples
        self.cache_ttl = cache_ttl
        self.logger = logging.getLogger(__name__)
        
    async def analyze_packages(
        self,
        query: SalesQuery,
        packages: List[TravelPackage]
    ) -> AnalysisResult:
        """
        Analizar paquetes turísticos.
        
        Args:
            query: Consulta de venta
            packages: Lista de paquetes
            
        Returns:
            Resultado del análisis
        """
        if len(packages) < self.min_samples:
            self.logger.warning(
                f"Muestra insuficiente: {len(packages)} paquetes"
            )
            return self._create_basic_analysis(packages)
            
        try:
            # Análisis básico
            metrics = self._calculate_metrics(packages)
            
            # Segmentación
            segments = self._segment_packages(packages)
            
            # Recomendaciones
            recommendations = self._generate_recommendations(
                query, packages, segments
            )
            
            # Insights
            insights = self._generate_insights(
                query, packages, segments, metrics
            )
            
            # Análisis de precios
            price_trends = await self._analyze_price_trends(packages)
            
            return AnalysisResult(
                packages=packages,
                metrics=metrics,
                segments=segments,
                recommendations=recommendations,
                insights=insights,
                price_trends=price_trends
            )
            
        except Exception as e:
            self.logger.error(f"Error en análisis: {str(e)}")
            return self._create_basic_analysis(packages)
            
    def _calculate_metrics(
        self,
        packages: List[TravelPackage]
    ) -> Dict[str, float]:
        """Calcular métricas básicas."""
        prices = [p.price for p in packages]
        durations = [p.duration for p in packages]
        
        return {
            "price_mean": np.mean(prices),
            "price_std": np.std(prices),
            "price_min": min(prices),
            "price_max": max(prices),
            "duration_mean": np.mean(durations),
            "duration_std": np.std(durations),
            "price_per_night_mean": np.mean([
                p.price / p.duration for p in packages
            ]),
            "sample_size": len(packages)
        }
        
    def _segment_packages(
        self,
        packages: List[TravelPackage]
    ) -> Dict[str, List[TravelPackage]]:
        """Segmentar paquetes por características."""
        # Preparar datos
        X = np.array([
            [p.price, p.duration, len(p.activities)]
            for p in packages
        ])
        
        # Normalizar
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        
        # Encontrar número óptimo de clusters
        best_k = 2
        best_score = -1
        
        for k in range(2, min(6, len(packages))):
            kmeans = KMeans(n_clusters=k, random_state=42)
            labels = kmeans.fit_predict(X_scaled)
            score = silhouette_score(X_scaled, labels)
            
            if score > best_score:
                best_score = score
                best_k = k
                
        # Segmentar
        kmeans = KMeans(n_clusters=best_k, random_state=42)
        labels = kmeans.fit_predict(X_scaled)
        
        # Caracterizar segmentos
        segments = {}
        centers = scaler.inverse_transform(kmeans.cluster_centers_)
        
        for i in range(best_k):
            segment_packages = [
                p for j, p in enumerate(packages)
                if labels[j] == i
            ]
            
            if len(segment_packages) == 0:
                continue
                
            # Determinar tipo de segmento
            center = centers[i]
            price_level = center[0]
            duration_level = center[1]
            activity_level = center[2]
            
            segment_type = self._classify_segment(
                price_level,
                duration_level,
                activity_level,
                [p.price for p in packages]
            )
            
            segments[segment_type] = segment_packages
            
        return segments
        
    def _classify_segment(
        self,
        price: float,
        duration: float,
        activities: float,
        all_prices: List[float]
    ) -> str:
        """Clasificar segmento según características."""
        price_percentile = np.percentile(all_prices, [33, 66])
        
        if price <= price_percentile[0]:
            price_level = "económico"
        elif price <= price_percentile[1]:
            price_level = "estándar"
        else:
            price_level = "premium"
            
        if activities >= 5:
            return f"{price_level}_aventura"
        elif duration >= 10:
            return f"{price_level}_extendido"
        else:
            return price_level
            
    def _generate_recommendations(
        self,
        query: SalesQuery,
        packages: List[TravelPackage],
        segments: Dict[str, List[TravelPackage]]
    ) -> List[TravelPackage]:
        """Generar recomendaciones personalizadas."""
        recommendations = []
        
        # Filtrar por presupuesto
        max_budget = query.preferences.get("max_budget")
        if max_budget:
            packages = [
                p for p in packages
                if p.price <= max_budget
            ]
            
        # Filtrar por duración mínima
        min_nights = query.preferences.get("min_nights")
        if min_nights:
            packages = [
                p for p in packages
                if p.duration >= min_nights
            ]
            
        # Ordenar por relevancia
        scored_packages = []
        desired_activities = set(
            query.preferences.get("activities", [])
        )
        
        for package in packages:
            package_activities = set(package.activities)
            activity_score = len(
                desired_activities & package_activities
            )
            value_score = package.rating / package.price
            
            total_score = (
                0.6 * activity_score +
                0.4 * value_score
            )
            
            scored_packages.append((package, total_score))
            
        # Seleccionar mejores opciones
        scored_packages.sort(key=lambda x: x[1], reverse=True)
        recommendations = [p[0] for p in scored_packages[:5]]
        
        return recommendations
        
    def _generate_insights(
        self,
        query: SalesQuery,
        packages: List[TravelPackage],
        segments: Dict[str, List[TravelPackage]],
        metrics: Dict[str, float]
    ) -> Dict[str, str]:
        """Generar insights sobre los paquetes."""
        insights = {}
        
        # Análisis de valor
        price_per_night = metrics["price_per_night_mean"]
        insights["valor"] = (
            f"El precio promedio por noche es ${price_per_night:.2f}. "
        )
        
        if "premium" in segments:
            premium_value = np.mean([
                p.rating / p.price
                for p in segments["premium"]
            ])
            insights["valor"] += (
                f"Los paquetes premium ofrecen un índice "
                f"de valor de {premium_value:.2f}."
            )
            
        # Análisis de temporada
        current_month = datetime.now().month
        high_season = 6 <= current_month <= 8
        insights["temporada"] = (
            "Actualmente en temporada " +
            ("alta" if high_season else "baja") +
            ". "
        )
        
        # Análisis de actividades
        all_activities = set()
        for p in packages:
            all_activities.update(p.activities)
            
        popular_activities = sorted(
            all_activities,
            key=lambda a: sum(
                1 for p in packages if a in p.activities
            ),
            reverse=True
        )[:3]
        
        insights["actividades"] = (
            f"Las actividades más populares son: "
            f"{', '.join(popular_activities)}."
        )
        
        return insights
        
    async def _analyze_price_trends(
        self,
        packages: List[TravelPackage]
    ) -> Dict[str, List[float]]:
        """Analizar tendencias de precios."""
        trends = {}
        
        for package in packages:
            # Obtener historial de precios
            try:
                price_history = await self.browser.extract_list_data(
                    url=f"{package.url}/history",
                    list_selector=".price-history",
                    item_selectors={
                        "date": ".history-date",
                        "price": ".history-price"
                    }
                )
                
                if price_history:
                    prices = [
                        float(item["price"].replace("$", ""))
                        for item in price_history
                    ]
                    trends[package.id] = prices
                    
            except Exception as e:
                self.logger.warning(
                    f"Error obteniendo historial: {str(e)}"
                )
                continue
                
        return trends
        
    def _create_basic_analysis(
        self,
        packages: List[TravelPackage]
    ) -> AnalysisResult:
        """Crear análisis básico con datos limitados."""
        return AnalysisResult(
            packages=packages,
            metrics=self._calculate_metrics(packages),
            segments={"todos": packages},
            recommendations=packages[:3],
            insights={
                "general": (
                    f"Análisis limitado basado en "
                    f"{len(packages)} paquetes."
                )
            },
            price_trends={}
        )
