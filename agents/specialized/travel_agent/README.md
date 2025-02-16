# Agente de Viajes

Agente de IA avanzado para asistencia en ventas de viajes, con capacidades RAG y análisis en tiempo real.

## Características

- **Asistente de Ventas Inteligente**
  - Procesamiento de instrucciones del vendedor
  - Generación de presupuestos personalizados
  - Refinamiento iterativo según feedback
  - Búsqueda semántica de paquetes con lenguaje natural
  - Integración con múltiples proveedores (Aero, Despegar)

- **Análisis Avanzado**
  - Comparación de precios y condiciones
  - Detección de oportunidades
  - Análisis de temporadas y tendencias
  - Cálculo de similitud entre paquetes usando embeddings

- **Base de Datos y Almacenamiento**
  - Supabase para almacenamiento estructurado
  - Tablas optimizadas para paquetes, presupuestos y sesiones
  - Historial de precios para análisis de tendencias
  - Almacenamiento vectorial de embeddings para búsqueda semántica
  - Sistema de caché con TTL para optimizar búsquedas

- **Generación de Presupuestos**
  - Templates personalizables con Jinja2
  - Perfiles de cliente predefinidos
  - Múltiples formatos de salida (HTML, PDF)
  - Estilos adaptables por tipo de cliente
  - Internacionalización de monedas y fechas

- **RAG y Aprendizaje Continuo**
  - Almacenamiento vectorial de conocimiento
  - Búsqueda semántica de paquetes similares
  - Mejora continua de recomendaciones

## Requisitos del Sistema

- Python 3.11 o superior
- Conda (Miniconda o Anaconda)
- Node.js 18 o superior (para algunas funcionalidades de Playwright)

## Instalación

1. Clonar el repositorio:
```bash
git clone https://github.com/costarotela/Knowledge_Acquisition.git
cd Knowledge_Acquisition/agents/specialized/travel_agent
```

2. Ejecutar el script de configuración del entorno:
```bash
./scripts/setup_environment.sh
```

Este script:
- Crea un entorno conda llamado `travel-agent-py311` con Python 3.11
- Instala todas las dependencias necesarias
- Configura el archivo `.env` con las variables de entorno requeridas
- Instala los navegadores necesarios para Playwright

3. Activar el entorno conda:
```bash
conda activate travel-agent-py311
```

4. Configurar las variables de entorno en el archivo `.env`:
```bash
OPENAI_API_KEY=tu_clave_de_openai          # Para generación de embeddings
PUBLIC_SUPABASE_URL=tu_url_de_supabase     # URL de Supabase
SUPABASE_SERVICE_KEY=tu_clave_de_supabase  # Clave de servicio de Supabase
```

## Estructura del Proyecto

```
travel_agent/
├── config/                 # Configuración
│   └── providers/         # Configuración de proveedores
│       ├── aero.json      # Configuración Aero
│       └── despegar.json  # Configuración Despegar
├── core/                   # Componentes principales
│   ├── agent.py           # Agente principal
│   ├── analysis_engine.py # Motor de análisis
│   ├── browser_manager.py # Gestor de navegación
│   ├── cache_manager.py   # Gestor de caché
│   ├── budget_engine.py   # Motor de presupuestos
│   ├── price_monitor.py   # Monitor de precios
│   ├── sales_assistant.py # Asistente de ventas
│   ├── storage_manager.py # Gestor de almacenamiento
│   └── schemas.py         # Modelos de datos
├── templates/             # Templates de presupuestos
│   ├── styles/           # Estilos CSS
│   ├── partials/         # Componentes parciales
│   ├── profiles.json     # Perfiles de cliente
│   └── default.html      # Template principal
├── scripts/               # Scripts de utilidad
│   ├── setup_environment.sh
│   ├── init_supabase.sql
│   ├── load_sample_data.py
│   └── search_packages.py
└── tests/                 # Pruebas
```

## Uso

### Búsqueda de Paquetes

```python
from travel_agent.scripts.search_packages import search_packages

# Búsqueda con lenguaje natural
resultados = search_packages(
    "Busco un viaje a la playa con actividades acuáticas para 2 personas"
)

# Los resultados incluyen paquetes relevantes ordenados por similitud
for paquete in resultados:
    print(f"Título: {paquete.title}")
    print(f"Precio: ${paquete.price}")
    print(f"Actividades: {paquete.activities}")
    print("---")
```

### Generación de Presupuestos

```python
from travel_agent.core.budget_engine import BudgetEngine
from travel_agent.core.schemas import CustomerProfile

# Crear motor de presupuestos
engine = BudgetEngine(locale="es_AR", currency="USD")

# Definir perfil del cliente
cliente = CustomerProfile(
    name="Juan Pérez",
    type="premium",  # Tipos: default, premium, corporate, family
    email="juan@example.com"
)

# Generar presupuesto
presupuesto_html = engine.generate_budget(
    packages=paquetes,
    customer_profile=cliente,
    template_name="default.html",
    output_format="html"
)

# También se puede generar en PDF
presupuesto_pdf = engine.generate_budget(
    packages=paquetes,
    customer_profile=cliente,
    template_name="default.html",
    output_format="pdf"
)
```

## Variables de Entorno

```bash
OPENAI_API_KEY=tu_clave_de_openai          # Para generación de embeddings
PUBLIC_SUPABASE_URL=tu_url_de_supabase     # URL de Supabase
SUPABASE_SERVICE_KEY=tu_clave_de_supabase  # Clave de servicio de Supabase
```

## Dependencias Adicionales

```bash
# Para generación de PDFs
apt-get install weasyprint

# Para internacionalización
pip install babel

# Para templates
pip install jinja2
```

## Seguridad

- Versiones de dependencias actualizadas y seguras
- Manejo seguro de claves API mediante variables de entorno
- Validación de datos con Pydantic
- Pruebas automatizadas para verificar comportamiento

## Licencia

Este proyecto está licenciado bajo la Licencia MIT.
