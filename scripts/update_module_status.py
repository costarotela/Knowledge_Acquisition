#!/usr/bin/env python3
"""
Script para actualizar el estado de los módulos administrativos.
Analiza el código fuente y las pruebas para determinar el estado actual.
"""

import os
import sys
from pathlib import Path
import ast
import pytest
import coverage
import logging
from datetime import datetime
from typing import Dict, List, Tuple

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Directorio base
BASE_DIR = Path("/home/pablo/CascadeProjects/NaturalAgent_backup_20250213_091711/Knowledge_Acquisition")
ADMIN_DIR = BASE_DIR / "admin_interface"

def analyze_module_implementation(module_id: str) -> Tuple[float, int, int]:
    """Analizar implementación de un módulo."""
    module_dir = ADMIN_DIR / "pages" / f"{module_id}.py"
    if not module_dir.exists():
        return 0.0, 0, 0
    
    # Analizar código fuente
    with open(module_dir, 'r') as f:
        tree = ast.parse(f.read())
    
    functions = len([node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)])
    classes = len([node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)])
    
    # Ejecutar pruebas y obtener cobertura
    cov = coverage.Coverage()
    cov.start()
    
    test_module = ADMIN_DIR / "tests" / f"test_{module_id}.py"
    if test_module.exists():
        pytest.main([str(test_module), "-q"])
    
    cov.stop()
    total = cov.report()
    
    return total, functions, classes

def update_module_status():
    """Actualizar estado de módulos en module_status.py."""
    status_file = ADMIN_DIR / "config" / "module_status.py"
    
    if not status_file.exists():
        logger.error(f"Status file not found: {status_file}")
        return
    
    # Leer archivo actual
    with open(status_file, 'r') as f:
        content = f.read()
    
    # Analizar cada módulo
    modules = {
        "knowledge_explorer": "Knowledge Explorer",
        "performance_monitor": "Performance Monitor",
        "validation_tools": "Validation Tools",
        "agent_manager": "Agent Manager"
    }
    
    updated_configs = []
    for module_id, name in modules.items():
        coverage, functions, classes = analyze_module_implementation(module_id)
        
        # Determinar estado basado en métricas
        status = "PLANNED"
        if functions > 0 or classes > 0:
            if coverage == 0:
                status = "IN_DEVELOPMENT"
            elif coverage < 50:
                status = "TESTING"
            elif coverage < 80:
                status = "BETA"
            else:
                status = "PRODUCTION"
        
        # Crear configuración actualizada
        config = f"""    "{module_id}": ModuleConfig(
        id="{module_id}",
        name="{name}",
        description="...",  # Mantener descripción existente
        status=ModuleStatus.{status},
        enabled={status in ["BETA", "PRODUCTION"]},
        test_coverage={coverage/100},
        implementation_date={f'datetime({datetime.now().year}, {datetime.now().month}, {datetime.now().day})' if status != "PLANNED" else None},
        tags=["..."],  # Mantener tags existentes
    ),"""
        
        updated_configs.append(config)
    
    # Actualizar archivo
    start_marker = "ADMIN_MODULES: Dict[str, ModuleConfig] = {"
    end_marker = "}"
    
    start_idx = content.find(start_marker) + len(start_marker)
    end_idx = content.find(end_marker, start_idx)
    
    new_content = (
        content[:start_idx] + "\n" +
        "\n".join(updated_configs) + "\n" +
        content[end_idx:]
    )
    
    # Guardar cambios
    with open(status_file, 'w') as f:
        f.write(new_content)
    
    logger.info("Module status updated successfully!")

if __name__ == "__main__":
    update_module_status()
