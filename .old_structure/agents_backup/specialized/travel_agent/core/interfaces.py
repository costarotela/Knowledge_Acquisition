"""
Interfaces for both standalone and orchestrated operation modes.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any, Union
from datetime import datetime
from pydantic import BaseModel

class AgentMode(str, enum.Enum):
    STANDALONE = "standalone"
    ORCHESTRATED = "orchestrated"

class AgentInterface(ABC):
    """Base interface that all agents must implement."""
    
    @abstractmethod
    async def process_query(self, query: str, context: Optional[Dict] = None) -> Dict:
        """Process a natural language query."""
        pass
    
    @abstractmethod
    async def update_knowledge(self, data: Dict) -> bool:
        """Update agent's knowledge base."""
        pass

class StandaloneCapabilities(BaseModel):
    """Capabilities available in standalone mode."""
    
    has_cli: bool = False
    has_api: bool = False
    has_ui: bool = False
    supported_formats: List[str] = ["json", "text"]

class AgentMetadata(BaseModel):
    """Metadata about the agent's capabilities and requirements."""
    
    name: str
    version: str
    description: str
    standalone_capabilities: StandaloneCapabilities
    required_credentials: List[str]
    supported_languages: List[str]
    dependencies: Dict[str, str]

class BaseSpecializedAgent(AgentInterface):
    """Base class for all specialized agents."""
    
    def __init__(
        self,
        mode: AgentMode = AgentMode.STANDALONE,
        knowledge_base: Optional[Any] = None,
        config: Optional[Dict] = None
    ):
        self.mode = mode
        self.knowledge_base = knowledge_base
        self.config = config or {}
        self._validate_config()
        
    @abstractmethod
    def get_metadata(self) -> AgentMetadata:
        """Get agent metadata."""
        pass
    
    def _validate_config(self):
        """Validate agent configuration."""
        if self.mode == AgentMode.ORCHESTRATED and not self.knowledge_base:
            raise ValueError("Knowledge base is required in orchestrated mode")
    
    async def collaborate(self, agent_name: str, query: Dict) -> Dict:
        """Collaborate with another agent when in orchestrated mode."""
        if self.mode != AgentMode.ORCHESTRATED:
            raise RuntimeError("Collaboration only available in orchestrated mode")
        # Implementation provided by orchestrator
        pass

class OrchestratorInterface(ABC):
    """Interface for agent orchestrator integration."""
    
    @abstractmethod
    async def register_with_orchestrator(self) -> bool:
        """Register agent capabilities with orchestrator."""
        pass
    
    @abstractmethod
    async def handle_orchestrator_request(self, request: Dict) -> Dict:
        """Handle requests from the orchestrator."""
        pass
