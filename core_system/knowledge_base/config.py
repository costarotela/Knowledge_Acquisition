"""
Configuration settings for the knowledge base system.
"""

from typing import Dict, Any, Optional
from pydantic import BaseSettings, Field


class ChromaDBSettings(BaseSettings):
    """Configuration for ChromaDB vector store."""
    collection_name: str = "knowledge_base"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    persist_directory: str = "./data/chromadb"
    distance_metric: str = "cosine"
    anonymized_telemetry: bool = False
    
    class Config:
        env_prefix = "CHROMADB_"


class Neo4jSettings(BaseSettings):
    """Configuration for Neo4j graph store."""
    uri: str = Field(..., env="NEO4J_URI")
    username: str = Field(..., env="NEO4J_USERNAME")
    password: str = Field(..., env="NEO4J_PASSWORD")
    database: str = "neo4j"
    max_connection_lifetime: int = 3600  # 1 hour
    max_connection_pool_size: int = 50
    
    class Config:
        env_prefix = "NEO4J_"


class SearchSettings(BaseSettings):
    """Configuration for search operations."""
    default_limit: int = 10
    max_limit: int = 100
    min_confidence: float = 0.5
    max_search_depth: int = 3
    cache_ttl: int = 300  # 5 minutes
    timeout: int = 30  # seconds
    
    class Config:
        env_prefix = "SEARCH_"


class KnowledgeBaseSettings(BaseSettings):
    """Main configuration for the knowledge base system."""
    chroma: ChromaDBSettings = ChromaDBSettings()
    neo4j: Neo4jSettings = Neo4jSettings()
    search: SearchSettings = SearchSettings()
    
    # Feature flags
    enable_caching: bool = True
    enable_async_indexing: bool = True
    enable_telemetry: bool = False
    
    # Advanced settings
    embedding_batch_size: int = 32
    max_concurrent_requests: int = 10
    retry_attempts: int = 3
    backoff_factor: float = 1.5
    
    class Config:
        env_prefix = "KB_"
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> "KnowledgeBaseSettings":
        """Create settings from a dictionary."""
        return cls(**config_dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert settings to a dictionary."""
        return self.dict()
    
    def update(self, **kwargs) -> None:
        """Update settings with new values."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)


# Default configuration
default_config = {
    "chroma": {
        "collection_name": "knowledge_base",
        "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
        "persist_directory": "./data/chromadb"
    },
    "neo4j": {
        "uri": "neo4j://localhost:7687",
        "username": "neo4j",
        "password": "password",
        "database": "neo4j"
    },
    "search": {
        "default_limit": 10,
        "max_limit": 100,
        "min_confidence": 0.5,
        "max_search_depth": 3
    }
}
