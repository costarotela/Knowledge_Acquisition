#!/bin/bash

# Script de actualización del sistema

echo "Iniciando actualización del Travel Agent..."

# 1. Activar entorno conda
source ~/miniconda3/etc/profile.d/conda.sh
conda activate knowledge-acquisition

# 2. Actualizar dependencias
echo "Actualizando dependencias..."
pip install --upgrade -r requirements.txt

# 3. Ejecutar migraciones de base de datos (si existen)
if [ -f "migrations/migrate.py" ]; then
    echo "Ejecutando migraciones..."
    python migrations/migrate.py
fi

# 4. Limpiar caché
echo "Limpiando caché..."
rm -rf cache/*
mkdir -p cache

# 5. Ejecutar tests
echo "Ejecutando tests..."
pytest tests/

# 6. Verificar vulnerabilidades
echo "Verificando vulnerabilidades..."
safety check

# 7. Actualizar documentación
echo "Actualizando documentación..."
if [ -f "docs/generate.py" ]; then
    python docs/generate.py
fi

# 8. Limpiar archivos temporales
echo "Limpiando archivos temporales..."
find . -type f -name "*.pyc" -delete
find . -type d -name "__pycache__" -delete

echo "Actualización completada!"

# Mostrar estado final
echo -e "\nEstado del sistema:"
echo "-------------------"
python -c "import sys; print(f'Python: {sys.version}')"
pip freeze | grep -E "browser-use|scikit-learn|numpy|pandas"
echo "-------------------"

# Verificar si hay errores pendientes
if [ $? -eq 0 ]; then
    echo "✅ Actualización exitosa"
else
    echo "❌ La actualización completó con errores"
    exit 1
fi
