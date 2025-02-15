"""
Core implementation of the Travel Agent.
"""

from typing import List, Dict, Optional, Callable
from datetime import datetime
import asyncio
import logging
import os
from pathlib import Path

try:
    from ..core_system.knowledge_base import KnowledgeBase
except ImportError:
    # Para pruebas, usamos el mock
    from ..tests.mocks.knowledge_base import MockKnowledgeBase as KnowledgeBase

from .provider_manager import ProviderManager
from .browser_manager import BrowserManager
from .price_monitor import PriceMonitor
from .schemas import TravelPackage, Accommodation, Activity

class TravelAgent:
    """
    Specialized agent for processing travel and tourism information.
    
    This agent can:
    1. Search and extract information from tourism providers
    2. Compare and analyze travel packages
    3. Generate customized budgets
    4. Track price changes and send alerts
    """
    
    def __init__(
        self,
        knowledge_base: KnowledgeBase,
        browser_config: Optional[Dict] = None,
        provider_credentials: Optional[Dict[str, Dict]] = None,
        price_monitor_config: Optional[Dict] = None,
        llm_model: str = "gpt-4"
    ):
        self.knowledge_base = knowledge_base
        self.browser_config = browser_config or {}
        self.browser_manager = BrowserManager(llm_model=llm_model)
        
        # Configurar gestor de proveedores
        config_dir = os.path.join(
            Path(__file__).parent.parent,
            "config"
        )
        self.provider_manager = ProviderManager(
            browser_manager=self.browser_manager,
            config_dir=config_dir,
            credentials=provider_credentials
        )
        
        # Configurar monitor de precios
        self.price_monitor = PriceMonitor(
            storage_dir=price_monitor_config.get("storage_dir") if price_monitor_config else None,
            check_interval=price_monitor_config.get("check_interval", 3600) if price_monitor_config else 3600
        )
        
        self.logger = logging.getLogger(__name__)
        
    async def start_monitoring(self):
        """Iniciar monitoreo de precios."""
        await self.price_monitor.start_monitoring()
        
    def stop_monitoring(self):
        """Detener monitoreo de precios."""
        self.price_monitor.stop_monitoring()
        
    async def create_price_alert(
        self,
        package: TravelPackage,
        conditions: Dict,
        callback: Callable
    ):
        """
        Crear alerta de precio.
        
        Args:
            package: Paquete a monitorear
            conditions: Condiciones para la alerta
            callback: Función a llamar cuando se cumpla la condición
        """
        return self.price_monitor.add_alert(package, conditions, callback)
        
    def get_price_history(self, package_id: str) -> List[Dict]:
        """Obtener historial de precios de un paquete."""
        return self.price_monitor.get_price_history(package_id)
        
    def analyze_price_trends(self, package_id: str) -> Dict:
        """Analizar tendencias de precios de un paquete."""
        return self.price_monitor.analyze_trends(package_id)

    async def search_packages(
        self,
        destination: str,
        dates: Optional[Dict] = None,
        preferences: Optional[Dict] = None
    ) -> List[TravelPackage]:
        """
        Buscar paquetes en todos los proveedores disponibles.
        
        Args:
            destination: Destino del viaje
            dates: Fechas de salida y regreso
            preferences: Preferencias específicas
            
        Returns:
            Lista combinada de paquetes de todos los proveedores
        """
        all_packages = []
        
        # Buscar en paralelo en todos los proveedores
        search_tasks = [
            self.provider_manager.search_packages(
                provider_name,
                destination,
                dates,
                preferences
            )
            for provider_name in self.provider_manager.providers.keys()
        ]
        
        results = await asyncio.gather(*search_tasks, return_exceptions=True)
        
        for provider_packages in results:
            if isinstance(provider_packages, Exception):
                self.logger.error(f"Error searching packages: {str(provider_packages)}")
                continue
            all_packages.extend(provider_packages)
        
        return all_packages
    
    def compare_packages(self, packages: List[TravelPackage]) -> Dict:
        """
        Comparar paquetes y generar análisis.
        
        Args:
            packages: Lista de paquetes a comparar
            
        Returns:
            Diccionario con análisis comparativo
        """
        if not packages:
            return {}
            
        analysis = {
            "price_range": {
                "min": min(p.price for p in packages),
                "max": max(p.price for p in packages),
                "avg": sum(p.price for p in packages) / len(packages)
            },
            "duration_range": {
                "min": min(p.duration for p in packages),
                "max": max(p.duration for p in packages)
            },
            "providers": list(set(p.provider for p in packages)),
            "best_value": None,
            "luxury_option": None,
            "budget_option": None
        }
        
        # Encontrar mejores opciones
        sorted_by_price = sorted(packages, key=lambda p: p.price)
        analysis["budget_option"] = sorted_by_price[0]
        analysis["luxury_option"] = sorted_by_price[-1]
        
        # Calcular mejor valor (relación precio/duración/servicios)
        def calculate_value_score(package):
            included_services = len(package.included_services)
            price_per_night = package.price / package.duration if package.duration else float('inf')
            return included_services / price_per_night if price_per_night else 0
            
        analysis["best_value"] = max(packages, key=calculate_value_score)
        
        return analysis
    
    def generate_budget(
        self,
        packages: List[TravelPackage],
        preferences: Dict
    ) -> Dict:
        """
        Generar presupuesto personalizado y detallado.
        
        Args:
            packages: Lista de paquetes disponibles
            preferences: Preferencias del cliente
            
        Returns:
            Presupuesto detallado con opciones y análisis
        """
        analysis = self.compare_packages(packages)
        max_budget = preferences.get("max_budget", float('inf'))
        min_nights = preferences.get("min_nights", 0)
        
        # Filtrar paquetes según preferencias
        suitable_packages = [
            p for p in packages
            if p.price <= max_budget and p.duration >= min_nights
        ]
        
        if not suitable_packages:
            return {
                "status": "no_matches",
                "message": "No se encontraron paquetes que cumplan con los requisitos"
            }
        
        # Analizar tendencias de precios
        price_trends = {}
        for package in suitable_packages[:3]:  # Solo los 3 mejores
            price_trends[package.id] = self.analyze_price_trends(package.id)
        
        # Organizar opciones
        budget = {
            "status": "success",
            "options": {
                "recommended": analysis["best_value"],
                "economic": analysis["budget_option"],
                "premium": analysis["luxury_option"]
            },
            "price_analysis": analysis["price_range"],
            "available_dates": list(set(
                p.dates["departure"]
                for p in suitable_packages
                if p.dates and "departure" in p.dates
            )),
            "price_trends": price_trends,
            "recommendations": self._generate_recommendations(
                suitable_packages,
                price_trends
            ),
            "observations": [
                "Los precios pueden variar según disponibilidad",
                "Se recomienda reservar con anticipación",
                "Consultar políticas de cancelación de cada proveedor"
            ]
        }
        
        return budget
        
    def _generate_recommendations(
        self,
        packages: List[TravelPackage],
        price_trends: Dict
    ) -> List[Dict]:
        """Generar recomendaciones basadas en análisis de precios."""
        recommendations = []
        
        for package in packages:
            if package.id in price_trends:
                trend = price_trends[package.id]
                
                if trend["trend"] == "strong_decrease":
                    recommendations.append({
                        "type": "price_opportunity",
                        "package_id": package.id,
                        "message": "Precios están bajando significativamente"
                    })
                elif trend["best_time_to_buy"]["suggestion"] == "buy":
                    recommendations.append({
                        "type": "timing",
                        "package_id": package.id,
                        "message": f"Buen momento para comprar: {trend['best_time_to_buy']['reason']}"
                    })
                    
        return recommendations
