#!/bin/bash

# Colores para output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}Actualizando repositorio...${NC}"

# Activar entorno conda
echo -e "${GREEN}Activando entorno conda...${NC}"
source ~/miniconda3/etc/profile.d/conda.sh
conda activate knowledge-acquisition

# Actualizar dependencias
echo -e "${GREEN}Actualizando dependencias...${NC}"
pip install -r requirements.txt

# Limpiar archivos temporales
echo -e "${GREEN}Limpiando archivos temporales...${NC}"
find . -type f -name "*.pyc" -delete
find . -type d -name "__pycache__" -delete

# Actualizar git
echo -e "${GREEN}Actualizando git...${NC}"
git add .
git status

# Solicitar mensaje de commit
echo -e "${YELLOW}Ingrese mensaje de commit:${NC}"
read commit_message

# Realizar commit y push
git commit -m "$commit_message"
git push origin main

echo -e "${GREEN}¡Repositorio actualizado exitosamente!${NC}"
