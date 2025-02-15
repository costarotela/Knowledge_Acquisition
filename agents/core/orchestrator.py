"""
Base implementation of the agent orchestrator.
"""

from typing import Dict, List, Optional, Type
from .base import BaseAgent, AgentMetadata, AgentMode
from ..config.base_config import AgentConfig
import asyncio
import logging
from pydantic import BaseModel

class AgentRegistry(BaseModel):
    """Registry of available agents."""
    
    agents: Dict[str, AgentMetadata] = {}
    instances: Dict[str, BaseAgent] = {}
    
    def register(self, agent: BaseAgent) -> bool:
        """Register a new agent."""
        metadata = agent.get_metadata()
        self.agents[metadata.name] = metadata
        self.instances[metadata.name] = agent
        return True
    
    def get_agent(self, name: str) -> Optional[BaseAgent]:
        """Get agent instance by name."""
        return self.instances.get(name)
    
    def list_agents(self) -> List[AgentMetadata]:
        """List all registered agents."""
        return list(self.agents.values())

class Orchestrator:
    """
    Manages and coordinates multiple agents.
    
    Responsibilities:
    1. Agent lifecycle management
    2. Inter-agent communication
    3. Resource allocation
    4. Error handling and recovery
    5. Task scheduling and prioritization
    """
    
    def __init__(self, config: Optional[AgentConfig] = None):
        self.config = config or AgentConfig()
        self.registry = AgentRegistry()
        self.logger = logging.getLogger(__name__)
    
    async def register_agent(self, agent: BaseAgent) -> bool:
        """Register a new agent with the orchestrator."""
        try:
            # Configurar el agente para modo orquestado
            agent.mode = AgentMode.ORCHESTRATED
            # Registrar el agente
            return self.registry.register(agent)
        except Exception as e:
            self.logger.error(f"Failed to register agent: {str(e)}")
            return False
    
    async def process_request(
        self,
        query: str,
        agent_name: Optional[str] = None,
        context: Optional[Dict] = None
    ) -> Dict:
        """
        Process a request using appropriate agent(s).
        
        If agent_name is provided, use that specific agent.
        Otherwise, determine the best agent(s) for the task.
        """
        try:
            if agent_name:
                agent = self.registry.get_agent(agent_name)
                if not agent:
                    raise ValueError(f"Agent not found: {agent_name}")
                return await agent.process_query(query, context)
            else:
                # Implementar lógica de selección de agente
                pass
        except Exception as e:
            self.logger.error(f"Error processing request: {str(e)}")
            raise
    
    async def coordinate_agents(
        self,
        task: Dict,
        agent_names: List[str]
    ) -> Dict:
        """Coordinate multiple agents to complete a complex task."""
        results = {}
        for name in agent_names:
            agent = self.registry.get_agent(name)
            if agent:
                try:
                    result = await agent.process_query(
                        task.get("query", ""),
                        task.get("context")
                    )
                    results[name] = result
                except Exception as e:
                    self.logger.error(f"Agent {name} failed: {str(e)}")
                    results[name] = {"error": str(e)}
        return results
    
    def get_agent_status(self, agent_name: str) -> Dict:
        """Get current status of an agent."""
        agent = self.registry.get_agent(agent_name)
        if not agent:
            raise ValueError(f"Agent not found: {agent_name}")
        
        metadata = agent.get_metadata()
        return {
            "name": metadata.name,
            "version": metadata.version,
            "status": "active",  # Implementar lógica de estado
            "capabilities": metadata.capabilities.dict()
        }
