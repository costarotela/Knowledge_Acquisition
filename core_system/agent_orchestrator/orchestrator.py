"""
Main orchestrator for coordinating agents and tasks.
"""
from typing import Dict, Any, List, Optional, Type
import logging
import asyncio
from datetime import datetime

from .base import (
    Agent, Task, TaskStatus, TaskResult,
    TaskQueue, AgentRegistry
)
from ..knowledge_base.unified_store import UnifiedKnowledgeStore
from ..multimodal_processor.unified_processor import UnifiedProcessor

logger = logging.getLogger(__name__)

class AgentOrchestrator:
    """
    Coordinates task execution and agent management.
    
    This orchestrator:
    1. Manages task lifecycle
    2. Coordinates agent registration and discovery
    3. Handles task distribution and load balancing
    4. Monitors task execution and handles failures
    5. Integrates with knowledge base and processors
    """
    
    def __init__(
        self,
        task_queue: TaskQueue,
        agent_registry: AgentRegistry,
        knowledge_store: UnifiedKnowledgeStore,
        processor: UnifiedProcessor,
        config: Dict[str, Any]
    ):
        """Initialize orchestrator."""
        self.task_queue = task_queue
        self.agent_registry = agent_registry
        self.knowledge_store = knowledge_store
        self.processor = processor
        self.config = config
        
        self.running = False
        self._tasks: Dict[str, Task] = {}
        self._agent_tasks: Dict[str, List[str]] = {}
    
    async def start(self):
        """Start the orchestrator."""
        if self.running:
            return
        
        self.running = True
        logger.info("Starting agent orchestrator")
        
        # Start background tasks
        self._task_monitor = asyncio.create_task(self._monitor_tasks())
        self._agent_monitor = asyncio.create_task(self._monitor_agents())
    
    async def stop(self):
        """Stop the orchestrator."""
        if not self.running:
            return
        
        self.running = False
        logger.info("Stopping agent orchestrator")
        
        # Cancel background tasks
        self._task_monitor.cancel()
        self._agent_monitor.cancel()
        
        try:
            await self._task_monitor
            await self._agent_monitor
        except asyncio.CancelledError:
            pass
    
    async def submit_task(self, task: Task) -> bool:
        """Submit a new task for processing."""
        try:
            # Validate task
            if not self._validate_task(task):
                return False
            
            # Store task
            self._tasks[task.id] = task
            
            # Push to queue
            success = await self.task_queue.push(task)
            if not success:
                del self._tasks[task.id]
                return False
            
            logger.info(f"Submitted task {task.id} of type {task.type}")
            return True
            
        except Exception as e:
            logger.error(f"Error submitting task: {e}")
            return False
    
    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a running task."""
        try:
            task = self._tasks.get(task_id)
            if not task:
                return False
            
            # Update task status
            success = await self.task_queue.update_status(
                task_id,
                TaskStatus.CANCELLED
            )
            
            if success:
                task.status = TaskStatus.CANCELLED
                task.completed_at = datetime.now()
            
            return success
            
        except Exception as e:
            logger.error(f"Error cancelling task: {e}")
            return False
    
    async def get_task_status(self, task_id: str) -> Optional[TaskStatus]:
        """Get current status of a task."""
        try:
            return await self.task_queue.get_status(task_id)
        except Exception as e:
            logger.error(f"Error getting task status: {e}")
            return None
    
    async def register_agent(self, agent: Agent) -> bool:
        """Register a new agent."""
        try:
            # Initialize agent
            success = await agent.initialize()
            if not success:
                return False
            
            # Register with registry
            success = await self.agent_registry.register_agent(agent)
            if not success:
                await agent.cleanup()
                return False
            
            self._agent_tasks[agent.agent_id] = []
            return True
            
        except Exception as e:
            logger.error(f"Error registering agent: {e}")
            return False
    
    async def unregister_agent(self, agent_id: str) -> bool:
        """Unregister an agent."""
        try:
            # Get agent
            agent = await self.agent_registry.get_agent(agent_id)
            if not agent:
                return False
            
            # Cleanup agent
            await agent.cleanup()
            
            # Remove from registry
            success = await self.agent_registry.unregister_agent(agent_id)
            if success:
                self._agent_tasks.pop(agent_id, None)
            
            return success
            
        except Exception as e:
            logger.error(f"Error unregistering agent: {e}")
            return False
    
    def _validate_task(self, task: Task) -> bool:
        """Validate task parameters."""
        try:
            # Check required fields
            if not task.type or not task.input_data:
                return False
            
            # Check if task type is supported
            if task.type not in self.config.get("supported_task_types", []):
                return False
            
            return True
            
        except Exception:
            return False
    
    async def _monitor_tasks(self):
        """Monitor task execution and handle failures."""
        while self.running:
            try:
                # Check all active tasks
                for task_id, task in list(self._tasks.items()):
                    if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                        continue
                    
                    # Get current status
                    status = await self.task_queue.get_status(task_id)
                    if not status:
                        continue
                    
                    # Handle status changes
                    if status != task.status:
                        task.status = status
                        
                        if status == TaskStatus.COMPLETED:
                            task.completed_at = datetime.now()
                            
                            # Process results
                            await self._process_task_results(task)
                        
                        elif status == TaskStatus.FAILED:
                            # Handle failure
                            await self._handle_task_failure(task)
                
                await asyncio.sleep(self.config.get("task_monitor_interval", 5))
                
            except Exception as e:
                logger.error(f"Error in task monitor: {e}")
                await asyncio.sleep(1)
    
    async def _monitor_agents(self):
        """Monitor agent health and handle failures."""
        while self.running:
            try:
                # Cleanup expired registrations
                await self.agent_registry.cleanup_expired()
                
                # Check agent health
                for agent_id in list(self._agent_tasks.keys()):
                    agent = await self.agent_registry.get_agent(agent_id)
                    if not agent or agent.status != "ready":
                        # Handle agent failure
                        await self._handle_agent_failure(agent_id)
                
                await asyncio.sleep(self.config.get("agent_monitor_interval", 30))
                
            except Exception as e:
                logger.error(f"Error in agent monitor: {e}")
                await asyncio.sleep(1)
    
    async def _process_task_results(self, task: Task):
        """Process and store task results."""
        try:
            if not task.result:
                return
            
            # Store results in knowledge base
            if task.result.data:
                await self.knowledge_store.store_task_results(
                    task.id,
                    task.result.data
                )
            
            # Process any artifacts
            if task.result.artifacts:
                for artifact_type, artifact_path in task.result.artifacts.items():
                    await self.processor.process(artifact_path)
            
        except Exception as e:
            logger.error(f"Error processing task results: {e}")
    
    async def _handle_task_failure(self, task: Task):
        """Handle task failure."""
        try:
            # Log failure
            logger.error(f"Task {task.id} failed: {task.result.error if task.result else 'Unknown error'}")
            
            # Retry if possible
            if task.metadata.get("retry_count", 0) < self.config.get("max_retries", 3):
                task.metadata["retry_count"] = task.metadata.get("retry_count", 0) + 1
                task.status = TaskStatus.PENDING
                await self.task_queue.push(task)
            
        except Exception as e:
            logger.error(f"Error handling task failure: {e}")
    
    async def _handle_agent_failure(self, agent_id: str):
        """Handle agent failure."""
        try:
            # Get tasks assigned to agent
            tasks = self._agent_tasks.get(agent_id, [])
            
            # Reassign tasks
            for task_id in tasks:
                task = self._tasks.get(task_id)
                if task and task.status == TaskStatus.RUNNING:
                    task.status = TaskStatus.PENDING
                    task.agent_id = None
                    await self.task_queue.push(task)
            
            # Unregister agent
            await self.unregister_agent(agent_id)
            
        except Exception as e:
            logger.error(f"Error handling agent failure: {e}")
    
    @classmethod
    def from_config(
        cls,
        config_path: str,
        task_queue_cls: Type[TaskQueue],
        agent_registry_cls: Type[AgentRegistry]
    ) -> 'AgentOrchestrator':
        """Create orchestrator from configuration file."""
        import yaml
        
        with open(config_path) as f:
            config = yaml.safe_load(f)
        
        # Initialize components
        task_queue = task_queue_cls(**config["task_queue"])
        agent_registry = agent_registry_cls(**config["agent_registry"])
        knowledge_store = UnifiedKnowledgeStore.from_config(config["knowledge_store"])
        processor = UnifiedProcessor.from_config_file(config["processor"])
        
        return cls(
            task_queue=task_queue,
            agent_registry=agent_registry,
            knowledge_store=knowledge_store,
            processor=processor,
            config=config["orchestrator"]
        )
