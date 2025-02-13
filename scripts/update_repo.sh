#!/bin/bash

# Colores para output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}Actualizando repositorio...${NC}"

# Asegurar que estamos en la rama feature/modular-architecture
BRANCH=$(git branch --show-current)
if [ "$BRANCH" != "feature/modular-architecture" ]; then
    echo -e "${YELLOW}Cambiando a rama feature/modular-architecture...${NC}"
    git checkout feature/modular-architecture
fi

# Agregar archivos nuevos y modificados
echo -e "${YELLOW}Agregando archivos nuevos y modificados...${NC}"
git add .

# Remover archivos eliminados
echo -e "${YELLOW}Removiendo archivos eliminados del tracking...${NC}"
git add -u

# Crear commit con timestamp
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
echo -e "${YELLOW}Creando commit...${NC}"
git commit -m "refactor: Actualización de arquitectura modular [$TIMESTAMP]"

# Push a la rama
echo -e "${YELLOW}Push a GitHub...${NC}"
git push origin feature/modular-architecture

echo -e "${GREEN}¡Repositorio actualizado exitosamente!${NC}"
