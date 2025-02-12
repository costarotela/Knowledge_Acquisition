#!/bin/bash

# Activar entorno conda
eval "$(conda shell.bash hook)"
conda activate knowledge-acquisition

# Ejecutar script de gestión
python scripts/manage_repo.py
