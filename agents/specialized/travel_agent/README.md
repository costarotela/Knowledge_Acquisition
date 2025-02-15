# AI Travel Agent

Sistema inteligente para búsqueda, análisis y generación de presupuestos de viajes.

## Características Principales

### 1. Extracción de Datos
- Soporte para múltiples proveedores de viajes
- Extracción de listas con paginación y scroll infinito
- Monitoreo de cambios en tiempo real
- Rate limiting y caché configurable
- Extracción de tablas y datos estructurados
- Manejo robusto de errores y reintentos

### 2. Análisis Avanzado
- Segmentación de paquetes mediante clustering
- Análisis de tendencias de precios
- Cálculo de métricas estadísticas
- Generación de insights personalizados
- Recomendaciones basadas en preferencias
- Análisis de sentimiento de reseñas

### 3. Gestión de Ventas
- Manejo de sesiones de venta
- Refinamiento iterativo de búsquedas
- Generación de presupuestos personalizados
- Seguimiento de interacciones
- Reportes detallados de ventas
- Historial de búsquedas y preferencias

## Requisitos

- Python 3.11 o superior
- Node.js 18+ (para Playwright)
- Conda (recomendado para gestión de entornos)

### Dependencias Principales
- browser-use >= 0.1.37
- playwright >= 1.40
- pydantic >= 2.10.4
- pytest >= 7.4.3
- pytest-asyncio >= 0.23.2
- pytest-cov >= 4.1.0
- langchain-openai >= 0.0.3

## Instalación

1. Crear entorno conda:
```bash
conda create -n knowledge-acquisition python=3.11
conda activate knowledge-acquisition
```

2. Instalar dependencias:
```bash
pip install -r requirements.txt
playwright install
```

3. Verificar la instalación:
```bash
pytest tests/
```

## Estructura del Proyecto

```
travel_agent/
├── core/                   # Componentes principales
│   ├── analysis_engine.py  # Motor de análisis
│   ├── browser_manager.py  # Gestión de navegación
│   ├── sales_assistant.py  # Asistente de ventas
│   └── schemas.py         # Modelos de datos
├── tests/                 # Tests unitarios y de integración
│   ├── test_analysis_engine.py
│   ├── test_browser_manager.py
│   └── test_sales_assistant.py
├── config/               # Configuraciones
│   ├── providers/       # Configuración de proveedores
│   └── settings.py      # Configuración general
├── scripts/             # Scripts de utilidad
│   └── update.sh       # Script de actualización
├── cache/              # Caché de datos
└── knowledge/         # Base de conocimiento
```

## Uso

### 1. Configuración de Proveedores

```python
from core.schemas import ProviderConfig

config = ProviderConfig(
    name="example_provider",
    type="travel",
    base_url="https://example.com",
    requires_auth=False,
    selectors={
        "package_list": ".package-item",
        "price": ".price",
        "title": ".title"
    },
    data_patterns={
        "price": r"\$(\d+)",
        "date": r"(\d{4}-\d{2}-\d{2})"
    },
    extraction={
        "list_mode": "pagination",
        "max_items": 100,
        "delay": 1
    }
)
```

### 2. Extracción de Datos

```python
from core.browser_manager import BrowserManager

# Inicializar el gestor con configuración personalizada
browser = BrowserManager(
    llm_model="gpt-4",  # Modelo de lenguaje para extracción inteligente
    cache_dir="data/cache",  # Directorio de caché
    cache_ttl=3600,  # Tiempo de vida del caché en segundos
    headless=True  # Modo sin interfaz gráfica
)

# Extraer datos de una tabla
table_data = await browser.extract_table_data(
    url="https://example.com/packages",
    table_selector="table.packages",
    column_map={
        "title": "td.package-title",
        "price": "td.package-price",
        "duration": "td.package-duration"
    }
)

# Extraer datos de una lista
list_data = await browser.extract_list_data(
    url="https://example.com/offers",
    list_selector=".offer-list",
    item_selectors={
        "title": ".offer-title",
        "description": ".offer-description",
        "price": ".offer-price"
    }
)

# Interactuar con la página
await browser.interact_with_page(
    url="https://example.com/search",
    interactions=[
        {
            "action": "type",
            "selector": "#destination",
            "target": "Cancun"
        },
        {
            "action": "click",
            "selector": "#search-btn"
        },
        {
            "action": "wait",
            "target": "2"  # Esperar 2 segundos
        }
    ]
)

# Extraer contenido dinámico con validación de patrones
result = await browser.extract_dynamic_content(
    url="https://example.com/details",
    selectors={
        "price": ".price-tag",
        "dates": ".available-dates"
    },
    data_patterns={
        "price": r"\$(\d+)",
        "dates": r"(\d{2}/\d{2}/\d{4})"
    },
    scroll=True,  # Activar scroll automático
    wait_for=".content-loaded"  # Esperar elemento específico
)

# Cerrar el navegador al finalizar
await browser.close()
```

### 3. Análisis de Paquetes

```python
from core.analysis_engine import AnalysisEngine
from core.schemas import SalesQuery

query = SalesQuery(
    client_name="Test Client",
    destination="Cancun",
    dates={
        "departure": "2025-03-01",
        "return": "2025-03-08"
    },
    preferences={
        "max_budget": 2000,
        "min_nights": 5,
        "activities": ["snorkel", "beach"]
    }
)

engine = AnalysisEngine()
analysis = await engine.analyze_packages(query, packages)
insights = analysis.insights
recommendations = analysis.recommendations
```

### 4. Gestión de Ventas

```python
from core.sales_assistant import SalesAssistant
from core.schemas import SessionState

assistant = SalesAssistant()
session = SessionState(client_name="Test Client")

# Iniciar interacción
await assistant.start_interaction(session)

# Refinar búsqueda
feedback = {"price": "too high", "activities": "more beach activities"}
await assistant.refine_search(session, feedback)

# Generar presupuesto
budget = await assistant.generate_budget(session)
```

## Seguridad

El proyecto utiliza el paquete `safety` para verificar vulnerabilidades en las dependencias. Para ejecutar una verificación:

```bash
safety check
```

## Contribuciones

1. Fork el repositorio
2. Cree una rama para su característica (`git checkout -b feature/amazing-feature`)
3. Commit sus cambios (`git commit -m 'Add some amazing feature'`)
4. Push a la rama (`git push origin feature/amazing-feature`)
5. Abra un Pull Request

## Licencia

Este proyecto está licenciado bajo la Licencia MIT - vea el archivo [LICENSE](LICENSE) para más detalles.
