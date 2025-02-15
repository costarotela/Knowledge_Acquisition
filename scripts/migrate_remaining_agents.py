#!/usr/bin/env python3
"""
Script para migrar los agentes restantes a la estructura estándar.
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
AGENTS_DIR = BASE_DIR / "agents"
SPECIALIZED_DIR = AGENTS_DIR / "specialized"

# Estructura estándar para cada agente
STANDARD_STRUCTURE = {
    "config": {
        "__init__.py": "",
        "settings.py": "\"\"\"Agent-specific settings.\"\"\"\n\nfrom ...config.base_config import AgentConfig\n"
    },
    "core": {
        "__init__.py": "",
        "agent.py": "",  # Se copiará el contenido del archivo original
        "interfaces.py": "\"\"\"Agent-specific interfaces.\"\"\"\n"
    },
    "processors": {
        "__init__.py": ""
    },
    "schemas": {
        "__init__.py": "",
        "models.py": "\"\"\"Data models for the agent.\"\"\"\n\nfrom pydantic import BaseModel\n"
    },
    "knowledge": {
        "__init__.py": "",
        "domain.py": "\"\"\"Domain-specific knowledge.\"\"\"\n"
    },
    "tests": {
        "__init__.py": "",
        "conftest.py": "\"\"\"Test configurations and fixtures.\"\"\"\n"
    }
}

def create_standard_structure(agent_dir: Path, agent_file: Path):
    """Crear estructura estándar para un agente y mover su código."""
    try:
        # Crear directorios y archivos base
        for dir_name, files in STANDARD_STRUCTURE.items():
            dir_path = agent_dir / dir_name
            dir_path.mkdir(exist_ok=True)
            
            for file_name, content in files.items():
                file_path = dir_path / file_name
                if not file_path.exists():
                    with file_path.open('w') as f:
                        f.write(content)
                    logger.info(f"Created {file_path}")
        
        # Mover el código del agente a core/agent.py
        if agent_file.exists():
            with agent_file.open('r') as source:
                content = source.read()
                
            target_file = agent_dir / "core" / "agent.py"
            with target_file.open('w') as target:
                target.write(content)
            
            # Crear backup del archivo original
            backup_file = agent_file.parent / f"{agent_file.stem}_backup{agent_file.suffix}"
            shutil.move(agent_file, backup_file)
            logger.info(f"Moved {agent_file} to {target_file}")
            logger.info(f"Created backup at {backup_file}")
            
    except Exception as e:
        logger.error(f"Error creating structure for {agent_dir.name}: {str(e)}")
        raise

def main():
    """Función principal de migración."""
    try:
        # Lista de agentes a migrar
        agents_to_migrate = [
            "academic_agent",
            "social_media_agent"
        ]
        
        for agent_name in agents_to_migrate:
            logger.info(f"Migrating {agent_name}...")
            
            agent_file = SPECIALIZED_DIR / f"{agent_name}.py"
            agent_dir = SPECIALIZED_DIR / agent_name
            
            # Crear directorio si no existe
            agent_dir.mkdir(exist_ok=True)
            
            # Crear estructura y mover código
            create_standard_structure(agent_dir, agent_file)
            
            logger.info(f"Successfully migrated {agent_name}")
        
        logger.info("Migration completed successfully!")
        
    except Exception as e:
        logger.error(f"Migration failed: {str(e)}")
        raise

if __name__ == "__main__":
    main()
