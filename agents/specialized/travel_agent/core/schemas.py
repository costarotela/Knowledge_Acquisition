"""
Modelos de datos para el agente de viajes.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
from decimal import Decimal

@dataclass
class Accommodation:
    """Información de alojamiento."""
    name: str
    type: str
    rating: float
    amenities: List[str] = field(default_factory=list)
    room_types: List[str] = field(default_factory=list)
    location: Dict[str, float] = field(default_factory=dict)
    images: List[str] = field(default_factory=list)

@dataclass
class Activity:
    """Actividad turística."""
    name: str
    description: str
    duration: Optional[int] = None
    difficulty: Optional[str] = None
    included: bool = True
    price: Optional[Decimal] = None

@dataclass
class TravelPackage:
    """Paquete turístico completo."""
    id: str
    title: str
    description: str
    destination: str
    price: Decimal
    currency: str
    duration: int
    start_date: datetime
    end_date: datetime
    provider: str
    url: str
    accommodation: Accommodation
    activities: List[str] = field(default_factory=list)
    included_services: List[str] = field(default_factory=list)
    rating: float = 0.0
    reviews_count: int = 0
    availability: int = 0
    cancellation_policy: Optional[str] = None
    price_history: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class SearchCriteria:
    """Criterios específicos de búsqueda."""
    accommodation_type: Optional[str] = None
    meal_plan: Optional[str] = None
    transportation: Optional[str] = None
    min_rating: Optional[float] = None
    max_distance: Optional[float] = None
    amenities: List[str] = field(default_factory=list)

@dataclass
class SalesQuery:
    """Consulta de venta."""
    client_name: str
    destination: str
    dates: Dict[str, str]
    preferences: Dict[str, Any] = field(default_factory=dict)
    search_criteria: Optional[SearchCriteria] = None
    template: Optional[str] = None
    priority: str = "normal"
    notes: Optional[str] = None

@dataclass
class Budget:
    """Presupuesto generado."""
    client_name: str
    destination: str
    dates: Dict[str, str]
    recommended_package: TravelPackage
    alternative_packages: List[TravelPackage]
    price_analysis: Dict[str, float]
    value_insights: str
    seasonal_info: str
    is_refined: bool
    generated_at: datetime
    template: Dict[str, Any]
    status: str = "success"
    message: Optional[str] = None
    formatted_sections: List[Dict] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class PriceHistory:
    """Historial de precios."""
    package_id: str
    provider: str
    prices: List[Dict[str, Any]]
    last_updated: datetime
    trend: Optional[str] = None
    prediction: Optional[Dict[str, Any]] = None

@dataclass
class SessionState:
    """Estado de una sesión de venta."""
    session_id: str
    query: SalesQuery
    current_analysis: Dict[str, Any]
    current_budget: Budget
    interaction_count: int
    start_time: datetime
    last_update: datetime
    feedback_history: List[Dict[str, Any]] = field(default_factory=list)
    refinements: List[Dict[str, Any]] = field(default_factory=list)

@dataclass
class SalesReport:
    """Reporte final de una interacción de venta."""
    query: SalesQuery
    final_budget: Budget
    interaction_count: int
    end_reason: str
    insights: Dict[str, str]
    metrics: Dict[str, float]
    duration: Optional[int] = None
    conversion: bool = False
    feedback_summary: Optional[Dict[str, Any]] = None
    recommendations: List[str] = field(default_factory=list)

@dataclass
class ProviderConfig:
    """Configuración de proveedor."""
    name: str
    type: str
    base_url: str
    requires_auth: bool
    selectors: Dict[str, str]
    data_patterns: Dict[str, str]
    extraction: Dict[str, Any]
    auth_config: Optional[Dict[str, str]] = None
    rate_limits: Optional[Dict[str, int]] = None
    cache_ttl: int = 3600
    timeout: int = 30
    retry_config: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ExtractionResult:
    """Resultado de extracción de datos."""
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    cache_info: Optional[Dict[str, Any]] = None
    duration: Optional[float] = None

@dataclass
class AnalysisResult:
    """Resultado del análisis de datos."""
    success: bool
    data: Dict[str, Any]
    insights: List[str] = field(default_factory=list)
    scores: Dict[str, float] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    duration: Optional[float] = None
