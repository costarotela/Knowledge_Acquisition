"""
API schemas for request/response models.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field

# Auth Models
class TokenRequest(BaseModel):
    """Token request model."""
    username: str
    password: str

class Token(BaseModel):
    """Token response model."""
    access_token: str
    token_type: str = "bearer"
    expires_at: datetime

# Task Models
class TaskRequest(BaseModel):
    """Task creation request."""
    task_type: str
    input_data: Any
    priority: Optional[str] = "normal"
    metadata: Dict[str, Any] = Field(default_factory=dict)

class TaskResponse(BaseModel):
    """Task response model."""
    task_id: str
    status: str
    created_at: datetime
    completed_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

# Agent Models
class AgentStatus(BaseModel):
    """Agent status model."""
    agent_id: str
    type: str
    status: str
    tasks_completed: int
    last_active: datetime
    config: Dict[str, Any]

# Pipeline Models
class PipelineStatus(BaseModel):
    """Pipeline status model."""
    pipeline_id: str
    status: str
    nodes: int
    tasks_pending: int
    tasks_completed: int
    node_states: Dict[str, Dict[str, Any]]

# Metric Models
class MetricValue(BaseModel):
    """Metric value model."""
    value: float
    timestamp: datetime
    labels: Dict[str, str] = Field(default_factory=dict)

class MetricData(BaseModel):
    """Metric data model."""
    name: str
    type: str
    description: str
    values: List[MetricValue]

# Alert Models
class AlertData(BaseModel):
    """Alert data model."""
    alert_id: str
    severity: str
    message: str
    timestamp: datetime
    acknowledged: bool = False

# WebSocket Models
class WSMessage(BaseModel):
    """WebSocket message model."""
    type: str
    data: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.now)

class WSRequest(BaseModel):
    """WebSocket request model."""
    action: str
    params: Dict[str, Any] = Field(default_factory=dict)

class WSResponse(BaseModel):
    """WebSocket response model."""
    status: str
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
