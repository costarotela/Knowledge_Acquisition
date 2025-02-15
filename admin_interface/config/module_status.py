"""
Configuration for admin interface modules status and feature flags.
"""

from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel
from datetime import datetime

class ModuleStatus(str, Enum):
    """Estados posibles de un módulo administrativo."""
    
    PLANNED = "planned"          # Planificado pero no implementado
    IN_DEVELOPMENT = "dev"       # En desarrollo
    TESTING = "testing"          # En fase de pruebas
    BETA = "beta"               # Funcional pero en beta
    PRODUCTION = "production"    # Completamente funcional
    DEPRECATED = "deprecated"    # Obsoleto/Deprecado

class ModuleDependency(BaseModel):
    """Dependencia de un módulo."""
    
    module_id: str
    min_status: ModuleStatus
    description: str

class ModuleConfig(BaseModel):
    """Configuración de un módulo administrativo."""
    
    id: str
    name: str
    description: str
    status: ModuleStatus
    visible: bool = True  # Si es False, no se muestra en la UI
    enabled: bool = False  # Si es False, aparece pero no se puede usar
    dependencies: List[ModuleDependency] = []
    implementation_date: Optional[datetime] = None
    test_coverage: float = 0.0
    documentation_url: Optional[str] = None
    maintainers: List[str] = []
    tags: List[str] = []

# Configuración de módulos administrativos
ADMIN_MODULES: Dict[str, ModuleConfig] = {
    "knowledge_explorer": ModuleConfig(
        id="knowledge_explorer",
        name="Knowledge Explorer",
        description="Explorador visual de la base de conocimiento con visualización de relaciones",
        status=ModuleStatus.BETA,
        enabled=True,
        test_coverage=0.62,
        implementation_date=datetime(2025, 2, 15),
        tags=["visualization", "knowledge", "graph"],
        maintainers=["admin_team"]
    ),
    
    "performance_monitor": ModuleConfig(
        id="performance_monitor",
        name="Performance Monitor",
        description="Monitoreo en tiempo real de agentes y sistema",
        status=ModuleStatus.PLANNED,
        enabled=False,
        dependencies=[
            ModuleDependency(
                module_id="agent_metrics",
                min_status=ModuleStatus.BETA,
                description="Requiere métricas de agentes"
            )
        ],
        tags=["monitoring", "metrics", "performance"]
    ),
    
    "validation_tools": ModuleConfig(
        id="validation_tools",
        name="Validation Tools",
        description="Herramientas para validación de datos y resultados",
        status=ModuleStatus.TESTING,
        enabled=True,
        test_coverage=0.75,
        implementation_date=datetime(2025, 2, 15),
        tags=["validation", "testing", "quality"]
    ),
    
    "agent_manager": ModuleConfig(
        id="agent_manager",
        name="Agent Manager",
        description="Gestión y configuración de agentes especializados",
        status=ModuleStatus.PLANNED,
        enabled=False,
        dependencies=[
            ModuleDependency(
                module_id="agent_orchestrator",
                min_status=ModuleStatus.BETA,
                description="Requiere orquestador de agentes"
            )
        ],
        tags=["agents", "configuration", "management"]
    )
}

def get_module_config(module_id: str) -> Optional[ModuleConfig]:
    """Obtener configuración de un módulo."""
    return ADMIN_MODULES.get(module_id)

def is_module_available(module_id: str) -> bool:
    """Verificar si un módulo está disponible para uso."""
    config = get_module_config(module_id)
    if not config:
        return False
    
    # Verificar estado y dependencias
    if not config.enabled:
        return False
    
    # Verificar dependencias
    for dep in config.dependencies:
        dep_config = get_module_config(dep.module_id)
        if not dep_config or dep_config.status.value < dep.min_status.value:
            return False
    
    return True
