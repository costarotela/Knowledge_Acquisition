"""
Base classes for the agent orchestration system.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from enum import Enum
from datetime import datetime
from pydantic import BaseModel, Field
import uuid

class TaskStatus(str, Enum):
    """Status of a task in the system."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class TaskPriority(int, Enum):
    """Priority levels for tasks."""
    LOW = 0
    MEDIUM = 1
    HIGH = 2
    CRITICAL = 3

class TaskResult(BaseModel):
    """Result of a task execution."""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    metrics: Dict[str, float] = Field(default_factory=dict)
    artifacts: Dict[str, str] = Field(default_factory=dict)

class Task(BaseModel):
    """Base class for all tasks in the system."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: str
    priority: TaskPriority = TaskPriority.MEDIUM
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    input_data: Dict[str, Any] = Field(default_factory=dict)
    result: Optional[TaskResult] = None
    agent_id: Optional[str] = None
    parent_task_id: Optional[str] = None
    subtasks: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

class Agent(ABC):
    """Base class for all agents in the system."""
    
    def __init__(self, agent_id: str, config: Dict[str, Any]):
        """Initialize the agent."""
        self.agent_id = agent_id
        self.config = config
        self.status = "initialized"
    
    @abstractmethod
    async def process_task(self, task: Task) -> TaskResult:
        """Process a task assigned to this agent."""
        pass
    
    @abstractmethod
    async def can_handle_task(self, task: Task) -> bool:
        """Check if this agent can handle the given task."""
        pass
    
    async def initialize(self) -> bool:
        """Initialize agent resources."""
        try:
            self.status = "ready"
            return True
        except Exception:
            self.status = "failed"
            return False
    
    async def cleanup(self):
        """Cleanup agent resources."""
        self.status = "stopped"

class TaskQueue(ABC):
    """Abstract base class for task queues."""
    
    @abstractmethod
    async def push(self, task: Task) -> bool:
        """Push a task to the queue."""
        pass
    
    @abstractmethod
    async def pop(self) -> Optional[Task]:
        """Pop next task from the queue."""
        pass
    
    @abstractmethod
    async def get_status(self, task_id: str) -> Optional[TaskStatus]:
        """Get status of a task."""
        pass
    
    @abstractmethod
    async def update_status(self, task_id: str, status: TaskStatus) -> bool:
        """Update status of a task."""
        pass
    
    @abstractmethod
    async def get_task(self, task_id: str) -> Optional[Task]:
        """Get task by ID."""
        pass

class AgentRegistry(ABC):
    """Abstract base class for agent registry."""
    
    @abstractmethod
    async def register_agent(self, agent: Agent) -> bool:
        """Register an agent in the system."""
        pass
    
    @abstractmethod
    async def unregister_agent(self, agent_id: str) -> bool:
        """Unregister an agent from the system."""
        pass
    
    @abstractmethod
    async def get_agent(self, agent_id: str) -> Optional[Agent]:
        """Get agent by ID."""
        pass
    
    @abstractmethod
    async def get_available_agents(self, task_type: str) -> List[Agent]:
        """Get available agents that can handle a task type."""
        pass
