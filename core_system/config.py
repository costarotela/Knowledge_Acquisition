"""
Core system configuration.
"""
from pathlib import Path
from typing import Dict, Any
import os

# Base paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
MODELS_DIR = BASE_DIR / "models"

# Knowledge Base Configuration
KNOWLEDGE_BASE_CONFIG = {
    "vector_db": {
        "type": "chroma",  # or "pinecone"
        "path": str(DATA_DIR / "vector_store"),
        "collection_name": "knowledge_collection"
    },
    "graph_db": {
        "type": "neo4j",
        "uri": os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        "user": os.getenv("NEO4J_USER", "neo4j"),
        "password": os.getenv("NEO4J_PASSWORD", "password")
    }
}

# Agent Orchestrator Configuration
ORCHESTRATOR_CONFIG = {
    "task_queue": {
        "broker_url": os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0"),
        "result_backend": os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")
    },
    "max_concurrent_tasks": 5,
    "task_timeout": 3600  # 1 hour
}

# Multimodal Processor Configuration
MULTIMODAL_CONFIG = {
    "vision": {
        "model_type": "llava-1.6",
        "model_path": str(MODELS_DIR / "vision_models" / "llava-1.6"),
        "device": "cuda" if os.getenv("USE_CUDA", "1") == "1" else "cpu"
    },
    "audio": {
        "model_type": "whisper-large-v3",
        "model_path": str(MODELS_DIR / "audio_models" / "whisper-large-v3"),
        "device": "cuda" if os.getenv("USE_CUDA", "1") == "1" else "cpu"
    },
    "document": {
        "parser_type": "unstructured",
        "max_chunk_size": 1000
    }
}

def get_config() -> Dict[str, Any]:
    """Get the complete configuration dictionary."""
    return {
        "knowledge_base": KNOWLEDGE_BASE_CONFIG,
        "orchestrator": ORCHESTRATOR_CONFIG,
        "multimodal": MULTIMODAL_CONFIG
    }
