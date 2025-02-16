#!/bin/bash

echo "🔄 Configurando entorno conda..."

# Verificar si conda está instalado
if ! command -v conda &> /dev/null; then
    echo "❌ Error: conda no está instalado. Por favor, instala Miniconda o Anaconda primero."
    exit 1
fi

# Nombre del entorno conda
CONDA_ENV="travel-agent-py311"

# Crear entorno conda si no existe
if ! conda env list | grep -q "^${CONDA_ENV}"; then
    echo "🔨 Creando entorno conda ${CONDA_ENV}..."
    conda create -n ${CONDA_ENV} python=3.11 -y
fi

# Activar entorno conda
echo "🔌 Activando entorno conda ${CONDA_ENV}..."
eval "$(conda shell.bash hook)"
conda activate ${CONDA_ENV}

# Verificar que estamos en el entorno correcto
if [[ "${CONDA_DEFAULT_ENV}" != "${CONDA_ENV}" ]]; then
    echo "❌ Error: No se pudo activar el entorno conda ${CONDA_ENV}"
    exit 1
fi

echo "✅ Entorno conda configurado correctamente!"
echo "💡 Para activar el entorno en nuevas terminales usa: conda activate ${CONDA_ENV}"
