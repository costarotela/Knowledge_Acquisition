#!/bin/bash

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Iniciando configuración del agente de viajes...${NC}"

# Verificar si conda está instalado
if ! command -v conda &> /dev/null; then
    echo -e "${RED}Error: conda no está instalado. Por favor, instale Miniconda o Anaconda.${NC}"
    exit 1
fi

# Crear el entorno conda
echo -e "${YELLOW}Creando entorno conda 'travel-agent'...${NC}"
conda env create -f environment.yml

# Verificar si la creación fue exitosa
if [ $? -eq 0 ]; then
    echo -e "${GREEN}Entorno conda creado exitosamente.${NC}"
else
    echo -e "${RED}Error al crear el entorno conda.${NC}"
    exit 1
fi

# Activar el entorno
echo -e "${YELLOW}Activando entorno travel-agent...${NC}"
source $(conda info --base)/etc/profile.d/conda.sh
conda activate travel-agent

# Instalar playwright
echo -e "${YELLOW}Instalando navegadores con playwright...${NC}"
playwright install

# Crear archivo .env si no existe
if [ ! -f .env ]; then
    echo -e "${YELLOW}Creando archivo .env...${NC}"
    echo "# Configuración del agente de viajes" > .env
    echo "OPENAI_API_KEY=your_api_key_here" >> .env
    echo "DEBUG=False" >> .env
    echo -e "${GREEN}Archivo .env creado. Por favor, configure sus claves API.${NC}"
fi

# Verificar la instalación
echo -e "${YELLOW}Verificando instalación...${NC}"
if python -c "import browser_use; import playwright; import langchain" &> /dev/null; then
    echo -e "${GREEN}Todas las dependencias están instaladas correctamente.${NC}"
else
    echo -e "${RED}Error: Algunas dependencias no se instalaron correctamente.${NC}"
    exit 1
fi

echo -e "${GREEN}¡Configuración completada!${NC}"
echo -e "${YELLOW}Para comenzar a usar el agente:${NC}"
echo -e "1. Configure sus claves API en el archivo .env"
echo -e "2. Active el entorno: conda activate travel-agent"
echo -e "3. Execute las pruebas: pytest tests/"
