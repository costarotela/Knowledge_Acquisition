#!/usr/bin/env python3
"""
Script para corregir anomalías en la estructura del proyecto.
"""

import os
import shutil
from pathlib import Path
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Directorio base
BASE_DIR = Path("/home/pablo/CascadeProjects/NaturalAgent_backup_20250213_091711/Knowledge_Acquisition")

def fix_admin_directories():
    """Unificar directorios admin."""
    admin_dir = BASE_DIR / "admin"
    admin_interface_dir = BASE_DIR / "admin_interface"
    
    if admin_dir.exists() and admin_interface_dir.exists():
        # Mover contenido de admin/ a admin_interface/
        for item in admin_dir.glob("*"):
            target = admin_interface_dir / item.name
            if not target.exists():
                shutil.move(str(item), str(target))
        
        # Mover admin/ a .old_structure
        backup_dir = BASE_DIR / ".old_structure" / "admin_backup"
        shutil.move(str(admin_dir), str(backup_dir))
        logger.info("Unified admin directories")

def fix_base_agents():
    """Mover base_agents a core."""
    base_agents_dir = BASE_DIR / "agents" / "base_agents"
    core_dir = BASE_DIR / "agents" / "core"
    
    if base_agents_dir.exists():
        # Mover contenido a core/
        for item in base_agents_dir.glob("*"):
            target = core_dir / item.name
            if not target.exists():
                shutil.move(str(item), str(target))
        
        # Mover base_agents/ a .old_structure
        backup_dir = BASE_DIR / ".old_structure" / "base_agents_backup"
        shutil.move(str(base_agents_dir), str(backup_dir))
        logger.info("Moved base_agents to core")

def standardize_processor_directories():
    """Estandarizar nombres de directorios de procesadores."""
    specialized_dir = BASE_DIR / "agents" / "specialized"
    
    for agent_dir in specialized_dir.glob("*"):
        if agent_dir.is_dir():
            processing_dir = agent_dir / "processing"
            processors_dir = agent_dir / "processors"
            
            if processing_dir.exists() and processors_dir.exists():
                # Mover contenido de processing/ a processors/
                for item in processing_dir.glob("*"):
                    target = processors_dir / item.name
                    if not target.exists():
                        shutil.move(str(item), str(target))
                
                # Mover processing/ a .old_structure
                backup_dir = BASE_DIR / ".old_structure" / f"{agent_dir.name}_processing_backup"
                shutil.move(str(processing_dir), str(backup_dir))
                logger.info(f"Unified processor directories for {agent_dir.name}")
            elif processing_dir.exists():
                # Renombrar processing/ a processors/
                processing_dir.rename(processors_dir)
                logger.info(f"Renamed processing to processors for {agent_dir.name}")

def ensure_standard_structure():
    """Asegurar que todos los agentes tengan la estructura estándar."""
    specialized_dir = BASE_DIR / "agents" / "specialized"
    
    standard_dirs = [
        "config",
        "core",
        "processors",
        "schemas",
        "knowledge",
        "tests"
    ]
    
    for agent_dir in specialized_dir.glob("*"):
        if agent_dir.is_dir():
            for std_dir in standard_dirs:
                dir_path = agent_dir / std_dir
                if not dir_path.exists():
                    dir_path.mkdir()
                    (dir_path / "__init__.py").touch()
                    logger.info(f"Created {std_dir} for {agent_dir.name}")

def main():
    """Función principal."""
    try:
        # Crear .old_structure si no existe
        (BASE_DIR / ".old_structure").mkdir(exist_ok=True)
        
        # Ejecutar correcciones
        fix_admin_directories()
        fix_base_agents()
        standardize_processor_directories()
        ensure_standard_structure()
        
        logger.info("Structure fixes completed successfully!")
        
    except Exception as e:
        logger.error(f"Error fixing structure: {str(e)}")
        raise

if __name__ == "__main__":
    main()
