"""
Redis-based agent registry implementation.
"""
from typing import Dict, Any, List, Optional
import json
import logging
import redis.asyncio as redis
from datetime import datetime, timedelta

from ..base import Agent, AgentRegistry

logger = logging.getLogger(__name__)

class RedisAgentRegistry(AgentRegistry):
    """Agent registry implementation using Redis."""
    
    def __init__(
        self,
        redis_url: str,
        prefix: str = "agent_registry:",
        ttl: int = 3600  # 1 hour TTL for agent registrations
    ):
        """Initialize Redis agent registry."""
        self.redis = redis.from_url(redis_url)
        self.prefix = prefix
        self.ttl = ttl
    
    def _agent_key(self, agent_id: str) -> str:
        """Get Redis key for an agent."""
        return f"{self.prefix}agent:{agent_id}"
    
    def _type_key(self, task_type: str) -> str:
        """Get Redis key for a task type."""
        return f"{self.prefix}type:{task_type}"
    
    async def register_agent(self, agent: Agent) -> bool:
        """Register an agent in Redis."""
        try:
            # Store agent information
            agent_data = {
                "id": agent.agent_id,
                "status": agent.status,
                "config": agent.config,
                "registered_at": datetime.now().isoformat()
            }
            
            # Create pipeline for atomic operations
            async with self.redis.pipeline(transaction=True) as pipe:
                # Store agent data
                await pipe.setex(
                    self._agent_key(agent.agent_id),
                    self.ttl,
                    json.dumps(agent_data)
                )
                
                # Add agent to task type sets
                for task_type in agent.config.get("supported_tasks", []):
                    await pipe.sadd(
                        self._type_key(task_type),
                        agent.agent_id
                    )
                    await pipe.expire(
                        self._type_key(task_type),
                        self.ttl
                    )
                
                # Execute pipeline
                await pipe.execute()
            
            return True
            
        except Exception as e:
            logger.error(f"Error registering agent: {e}")
            return False
    
    async def unregister_agent(self, agent_id: str) -> bool:
        """Unregister an agent from Redis."""
        try:
            # Get agent data first
            agent_data = await self.redis.get(self._agent_key(agent_id))
            if not agent_data:
                return False
            
            agent_info = json.loads(agent_data)
            
            # Create pipeline for atomic operations
            async with self.redis.pipeline(transaction=True) as pipe:
                # Remove agent data
                await pipe.delete(self._agent_key(agent_id))
                
                # Remove from task type sets
                for task_type in agent_info.get("config", {}).get("supported_tasks", []):
                    await pipe.srem(
                        self._type_key(task_type),
                        agent_id
                    )
                
                # Execute pipeline
                await pipe.execute()
            
            return True
            
        except Exception as e:
            logger.error(f"Error unregistering agent: {e}")
            return False
    
    async def get_agent(self, agent_id: str) -> Optional[Agent]:
        """Get agent by ID from Redis."""
        try:
            agent_data = await self.redis.get(self._agent_key(agent_id))
            if not agent_data:
                return None
            
            # Parse agent data
            agent_info = json.loads(agent_data)
            
            # Refresh TTL
            await self.redis.expire(self._agent_key(agent_id), self.ttl)
            
            # Create agent instance
            # Note: This is a simplified version, in practice you'd need
            # to reconstruct the actual agent class
            return Agent(
                agent_id=agent_info["id"],
                config=agent_info["config"]
            )
            
        except Exception as e:
            logger.error(f"Error getting agent: {e}")
            return None
    
    async def get_available_agents(self, task_type: str) -> List[Agent]:
        """Get available agents for a task type from Redis."""
        try:
            # Get all agent IDs for task type
            agent_ids = await self.redis.smembers(self._type_key(task_type))
            
            agents = []
            for agent_id in agent_ids:
                agent = await self.get_agent(agent_id.decode())
                if agent and agent.status == "ready":
                    agents.append(agent)
            
            return agents
            
        except Exception as e:
            logger.error(f"Error getting available agents: {e}")
            return []
    
    async def cleanup_expired(self):
        """Cleanup expired agent registrations."""
        try:
            # Get all agent keys
            agent_keys = await self.redis.keys(f"{self.prefix}agent:*")
            
            for key in agent_keys:
                # Check if key is expired
                ttl = await self.redis.ttl(key)
                if ttl <= 0:
                    agent_id = key.decode().split(":")[-1]
                    await self.unregister_agent(agent_id)
            
        except Exception as e:
            logger.error(f"Error cleaning up expired registrations: {e}")
    
    async def heartbeat(self, agent_id: str) -> bool:
        """Update agent heartbeat."""
        try:
            # Check if agent exists
            if not await self.redis.exists(self._agent_key(agent_id)):
                return False
            
            # Refresh TTL
            await self.redis.expire(self._agent_key(agent_id), self.ttl)
            
            # Update last heartbeat time
            await self.redis.hset(
                self._agent_key(agent_id),
                "last_heartbeat",
                datetime.now().isoformat()
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating agent heartbeat: {e}")
            return False
