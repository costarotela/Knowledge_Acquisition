"""
Base interfaces and classes for all agents in the system.
"""

from abc import ABC, abstractmethod
from typing import Dict, Optional, Any, List
from enum import Enum
from pydantic import BaseModel, Field

class AgentMode(str, Enum):
    STANDALONE = "standalone"
    ORCHESTRATED = "orchestrated"

class AgentCapabilities(BaseModel):
    """Define what an agent can do independently."""
    
    interfaces: List[str] = Field(
        default=["cli"],
        description="Available interfaces (cli, api, ui)"
    )
    supported_formats: List[str] = Field(
        default=["json"],
        description="Supported data formats"
    )
    can_run_standalone: bool = Field(
        default=True,
        description="Can operate without orchestrator"
    )
    required_resources: Dict[str, str] = Field(
        default_factory=dict,
        description="Required system resources"
    )

class AgentMetadata(BaseModel):
    """Metadata for agent discovery and management."""
    
    name: str
    version: str
    description: str
    capabilities: AgentCapabilities
    required_credentials: List[str] = Field(default_factory=list)
    supported_languages: List[str] = Field(default=["en"])
    dependencies: Dict[str, str] = Field(default_factory=dict)

class BaseAgent(ABC):
    """Base class for all agents in the system."""
    
    def __init__(
        self,
        mode: AgentMode = AgentMode.STANDALONE,
        knowledge_base: Optional[Any] = None,
        config: Optional[Dict] = None
    ):
        self.mode = mode
        self.knowledge_base = knowledge_base
        self.config = config or {}
        self._validate_setup()
    
    @abstractmethod
    def get_metadata(self) -> AgentMetadata:
        """Get agent metadata for discovery."""
        pass
    
    @abstractmethod
    async def process_query(self, query: str, context: Optional[Dict] = None) -> Dict:
        """Process a user query."""
        pass
    
    @abstractmethod
    async def update_knowledge(self, data: Dict) -> bool:
        """Update agent's knowledge."""
        pass
    
    def _validate_setup(self):
        """Validate agent setup based on mode."""
        if self.mode == AgentMode.ORCHESTRATED:
            if not self.knowledge_base:
                raise ValueError("Knowledge base required in orchestrated mode")
            self._validate_orchestration()
    
    def _validate_orchestration(self):
        """Validate orchestration requirements."""
        metadata = self.get_metadata()
        for cred in metadata.required_credentials:
            if cred not in self.config:
                raise ValueError(f"Missing required credential: {cred}")

class OrchestrationCapable(ABC):
    """Interface for agents that can be orchestrated."""
    
    @abstractmethod
    async def register_with_orchestrator(self) -> bool:
        """Register agent with orchestrator."""
        pass
    
    @abstractmethod
    async def handle_orchestrator_request(self, request: Dict) -> Dict:
        """Handle orchestrator requests."""
        pass
    
    @abstractmethod
    async def collaborate(self, agent_name: str, query: Dict) -> Dict:
        """Collaborate with another agent."""
        pass
