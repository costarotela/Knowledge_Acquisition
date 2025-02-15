"""
Sistema de monitoreo y alertas de precios.
"""

from typing import List, Dict, Optional, Callable
from datetime import datetime, timedelta
import asyncio
import json
import logging
from pathlib import Path
from .schemas import TravelPackage

class PriceAlert:
    """Alerta de cambio de precio."""
    
    def __init__(
        self,
        package_id: str,
        destination: str,
        initial_price: float,
        target_price: float,
        alert_type: str,  # "decrease", "increase", "threshold"
        callback: Callable,
        expiration: Optional[datetime] = None
    ):
        self.package_id = package_id
        self.destination = destination
        self.initial_price = initial_price
        self.target_price = target_price
        self.alert_type = alert_type
        self.callback = callback
        self.expiration = expiration or (
            datetime.now() + timedelta(days=30)
        )
        self.triggered = False
        self.price_history = [(datetime.now(), initial_price)]

class PriceMonitor:
    """
    Monitor de precios que:
    1. Rastrea cambios de precios
    2. Genera alertas según condiciones
    3. Analiza tendencias
    4. Sugiere mejores momentos para comprar
    """
    
    def __init__(
        self,
        storage_dir: Optional[str] = None,
        check_interval: int = 3600  # 1 hora por defecto
    ):
        self.alerts: List[PriceAlert] = []
        self.storage_dir = Path(storage_dir or "data/price_history")
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.check_interval = check_interval
        self.logger = logging.getLogger(__name__)
        self._monitoring = False
        
    async def start_monitoring(self):
        """Iniciar monitoreo de precios."""
        self._monitoring = True
        while self._monitoring:
            await self._check_alerts()
            await asyncio.sleep(self.check_interval)
    
    def stop_monitoring(self):
        """Detener monitoreo."""
        self._monitoring = False
    
    def add_alert(
        self,
        package: TravelPackage,
        conditions: Dict,
        callback: Callable
    ) -> PriceAlert:
        """
        Agregar nueva alerta.
        
        Args:
            package: Paquete a monitorear
            conditions: Condiciones para la alerta
            callback: Función a llamar cuando se cumpla la condición
        """
        alert = PriceAlert(
            package_id=package.id,
            destination=package.destination,
            initial_price=package.price,
            target_price=conditions.get("target_price", package.price),
            alert_type=conditions.get("type", "decrease"),
            callback=callback,
            expiration=conditions.get("expiration")
        )
        
        self.alerts.append(alert)
        self._save_alert(alert)
        return alert
    
    def remove_alert(self, alert_id: str):
        """Eliminar alerta por ID."""
        self.alerts = [a for a in self.alerts if a.package_id != alert_id]
        
    async def update_price(
        self,
        package_id: str,
        new_price: float
    ):
        """
        Actualizar precio y verificar alertas.
        
        Args:
            package_id: ID del paquete
            new_price: Nuevo precio
        """
        for alert in self.alerts:
            if alert.package_id == package_id:
                alert.price_history.append((datetime.now(), new_price))
                await self._check_alert_conditions(alert, new_price)
                
    def get_price_history(
        self,
        package_id: str
    ) -> List[Dict]:
        """
        Obtener historial de precios.
        
        Args:
            package_id: ID del paquete
            
        Returns:
            Lista de precios con fechas
        """
        for alert in self.alerts:
            if alert.package_id == package_id:
                return [
                    {
                        "date": date.isoformat(),
                        "price": price
                    }
                    for date, price in alert.price_history
                ]
        return []
    
    def analyze_trends(
        self,
        package_id: str
    ) -> Dict:
        """
        Analizar tendencias de precios.
        
        Args:
            package_id: ID del paquete
            
        Returns:
            Análisis de tendencias
        """
        history = self.get_price_history(package_id)
        if not history:
            return {}
            
        prices = [h["price"] for h in history]
        dates = [datetime.fromisoformat(h["date"]) for h in history]
        
        analysis = {
            "current_price": prices[-1],
            "initial_price": prices[0],
            "min_price": min(prices),
            "max_price": max(prices),
            "avg_price": sum(prices) / len(prices),
            "price_change": prices[-1] - prices[0],
            "price_change_percent": (
                (prices[-1] - prices[0]) / prices[0] * 100
                if prices[0] != 0 else 0
            ),
            "trend": self._calculate_trend(prices),
            "best_time_to_buy": self._suggest_buy_time(prices, dates)
        }
        
        return analysis
    
    def _calculate_trend(self, prices: List[float]) -> str:
        """Calcular tendencia de precios."""
        if len(prices) < 2:
            return "stable"
            
        # Calcular cambios porcentuales
        changes = [
            (b - a) / a * 100
            for a, b in zip(prices[:-1], prices[1:])
        ]
        
        avg_change = sum(changes) / len(changes)
        
        if avg_change > 5:
            return "strong_increase"
        elif avg_change > 2:
            return "moderate_increase"
        elif avg_change < -5:
            return "strong_decrease"
        elif avg_change < -2:
            return "moderate_decrease"
        else:
            return "stable"
    
    def _suggest_buy_time(
        self,
        prices: List[float],
        dates: List[datetime]
    ) -> Dict:
        """Sugerir mejor momento para comprar."""
        if len(prices) < 7:  # Necesitamos al menos una semana de datos
            return {
                "confidence": "low",
                "suggestion": "need_more_data"
            }
            
        trend = self._calculate_trend(prices)
        current_price = prices[-1]
        min_price = min(prices)
        
        if trend in ["strong_decrease", "moderate_decrease"]:
            return {
                "confidence": "high",
                "suggestion": "wait",
                "reason": "Precios están bajando"
            }
        elif trend == "stable" and current_price <= min_price * 1.1:
            return {
                "confidence": "medium",
                "suggestion": "buy",
                "reason": "Precio estable y cercano al mínimo"
            }
        elif trend in ["strong_increase", "moderate_increase"]:
            return {
                "confidence": "high",
                "suggestion": "buy",
                "reason": "Precios están subiendo"
            }
        
        return {
            "confidence": "low",
            "suggestion": "monitor",
            "reason": "Patrón no claro"
        }
    
    async def _check_alerts(self):
        """Verificar todas las alertas activas."""
        now = datetime.now()
        expired_alerts = []
        
        for alert in self.alerts:
            if now > alert.expiration:
                expired_alerts.append(alert)
                continue
                
            latest_price = alert.price_history[-1][1]
            await self._check_alert_conditions(alert, latest_price)
            
        # Limpiar alertas expiradas
        for alert in expired_alerts:
            self.remove_alert(alert.package_id)
    
    async def _check_alert_conditions(
        self,
        alert: PriceAlert,
        current_price: float
    ):
        """Verificar condiciones de una alerta."""
        if alert.triggered:
            return
            
        should_trigger = False
        
        if alert.alert_type == "decrease":
            should_trigger = current_price < alert.target_price
        elif alert.alert_type == "increase":
            should_trigger = current_price > alert.target_price
        elif alert.alert_type == "threshold":
            price_change = abs(current_price - alert.initial_price)
            threshold = abs(alert.target_price - alert.initial_price)
            should_trigger = price_change >= threshold
            
        if should_trigger:
            alert.triggered = True
            try:
                await alert.callback(alert, current_price)
            except Exception as e:
                self.logger.error(f"Error en callback de alerta: {str(e)}")
    
    def _save_alert(self, alert: PriceAlert):
        """Guardar alerta en almacenamiento persistente."""
        alert_data = {
            "package_id": alert.package_id,
            "destination": alert.destination,
            "initial_price": alert.initial_price,
            "target_price": alert.target_price,
            "alert_type": alert.alert_type,
            "expiration": alert.expiration.isoformat(),
            "price_history": [
                {
                    "date": date.isoformat(),
                    "price": price
                }
                for date, price in alert.price_history
            ]
        }
        
        file_path = self.storage_dir / f"{alert.package_id}.json"
        with open(file_path, "w") as f:
            json.dump(alert_data, f, indent=2)
