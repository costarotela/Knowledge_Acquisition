"""
Celery-based task queue implementation.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
import json
import logging
from celery import Celery
from celery.result import AsyncResult

from ..base import Task, TaskStatus, TaskQueue

logger = logging.getLogger(__name__)

class CeleryTaskQueue(TaskQueue):
    """Task queue implementation using Celery."""
    
    def __init__(
        self,
        broker_url: str,
        backend_url: str,
        queue_name: str = "knowledge_tasks"
    ):
        """Initialize Celery task queue."""
        self.app = Celery(
            "knowledge_acquisition",
            broker=broker_url,
            backend=backend_url
        )
        
        self.queue_name = queue_name
        self._configure_celery()
    
    def _configure_celery(self):
        """Configure Celery settings."""
        self.app.conf.update(
            task_serializer="json",
            accept_content=["json"],
            result_serializer="json",
            enable_utc=True,
            task_track_started=True,
            task_routes={
                "process_task": {"queue": self.queue_name}
            },
            task_annotations={
                "process_task": {
                    "rate_limit": "10/m"
                }
            }
        )
        
        # Register task processor
        @self.app.task(name="process_task", bind=True)
        def process_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
            """Process a task through Celery."""
            try:
                # Convert task data back to Task object
                task = Task(**task_data)
                
                # Update task status
                task.status = TaskStatus.RUNNING
                task.started_at = datetime.now()
                
                # Here we would normally process the task
                # For now, just return success
                return {
                    "task_id": task.id,
                    "status": TaskStatus.COMPLETED,
                    "completed_at": datetime.now().isoformat()
                }
                
            except Exception as e:
                logger.error(f"Error processing task: {e}")
                return {
                    "task_id": task_data.get("id"),
                    "status": TaskStatus.FAILED,
                    "error": str(e)
                }
    
    async def push(self, task: Task) -> bool:
        """Push a task to the Celery queue."""
        try:
            # Convert Task to dict for serialization
            task_data = json.loads(task.json())
            
            # Send task to Celery
            celery_task = self.app.send_task(
                "process_task",
                args=[task_data],
                queue=self.queue_name
            )
            
            # Store Celery task ID in task metadata
            task.metadata["celery_task_id"] = celery_task.id
            return True
            
        except Exception as e:
            logger.error(f"Error pushing task to queue: {e}")
            return False
    
    async def pop(self) -> Optional[Task]:
        """
        Pop next task from the queue.
        Note: In Celery, tasks are automatically distributed to workers,
        so this method is mainly for testing/monitoring.
        """
        try:
            # Get all active tasks
            inspector = self.app.control.inspect()
            active_tasks = inspector.active()
            
            if not active_tasks:
                return None
            
            # Get first task from first worker
            for worker_tasks in active_tasks.values():
                if worker_tasks:
                    task_data = worker_tasks[0]
                    return Task(**json.loads(task_data["kwargs"]["task_data"]))
            
            return None
            
        except Exception as e:
            logger.error(f"Error popping task from queue: {e}")
            return None
    
    async def get_status(self, task_id: str) -> Optional[TaskStatus]:
        """Get status of a Celery task."""
        try:
            task = await self.get_task(task_id)
            if not task:
                return None
            
            celery_task_id = task.metadata.get("celery_task_id")
            if not celery_task_id:
                return None
            
            # Get Celery task status
            result = AsyncResult(celery_task_id, app=self.app)
            
            # Map Celery status to our TaskStatus
            status_map = {
                "PENDING": TaskStatus.PENDING,
                "STARTED": TaskStatus.RUNNING,
                "SUCCESS": TaskStatus.COMPLETED,
                "FAILURE": TaskStatus.FAILED,
                "REVOKED": TaskStatus.CANCELLED
            }
            
            return status_map.get(result.status, TaskStatus.PENDING)
            
        except Exception as e:
            logger.error(f"Error getting task status: {e}")
            return None
    
    async def update_status(self, task_id: str, status: TaskStatus) -> bool:
        """Update status of a task."""
        try:
            task = await self.get_task(task_id)
            if not task:
                return False
            
            celery_task_id = task.metadata.get("celery_task_id")
            if not celery_task_id:
                return False
            
            # Update task status in Celery
            result = AsyncResult(celery_task_id, app=self.app)
            
            if status == TaskStatus.CANCELLED:
                result.revoke(terminate=True)
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating task status: {e}")
            return False
    
    async def get_task(self, task_id: str) -> Optional[Task]:
        """Get task by ID."""
        try:
            # Get all tasks
            inspector = self.app.control.inspect()
            
            # Check different task states
            states = {
                "active": inspector.active(),
                "reserved": inspector.reserved(),
                "scheduled": inspector.scheduled()
            }
            
            # Search for task in all states
            for state_tasks in states.values():
                if not state_tasks:
                    continue
                
                for worker_tasks in state_tasks.values():
                    for task_data in worker_tasks:
                        if task_data["id"] == task_id:
                            return Task(**json.loads(task_data["kwargs"]["task_data"]))
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting task: {e}")
            return None
