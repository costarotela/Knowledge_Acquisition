"""
Agent system configuration.
"""
from pathlib import Path
import os

# Base paths
BASE_DIR = Path(__file__).parent.parent
MODELS_DIR = BASE_DIR / "models"

# YouTube Agent Configuration
YOUTUBE_AGENT_CONFIG = {
    "frame_extractor": {
        "fps": 1,  # Extract 1 frame per second
        "min_scene_length": 2.0,  # Minimum scene length in seconds
        "output_dir": str(BASE_DIR / "data" / "frames")
    },
    "topic_clustering": {
        "model_name": "sentence-transformers/all-MiniLM-L6-v2",
        "min_cluster_size": 3
    }
}

# Web Research Agent Configuration
WEB_RESEARCH_CONFIG = {
    "brave_search": {
        "api_key": os.getenv("BRAVE_API_KEY"),
        "max_results": 10,
        "timeout": 30
    },
    "credibility_filter": {
        "min_domain_authority": 30,
        "check_ssl": True,
        "blacklist_file": str(BASE_DIR / "config" / "domain_blacklist.txt")
    }
}

# GitHub Agent Configuration
GITHUB_AGENT_CONFIG = {
    "code_analyzer": {
        "languages": ["python", "javascript", "typescript"],
        "max_file_size": 1_000_000,  # 1MB
        "ignore_patterns": ["node_modules", "venv", "__pycache__"]
    },
    "repo_trends": {
        "min_stars": 100,
        "max_repos": 1000,
        "update_interval": 86400  # 24 hours
    }
}

# RAG Agent Configuration
RAG_AGENT_CONFIG = {
    "hypothesis_generator": {
        "model_name": "gpt-4-0125-preview",
        "temperature": 0.7,
        "max_hypotheses": 5
    },
    "knowledge_synthesis": {
        "chunk_size": 1000,
        "overlap": 200,
        "rerank_top_k": 10
    }
}

def get_agent_config(agent_type: str) -> dict:
    """Get configuration for a specific agent type."""
    configs = {
        "youtube": YOUTUBE_AGENT_CONFIG,
        "web_research": WEB_RESEARCH_CONFIG,
        "github": GITHUB_AGENT_CONFIG,
        "rag": RAG_AGENT_CONFIG
    }
    return configs.get(agent_type, {})
