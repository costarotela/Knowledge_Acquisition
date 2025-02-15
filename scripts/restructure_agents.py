#!/usr/bin/env python3
"""
Script para reestructurar los agentes y estandarizar su estructura.
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

# Estructura estándar para cada agente
STANDARD_STRUCTURE = {
    "config": {
        "__init__.py": "",
        "settings.py": "\"\"\"Agent-specific settings.\"\"\"\n\nfrom ...config.base_config import AgentConfig\n"
    },
    "core": {
        "__init__.py": "",
        "agent.py": "\"\"\"Core agent implementation.\"\"\"\n\nfrom ...core.base import BaseAgent\n",
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

# Mapeo de agentes a mover
AGENT_MAPPING = {
    "custom_rag_agent": "rag_agent",
    "github_agent": "github_agent",
    "web_research_agent": "web_research_agent",
    "youtube_agent": "youtube_agent",
    "travel_agent": "travel_agent"
}

def create_standard_structure(agent_dir: Path):
    """Crear estructura estándar para un agente."""
    try:
        # Crear el directorio base del agente si no existe
        agent_dir.mkdir(parents=True, exist_ok=True)
        
        for dir_name, files in STANDARD_STRUCTURE.items():
            dir_path = agent_dir / dir_name
            dir_path.mkdir(parents=True, exist_ok=True)
            
            for file_name, content in files.items():
                file_path = dir_path / file_name
                if not file_path.exists():
                    with open(file_path, 'w') as f:
                        f.write(content)
        
        logger.info(f"Created standard structure in {agent_dir}")
    except Exception as e:
        logger.error(f"Error creating standard structure: {e}")
        raise

def migrate_agent(source_dir: Path, target_dir: Path):
    """Migrar un agente a la nueva estructura."""
    try:
        # Crear estructura estándar
        create_standard_structure(target_dir)
        
        # Mover archivos existentes a las ubicaciones correctas
        if source_dir.exists():
            for item in source_dir.glob('**/*'):
                if item.is_file():
                    # Determinar destino basado en el tipo de archivo
                    relative_path = item.relative_to(source_dir)
                    if "test" in str(relative_path):
                        dest = target_dir / "tests" / relative_path.name
                    elif "schema" in str(relative_path) or "model" in str(relative_path):
                        dest = target_dir / "schemas" / relative_path.name
                    elif "process" in str(relative_path):
                        dest = target_dir / "processors" / relative_path.name
                    else:
                        dest = target_dir / "core" / relative_path.name
                    
                    # Crear directorio destino si no existe
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Copiar archivo
                    shutil.copy2(item, dest)
                    logger.info(f"Moved {item} to {dest}")
        
        logger.info(f"Successfully migrated {source_dir.name}")
        
    except Exception as e:
        logger.error(f"Error migrating {source_dir.name}: {str(e)}")
        raise

def main():
    """Función principal de migración."""
    try:
        # Crear directorios base si no existen
        for dir_name in ["config", "core", "specialized", "tests"]:
            (AGENTS_DIR / dir_name).mkdir(exist_ok=True)
        
        # Migrar cada agente
        for old_name, new_name in AGENT_MAPPING.items():
            source_dir = AGENTS_DIR / old_name
            target_dir = AGENTS_DIR / "specialized" / new_name
            
            logger.info(f"Migrating {old_name} to {new_name}...")
            migrate_agent(source_dir, target_dir)
            
            # Respaldar directorio original
            if source_dir.exists():
                backup_dir = source_dir.parent / f"{old_name}_backup"
                shutil.move(source_dir, backup_dir)
                logger.info(f"Backed up {old_name} to {backup_dir}")
        
        logger.info("Migration completed successfully!")
        
    except Exception as e:
        logger.error(f"Migration failed: {str(e)}")
        raise

if __name__ == "__main__":
    main()
