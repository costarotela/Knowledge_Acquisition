"""
Configuration schemas for the knowledge acquisition system.
"""
from typing import Dict, Any, List, Optional
from enum import Enum
from pydantic import BaseModel, Field, SecretStr, validator
import os

class LogLevel(str, Enum):
    """Available logging levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"

class AgentMode(str, Enum):
    """Operating modes for agents."""
    STANDALONE = "standalone"
    COLLABORATIVE = "collaborative"
    SUPERVISED = "supervised"

class APIConfig(BaseModel):
    """API configuration and credentials."""
    openai_api_key: SecretStr
    github_token: Optional[SecretStr] = None
    google_api_key: Optional[SecretStr] = None
    
    @validator("*")
    def load_from_env(cls, v, field):
        """Load secrets from environment if not provided."""
        if v is None:
            env_val = os.getenv(field.name.upper())
            if env_val:
                return SecretStr(env_val)
        return v

class StorageConfig(BaseModel):
    """Storage configuration."""
    vector_store_path: str = Field(..., description="Path to vector store")
    knowledge_base_path: str = Field(..., description="Path to knowledge base")
    cache_dir: str = Field(..., description="Path to cache directory")
    max_cache_size: int = Field(default=1024, description="Max cache size in MB")

class ProcessingConfig(BaseModel):
    """Processing configuration."""
    batch_size: int = Field(default=32)
    max_workers: int = Field(default=4)
    timeout: int = Field(default=300)
    retry_attempts: int = Field(default=3)
    use_gpu: bool = Field(default=True)

class MonitoringConfig(BaseModel):
    """Monitoring and logging configuration."""
    log_level: LogLevel = Field(default=LogLevel.INFO)
    log_file: str = Field(default="knowledge_acquisition.log")
    enable_metrics: bool = Field(default=True)
    metrics_port: int = Field(default=9090)
    enable_tracing: bool = Field(default=False)

class AgentConfig(BaseModel):
    """Base configuration for agents."""
    name: str
    mode: AgentMode = Field(default=AgentMode.COLLABORATIVE)
    enabled: bool = Field(default=True)
    max_concurrent_tasks: int = Field(default=5)
    task_timeout: int = Field(default=600)
    retry_policy: Dict[str, Any] = Field(default_factory=dict)

class YouTubeAgentConfig(AgentConfig):
    """YouTube agent specific configuration."""
    max_videos: int = Field(default=100)
    download_path: str
    supported_formats: List[str] = Field(default=["mp4", "webm"])
    extract_captions: bool = Field(default=True)

class WebResearchAgentConfig(AgentConfig):
    """Web research agent specific configuration."""
    max_depth: int = Field(default=3)
    max_pages: int = Field(default=50)
    request_delay: float = Field(default=1.0)
    excluded_domains: List[str] = Field(default_factory=list)

class GitHubAgentConfig(AgentConfig):
    """GitHub agent specific configuration."""
    max_repos: int = Field(default=10)
    max_files: int = Field(default=1000)
    analyze_commits: bool = Field(default=True)
    excluded_files: List[str] = Field(default_factory=list)

class RAGAgentConfig(AgentConfig):
    """RAG agent specific configuration."""
    model_name: str = Field(default="gpt-4")
    max_documents: int = Field(default=5)
    temperature: float = Field(default=0.7)
    max_tokens: int = Field(default=2000)

class SystemConfig(BaseModel):
    """Complete system configuration."""
    api: APIConfig
    storage: StorageConfig
    processing: ProcessingConfig
    monitoring: MonitoringConfig
    agents: Dict[str, AgentConfig] = Field(default_factory=dict)
    
    @validator("agents")
    def validate_agent_configs(cls, v):
        """Validate agent configurations."""
        agent_types = {
            "youtube": YouTubeAgentConfig,
            "web_research": WebResearchAgentConfig,
            "github": GitHubAgentConfig,
            "rag": RAGAgentConfig
        }
        
        validated = {}
        for name, config in v.items():
            agent_type = name.split("_")[0]
            if agent_type in agent_types:
                if isinstance(config, dict):
                    config = agent_types[agent_type](**config)
                validated[name] = config
            else:
                validated[name] = config
        
        return validated
