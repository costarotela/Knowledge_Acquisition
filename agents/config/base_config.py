"""
Base configuration for all agents.
"""

from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from pathlib import Path

class AgentConfig(BaseModel):
    """Base configuration for any agent."""
    
    # Modo de operación
    mode: str = Field(
        default="standalone",
        description="Operation mode (standalone/orchestrated)"
    )
    
    # Recursos del sistema
    max_memory: str = Field(
        default="1GB",
        description="Maximum memory allocation"
    )
    max_cpu_percent: float = Field(
        default=80.0,
        description="Maximum CPU usage percentage"
    )
    
    # Configuración de logging
    log_level: str = Field(
        default="INFO",
        description="Logging level"
    )
    log_file: Optional[Path] = Field(
        default=None,
        description="Log file path"
    )
    
    # Timeouts y reintentos
    request_timeout: int = Field(
        default=30,
        description="Request timeout in seconds"
    )
    max_retries: int = Field(
        default=3,
        description="Maximum number of retries"
    )
    
    # Cache
    enable_cache: bool = Field(
        default=True,
        description="Enable result caching"
    )
    cache_ttl: int = Field(
        default=3600,
        description="Cache TTL in seconds"
    )
    
    # Orquestación
    orchestrator_url: Optional[str] = Field(
        default=None,
        description="Orchestrator URL when in orchestrated mode"
    )
    
    class Config:
        extra = "allow"  # Permite campos adicionales específicos del agente

def load_agent_config(
    agent_name: str,
    config_path: Optional[Path] = None,
    override: Optional[Dict[str, Any]] = None
) -> AgentConfig:
    """
    Load configuration for a specific agent.
    
    Args:
        agent_name: Name of the agent
        config_path: Optional path to config file
        override: Optional config overrides
    
    Returns:
        AgentConfig instance
    """
    # Implementar lógica de carga de configuración
    pass
