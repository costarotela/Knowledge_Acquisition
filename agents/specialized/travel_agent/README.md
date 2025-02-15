# Travel Agent Specialized Module

Este módulo implementa un agente especializado para la búsqueda, comparación y análisis de paquetes turísticos utilizando browser-use para la extracción de datos.

## Requisitos del Sistema

- Python 3.11 o superior
- Conda (Miniconda o Anaconda)
- Navegadores web (se instalarán automáticamente con playwright)
- Conexión a Internet
- Clave API de OpenAI

## Características

- Extracción automática de datos de proveedores turísticos
- Comparación y análisis de paquetes
- Generación de recomendaciones personalizadas
- Soporte para múltiples proveedores (Aero, Ola, etc.)
- Entorno virtual aislado y específico

## Instalación

### Método Automático (Recomendado)

1. Clone el repositorio y navegue al directorio del agente:
```bash
cd agents/specialized/travel_agent
```

2. Ejecute el script de instalación:
```bash
chmod +x setup.sh
./setup.sh
```

3. Configure sus claves API en el archivo `.env`

### Instalación Manual

1. Crear el entorno virtual:
```bash
conda env create -f environment.yml
```

2. Activar el entorno:
```bash
conda activate travel-agent
```

3. Instalar playwright:
```bash
playwright install
```

4. Crear y configurar el archivo `.env`:
```bash
cp .env.example .env
# Edite .env con sus claves API
```

## Estructura del Módulo

```
travel_agent/
├── __init__.py           # Exporta las clases principales
├── travel_agent.py       # Implementación principal del agente
├── browser_manager.py    # Gestión de navegación y extracción
├── providers.py          # Definición de proveedores
├── schemas.py           # Modelos de datos
├── environment.yml      # Configuración del entorno
├── setup.sh            # Script de instalación
└── tests/              # Pruebas unitarias
```

## Estructura de Datos

### Paquete de Viaje (TravelPackage)

Los paquetes de viaje deben incluir los siguientes campos obligatorios:

```python
{
    "id": str,                    # Identificador único del paquete
    "provider": str,              # Nombre del proveedor
    "destination": str,           # Destino del viaje
    "title": str,                 # Título del paquete
    "description": str,           # Descripción detallada
    "price": float,              # Precio del paquete
    "currency": str,             # Moneda (USD, EUR, etc.)
    "duration": int,             # Duración en días
    "start_date": datetime,      # Fecha de inicio (YYYY-MM-DD)
    "end_date": datetime,        # Fecha de fin (YYYY-MM-DD)
    "accommodation": {           # Detalles del alojamiento
        "name": str,
        "type": str,
        "location": str,
        "rating": float,
        "amenities": List[str],
        "room_types": List[str]
    },
    "activities": List[{         # Lista de actividades
        "name": str,
        "description": str,
        "duration": str,
        "price": float,
        "included": List[str],
        "requirements": List[str]
    }],
    "included_services": List[str],  # Servicios incluidos
    "excluded_services": List[str],  # Servicios no incluidos
    "booking_url": str,              # URL para reservar
    "terms_conditions": str          # Términos y condiciones
}
```

### Validación de Datos

El módulo implementa una validación estricta de los paquetes de viaje:

1. **Campos Requeridos**: Todos los campos listados arriba son obligatorios
2. **Validación de Fechas**: 
   - Formato: YYYY-MM-DD
   - Las fechas deben ser instancias de `datetime` o strings en el formato correcto
3. **Validación de Precios**:
   - Deben ser números positivos
   - Se admiten decimales para centavos
4. **Validación de Duración**:
   - Debe ser un número entero positivo
   - Representa la cantidad de días del viaje

## Uso Básico

```python
from travel_agent import TravelAgent
from core_system.knowledge_base import KnowledgeBase

# Inicializar agente
agent = TravelAgent(
    knowledge_base=KnowledgeBase(),
    providers=[
        TourismProvider.create_aero_provider(),
        TourismProvider.create_ola_provider()
    ]
)

# Buscar paquetes
packages = await agent.search_packages(
    destination="Bariloche",
    dates={
        "start": "2025-03-01",
        "end": "2025-03-10"
    }
)

# Comparar y analizar
analysis = await agent.compare_packages(packages)
```

## Uso del Módulo

### Búsqueda de Paquetes

```python
from travel_agent import TravelAgent
from datetime import datetime

# Inicializar el agente
agent = TravelAgent(knowledge_base=kb)

# Buscar paquetes
packages = await agent.search_packages(
    destination="Bariloche",
    dates={
        "start": "2025-03-01",
        "end": "2025-03-10"
    },
    preferences={
        "max_price": 2000,
        "activities": ["hiking", "skiing"]
    }
)

# Comparar paquetes
comparison = await agent.compare_packages(packages)
```

## Desarrollo

### Configuración del Entorno de Desarrollo

1. Crear rama feature:
```bash
git checkout -b feature/nueva-funcionalidad
```

2. Activar entorno:
```bash
conda activate travel-agent
```

3. Ejecutar pruebas:
```bash
pytest tests/
```

### Agregar Nuevo Proveedor

1. Extender la clase `TourismProvider`
2. Definir reglas de extracción específicas
3. Implementar métodos de validación
4. Agregar pruebas unitarias

## Solución de Problemas

### Problemas Comunes

1. **Error al crear el entorno conda**
   - Verifique que tiene conda instalado: `conda --version`
   - Actualice conda: `conda update -n base conda`

2. **Error con playwright**
   - Reinstale los navegadores: `playwright install`
   - Verifique las dependencias del sistema: `playwright install-deps`

3. **Errores de extracción**
   - Verifique su conexión a Internet
   - Confirme que las reglas de extracción están actualizadas
   - Revise los logs en modo DEBUG

## Notas

- Este módulo está diseñado para funcionar de manera independiente
- Las dependencias se mantienen separadas para facilitar la modularidad
- Se recomienda usar el entorno virtual específico para desarrollo
- Actualice regularmente las reglas de extracción para mantener la compatibilidad con los sitios web

## Contribuir

1. Fork el repositorio
2. Cree una rama para su funcionalidad
3. Implemente sus cambios
4. Agregue pruebas
5. Envíe un pull request

## Licencia

MIT License - ver archivo LICENSE para más detalles
