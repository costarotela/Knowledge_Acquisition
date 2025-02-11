#!/bin/bash

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}Configurando Knowledge Acquisition System...${NC}"

# Verificar requisitos
echo -e "\n${YELLOW}Verificando requisitos...${NC}"

# Verificar Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Python 3 no está instalado${NC}"
    exit 1
fi

# Verificar Conda
if ! command -v conda &> /dev/null; then
    echo -e "${RED}Conda no está instalado${NC}"
    exit 1
fi

# Crear entorno Conda
echo -e "\n${YELLOW}Creando entorno Conda...${NC}"
conda env create -f environment.yml
conda activate knowledge-acquisition

# Configurar variables de entorno
echo -e "\n${YELLOW}Configurando variables de entorno...${NC}"
if [ ! -f .env ]; then
    cp .env.example .env
    echo -e "${GREEN}Archivo .env creado. Por favor, configura tus claves API.${NC}"
fi

# Configurar base de datos
echo -e "\n${YELLOW}Configurando base de datos...${NC}"
for f in sql/migrations/*.sql
do
    echo -e "Ejecutando $f..."
    # TODO: Ejecutar script SQL en Supabase
done

# Configurar Sphinx para documentación
echo -e "\n${YELLOW}Configurando documentación...${NC}"
pip install sphinx sphinx-rtd-theme
sphinx-quickstart docs \
    --quiet \
    --project="Knowledge Acquisition" \
    --author="Tu Nombre" \
    --sep \
    --ext-autodoc \
    --ext-viewcode \
    --ext-napoleon

# Generar documentación
cd docs
make html
cd ..

# Configurar pre-commit hooks
echo -e "\n${YELLOW}Configurando git hooks...${NC}"
pip install pre-commit
pre-commit install

# Crear directorios necesarios
echo -e "\n${YELLOW}Creando directorios...${NC}"
mkdir -p data/raw data/processed logs temp_audio

# Ejecutar tests
echo -e "\n${YELLOW}Ejecutando tests...${NC}"
pytest tests/

echo -e "\n${GREEN}¡Configuración completada!${NC}"
echo -e "\nPasos siguientes:"
echo -e "1. Edita ${YELLOW}.env${NC} con tus claves API"
echo -e "2. Ejecuta ${YELLOW}streamlit run app.py${NC} para iniciar la aplicación"
