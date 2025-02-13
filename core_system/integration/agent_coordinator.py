"""
Agent coordination and integration system.
"""
from typing import Dict, Any, List, Optional
import logging
import asyncio
from datetime import datetime

from pydantic import BaseModel

from ..agent_orchestrator.base import Task, TaskResult
from ...config.schemas import SystemConfig, AgentConfig
from ...agents.base_agents.knowledge_agent import KnowledgeAgent

logger = logging.getLogger(__name__)

class AgentCoordinator:
    """Coordinates interactions between different agents."""
    
    def __init__(self, config: SystemConfig):
        """Initialize coordinator with system configuration."""
        self.config = config
        self.agents: Dict[str, KnowledgeAgent] = {}
        self.active_tasks: Dict[str, Task] = {}
        self.task_results: Dict[str, TaskResult] = {}
    
    async def register_agent(
        self,
        agent_id: str,
        agent: KnowledgeAgent
    ) -> bool:
        """Register an agent with the coordinator."""
        try:
            if agent_id in self.agents:
                logger.warning(f"Agent {agent_id} already registered")
                return False
            
            # Initialize agent
            success = await agent.initialize()
            if not success:
                logger.error(f"Failed to initialize agent {agent_id}")
                return False
            
            self.agents[agent_id] = agent
            logger.info(f"Successfully registered agent {agent_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error registering agent {agent_id}: {e}")
            return False
    
    async def unregister_agent(self, agent_id: str) -> bool:
        """Unregister an agent."""
        try:
            if agent_id not in self.agents:
                logger.warning(f"Agent {agent_id} not found")
                return False
            
            # Cleanup agent
            agent = self.agents[agent_id]
            await agent.cleanup()
            
            del self.agents[agent_id]
            logger.info(f"Successfully unregistered agent {agent_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error unregistering agent {agent_id}: {e}")
            return False
    
    async def submit_task(
        self,
        task: Task,
        agent_ids: Optional[List[str]] = None
    ) -> str:
        """Submit a task to specific agents or let coordinator decide."""
        try:
            if not agent_ids:
                # Auto-select agents based on task type
                agent_ids = self._select_agents_for_task(task)
            
            if not agent_ids:
                raise ValueError("No suitable agents found for task")
            
            # Create subtasks for each agent
            subtasks = []
            for agent_id in agent_ids:
                if agent_id not in self.agents:
                    logger.warning(f"Agent {agent_id} not found")
                    continue
                
                subtask = self._create_subtask(task, agent_id)
                subtasks.append(subtask)
            
            # Submit subtasks
            results = await asyncio.gather(
                *[self._execute_subtask(subtask) for subtask in subtasks],
                return_exceptions=True
            )
            
            # Combine results
            combined_result = self._combine_results(results)
            self.task_results[task.id] = combined_result
            
            return task.id
            
        except Exception as e:
            logger.error(f"Error submitting task: {e}")
            return None
    
    async def get_task_result(self, task_id: str) -> Optional[TaskResult]:
        """Get the result of a task."""
        return self.task_results.get(task_id)
    
    def _select_agents_for_task(self, task: Task) -> List[str]:
        """Select appropriate agents based on task type and requirements."""
        selected = []
        
        # Map task types to agent capabilities
        task_type = task.task_type.lower()
        type_mapping = {
            "video": ["youtube"],
            "web": ["web_research"],
            "code": ["github"],
            "knowledge": ["rag"],
            "research": ["web_research", "rag"],
            "analysis": ["rag", "github"]
        }
        
        # Get potential agent types
        agent_types = []
        for key, types in type_mapping.items():
            if key in task_type:
                agent_types.extend(types)
        
        # Select agents of matching types
        for agent_id, agent in self.agents.items():
            agent_type = agent_id.split("_")[0]
            if agent_type in agent_types:
                selected.append(agent_id)
        
        return selected
    
    def _create_subtask(self, task: Task, agent_id: str) -> Task:
        """Create a subtask for a specific agent."""
        return Task(
            id=f"{task.id}_{agent_id}",
            task_type=task.task_type,
            input_data=task.input_data,
            parent_id=task.id,
            agent_id=agent_id,
            priority=task.priority,
            deadline=task.deadline
        )
    
    async def _execute_subtask(self, task: Task) -> TaskResult:
        """Execute a subtask on the specified agent."""
        try:
            agent = self.agents[task.agent_id]
            
            # Check agent availability
            if not self._check_agent_availability(agent, task):
                return TaskResult(
                    success=False,
                    error=f"Agent {task.agent_id} not available"
                )
            
            # Execute task
            self.active_tasks[task.id] = task
            result = await agent.process_task(task)
            del self.active_tasks[task.id]
            
            return result
            
        except Exception as e:
            logger.error(f"Error executing subtask {task.id}: {e}")
            return TaskResult(
                success=False,
                error=str(e)
            )
    
    def _check_agent_availability(
        self,
        agent: KnowledgeAgent,
        task: Task
    ) -> bool:
        """Check if agent is available for task."""
        # Get agent config
        agent_config = self.config.agents.get(agent.agent_id)
        if not agent_config:
            return False
        
        # Check if agent is enabled
        if not agent_config.enabled:
            return False
        
        # Check concurrent tasks
        agent_tasks = [
            t for t in self.active_tasks.values()
            if t.agent_id == agent.agent_id
        ]
        if len(agent_tasks) >= agent_config.max_concurrent_tasks:
            return False
        
        return True
    
    def _combine_results(
        self,
        results: List[TaskResult]
    ) -> TaskResult:
        """Combine results from multiple agents."""
        # Filter out exceptions
        valid_results = [
            r for r in results
            if isinstance(r, TaskResult)
        ]
        
        if not valid_results:
            return TaskResult(
                success=False,
                error="All subtasks failed"
            )
        
        # Combine successful results
        successful = [r for r in valid_results if r.success]
        if not successful:
            return TaskResult(
                success=False,
                error="All subtasks failed: " + 
                      "; ".join(r.error for r in valid_results)
            )
        
        # Merge data and metrics
        combined_data = {}
        combined_metrics = {}
        
        for result in successful:
            if result.data:
                combined_data.update(result.data)
            if result.metrics:
                for key, value in result.metrics.items():
                    if key in combined_metrics:
                        if isinstance(value, (int, float)):
                            combined_metrics[key] += value
                        else:
                            combined_metrics[key] = value
                    else:
                        combined_metrics[key] = value
        
        return TaskResult(
            success=True,
            data=combined_data,
            metrics=combined_metrics
        )
