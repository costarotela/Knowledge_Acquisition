"""
FastAPI application for knowledge acquisition system.
"""
from typing import List, Dict, Any
from fastapi import FastAPI, WebSocket, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import asyncio
from datetime import datetime

from .schemas import (
    TokenRequest, Token, TaskRequest, TaskResponse,
    AgentStatus, PipelineStatus, MetricData, AlertData,
    WSMessage, WSRequest, WSResponse
)
from .auth import AuthHandler, RoleChecker
from core_system.integration.agent_coordinator import AgentCoordinator
from core_system.pipeline.processor import PipelineProcessor
from core_system.monitoring.monitor import MonitoringSystem
from config.schemas import SystemConfig

app = FastAPI(
    title="Knowledge Acquisition API",
    description="API for knowledge acquisition system",
    version="1.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize systems
config = SystemConfig.from_yaml("config/config.yaml")
auth_handler = AuthHandler(config)
coordinator = AgentCoordinator(config)
processor = PipelineProcessor(config, coordinator)
monitoring = MonitoringSystem(config.monitoring)

# Role checkers
admin_role = RoleChecker(["admin"])
user_role = RoleChecker(["user", "admin"])

# WebSocket connections
ws_connections: Dict[str, WebSocket] = {}

# Auth endpoints
@app.post("/auth/token", response_model=Token)
async def login(request: TokenRequest):
    """Get authentication token."""
    # TODO: Validate against user database
    if request.username == "admin" and request.password == "admin":
        token = auth_handler.create_access_token(request.username)
        return Token(
            access_token=token,
            expires_at=datetime.utcnow()
        )
    raise HTTPException(
        status_code=401,
        detail="Invalid credentials"
    )

# Task endpoints
@app.post("/tasks", response_model=TaskResponse)
async def create_task(
    request: TaskRequest,
    username: str = Depends(user_role)
):
    """Create a new task."""
    task = coordinator.create_task(
        task_type=request.task_type,
        input_data=request.input_data,
        metadata={
            **request.metadata,
            "created_by": username
        }
    )
    
    # Process task asynchronously
    asyncio.create_task(coordinator.process_task(task))
    
    return TaskResponse(
        task_id=task.id,
        status=task.status.value,
        created_at=task.created_at
    )

@app.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: str,
    username: str = Depends(user_role)
):
    """Get task status and result."""
    task = coordinator.get_task(task_id)
    if not task:
        raise HTTPException(
            status_code=404,
            detail="Task not found"
        )
    
    return TaskResponse(
        task_id=task.id,
        status=task.status.value,
        created_at=task.created_at,
        completed_at=task.completed_at,
        result=task.result,
        error=task.error
    )

# Agent endpoints
@app.get("/agents", response_model=List[AgentStatus])
async def list_agents(username: str = Depends(user_role)):
    """List all registered agents."""
    return [
        AgentStatus(
            agent_id=agent_id,
            type=agent.__class__.__name__,
            status=agent.state.value,
            tasks_completed=agent.tasks_completed,
            last_active=agent.last_active,
            config=agent.config.dict()
        )
        for agent_id, agent in coordinator.agents.items()
    ]

@app.get("/agents/{agent_id}", response_model=AgentStatus)
async def get_agent(
    agent_id: str,
    username: str = Depends(user_role)
):
    """Get agent status."""
    agent = coordinator.get_agent(agent_id)
    if not agent:
        raise HTTPException(
            status_code=404,
            detail="Agent not found"
        )
    
    return AgentStatus(
        agent_id=agent_id,
        type=agent.__class__.__name__,
        status=agent.state.value,
        tasks_completed=agent.tasks_completed,
        last_active=agent.last_active,
        config=agent.config.dict()
    )

# Pipeline endpoints
@app.get("/pipelines", response_model=List[PipelineStatus])
async def list_pipelines(username: str = Depends(user_role)):
    """List all registered pipelines."""
    return [
        PipelineStatus(
            pipeline_id=pipeline_id,
            status=processor.get_pipeline_state(pipeline_id).status,
            nodes=len(pipeline.nodes),
            tasks_pending=len(processor.get_pipeline_state(pipeline_id).pending_tasks),
            tasks_completed=len(processor.get_pipeline_state(pipeline_id).completed_tasks),
            node_states={
                node.node_id: processor.get_pipeline_state(pipeline_id).node_states[node.node_id].dict()
                for node in pipeline.nodes
            }
        )
        for pipeline_id, pipeline in processor.pipelines.items()
    ]

# Monitoring endpoints
@app.get("/metrics", response_model=List[MetricData])
async def get_metrics(username: str = Depends(user_role)):
    """Get system metrics."""
    return [
        MetricData(
            name=name,
            type=metric.type.value,
            description=metric.description,
            values=[
                MetricValue(
                    value=v.value,
                    timestamp=v.timestamp,
                    labels=v.labels
                )
                for v in metric.values
            ]
        )
        for name, metric in monitoring.metrics.items()
    ]

@app.get("/alerts", response_model=List[AlertData])
async def get_alerts(username: str = Depends(user_role)):
    """Get active alerts."""
    return [
        AlertData(
            alert_id=alert.alert_id,
            severity=alert.severity.value,
            message=alert.message,
            timestamp=alert.timestamp,
            acknowledged=alert.acknowledged
        )
        for alert in monitoring.active_alerts.values()
    ]

# WebSocket endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket connection for real-time updates."""
    await websocket.accept()
    
    try:
        # Register connection
        client_id = str(id(websocket))
        ws_connections[client_id] = websocket
        
        # Handle messages
        while True:
            data = await websocket.receive_json()
            request = WSRequest(**data)
            
            # Process request
            if request.action == "subscribe":
                # Handle subscription
                response = WSResponse(
                    status="success",
                    data={"subscribed": request.params.get("topics", [])}
                )
            else:
                response = WSResponse(
                    status="error",
                    error="Unknown action"
                )
            
            # Send response
            await websocket.send_json(response.dict())
            
    except Exception as e:
        print(f"WebSocket error: {e}")
    
    finally:
        # Clean up connection
        if client_id in ws_connections:
            del ws_connections[client_id]

async def broadcast_update(message: WSMessage):
    """Broadcast update to all connected clients."""
    for ws in ws_connections.values():
        try:
            await ws.send_json(message.dict())
        except Exception as e:
            print(f"Error broadcasting to client: {e}")

# Start background tasks
@app.on_event("startup")
async def startup_event():
    """Start background tasks."""
    asyncio.create_task(update_loop())

async def update_loop():
    """Background task to send updates."""
    while True:
        try:
            # Send metrics update
            metrics = {
                name: [v.dict() for v in metric.values[-5:]]
                for name, metric in monitoring.metrics.items()
            }
            
            await broadcast_update(WSMessage(
                type="metrics_update",
                data={"metrics": metrics}
            ))
            
            # Send alerts update
            alerts = [
                alert.dict()
                for alert in monitoring.active_alerts.values()
            ]
            
            await broadcast_update(WSMessage(
                type="alerts_update",
                data={"alerts": alerts}
            ))
            
            # Wait before next update
            await asyncio.sleep(5)
            
        except Exception as e:
            print(f"Error in update loop: {e}")
            await asyncio.sleep(5)
