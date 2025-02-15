#!/bin/bash

# Directorio del proyecto
PROJECT_DIR="/home/pablo/CascadeProjects/NaturalAgent_backup_20250213_091711/Knowledge_Acquisition"

# Ir al directorio del proyecto
cd "$PROJECT_DIR" || exit 1

# Agregar archivos modificados y nuevos
echo "Agregando archivos modificados y nuevos..."
git add agents/specialized/travel_agent/README.md \
    agents/specialized/travel_agent/core/agent.py \
    agents/specialized/travel_agent/requirements.txt \
    agents/specialized/travel_agent/tests/conftest.py \
    agents/specialized/travel_agent/core/analysis_engine.py \
    agents/specialized/travel_agent/core/price_monitor.py \
    agents/specialized/travel_agent/core/sales_assistant.py \
    agents/specialized/travel_agent/core/schemas.py \
    agents/specialized/travel_agent/core/session_manager.py \
    agents/specialized/travel_agent/pyproject.toml \
    agents/specialized/travel_agent/scripts/ \
    agents/specialized/travel_agent/tests/test_analysis_engine.py \
    agents/specialized/travel_agent/tests/test_sales_assistant.py

# Crear commit
echo "Creando commit..."
git commit -m "feat: Agrega nuevos componentes al Travel Agent

- Agrega analysis_engine.py para análisis de datos de viajes
- Agrega price_monitor.py para monitoreo de precios
- Agrega sales_assistant.py para asistencia en ventas
- Agrega schemas.py para modelos de datos
- Agrega session_manager.py para gestión de sesiones
- Actualiza configuración y dependencias
- Agrega nuevos tests para los componentes"

# Subir cambios
echo "Subiendo cambios al repositorio..."
git push origin feature/admin-interface-refactor

echo "¡Actualización completada!"
