"""
CLI commands for knowledge acquisition system.
"""
import click
import yaml
import asyncio
from rich.console import Console
from rich.table import Table
from rich.progress import track
from datetime import datetime

from core_system.integration.agent_coordinator import AgentCoordinator
from core_system.pipeline.processor import PipelineProcessor
from core_system.monitoring.monitor import MonitoringSystem
from config.schemas import SystemConfig

console = Console()

def load_config():
    """Load system configuration."""
    with open("config/config.yaml", "r") as f:
        config_dict = yaml.safe_load(f)
    return SystemConfig(**config_dict)

@click.group()
def cli():
    """Knowledge Acquisition System CLI."""
    pass

# Agent Commands
@cli.group()
def agents():
    """Agent management commands."""
    pass

@agents.command()
def list():
    """List all registered agents."""
    config = load_config()
    coordinator = AgentCoordinator(config)
    
    table = Table(title="Registered Agents")
    table.add_column("ID", style="cyan")
    table.add_column("Type", style="magenta")
    table.add_column("Status", style="green")
    table.add_column("Tasks Completed", justify="right")
    
    for agent_id, agent in coordinator.agents.items():
        table.add_row(
            agent_id,
            agent.__class__.__name__,
            agent.state.value,
            str(agent.tasks_completed)
        )
    
    console.print(table)

@agents.command()
@click.argument("agent_id")
def info(agent_id):
    """Show detailed information about an agent."""
    config = load_config()
    coordinator = AgentCoordinator(config)
    
    agent = coordinator.get_agent(agent_id)
    if not agent:
        console.print(f"[red]Agent {agent_id} not found[/red]")
        return
    
    console.print(f"[bold cyan]Agent Details: {agent_id}[/bold cyan]")
    console.print(f"Type: {agent.__class__.__name__}")
    console.print(f"Status: {agent.state.value}")
    console.print(f"Tasks Completed: {agent.tasks_completed}")
    console.print("\nConfiguration:")
    for key, value in agent.config.dict().items():
        console.print(f"  {key}: {value}")

# Pipeline Commands
@cli.group()
def pipeline():
    """Pipeline management commands."""
    pass

@pipeline.command()
def list():
    """List all registered pipelines."""
    config = load_config()
    processor = PipelineProcessor(config, AgentCoordinator(config))
    
    table = Table(title="Registered Pipelines")
    table.add_column("ID", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Nodes", justify="right")
    table.add_column("Tasks Pending", justify="right")
    
    for pipeline_id, pipeline in processor.pipelines.items():
        state = processor.get_pipeline_state(pipeline_id)
        table.add_row(
            pipeline_id,
            state.status,
            str(len(pipeline.nodes)),
            str(len(state.pending_tasks))
        )
    
    console.print(table)

@pipeline.command()
@click.argument("pipeline_id")
def info(pipeline_id):
    """Show detailed information about a pipeline."""
    config = load_config()
    processor = PipelineProcessor(config, AgentCoordinator(config))
    
    pipeline = processor.pipelines.get(pipeline_id)
    if not pipeline:
        console.print(f"[red]Pipeline {pipeline_id} not found[/red]")
        return
    
    state = processor.get_pipeline_state(pipeline_id)
    
    console.print(f"[bold cyan]Pipeline Details: {pipeline_id}[/bold cyan]")
    console.print(f"Status: {state.status}")
    console.print(f"Nodes: {len(pipeline.nodes)}")
    console.print(f"Tasks Pending: {len(state.pending_tasks)}")
    
    console.print("\nNodes:")
    for node in pipeline.nodes:
        console.print(f"\n  [magenta]{node.node_id}[/magenta]")
        console.print(f"  Stage: {node.stage.value}")
        console.print(f"  Agents: {', '.join(node.agent_ids)}")
        console.print(f"  Required: {node.required}")

# Monitoring Commands
@cli.group()
def monitor():
    """System monitoring commands."""
    pass

@monitor.command()
def metrics():
    """Show current system metrics."""
    config = load_config()
    monitoring = MonitoringSystem(config.monitoring)
    
    table = Table(title="System Metrics")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", justify="right")
    table.add_column("Type", style="magenta")
    
    for name, metric in monitoring.metrics.items():
        if metric.values:
            latest = metric.values[-1]
            table.add_row(
                name,
                f"{latest.value:.2f}",
                metric.type.value
            )
    
    console.print(table)

@monitor.command()
def alerts():
    """Show active alerts."""
    config = load_config()
    monitoring = MonitoringSystem(config.monitoring)
    
    table = Table(title="Active Alerts")
    table.add_column("ID", style="cyan")
    table.add_column("Severity", style="red")
    table.add_column("Message")
    table.add_column("Time", justify="right")
    
    for alert in monitoring.active_alerts.values():
        table.add_row(
            alert.alert_id,
            alert.severity.value,
            alert.message,
            alert.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        )
    
    console.print(table)

# Task Commands
@cli.group()
def tasks():
    """Task management commands."""
    pass

@tasks.command()
@click.argument("task_type")
@click.argument("input_data")
def submit(task_type, input_data):
    """Submit a new task for processing."""
    config = load_config()
    coordinator = AgentCoordinator(config)
    
    task = coordinator.create_task(
        task_type=task_type,
        input_data=input_data
    )
    
    with console.status("[bold green]Processing task..."):
        result = asyncio.run(coordinator.process_task(task))
    
    if result.success:
        console.print("[green]Task completed successfully![/green]")
        console.print("\nResults:")
        console.print(result.data)
    else:
        console.print("[red]Task failed![/red]")
        console.print(f"Error: {result.error}")

@tasks.command()
def list():
    """List recent tasks."""
    config = load_config()
    coordinator = AgentCoordinator(config)
    
    table = Table(title="Recent Tasks")
    table.add_column("ID", style="cyan")
    table.add_column("Type", style="magenta")
    table.add_column("Status", style="green")
    table.add_column("Created", justify="right")
    
    for task in coordinator.recent_tasks:
        table.add_row(
            task.id,
            task.task_type,
            task.status.value,
            task.created_at.strftime("%Y-%m-%d %H:%M:%S")
        )
    
    console.print(table)

if __name__ == "__main__":
    cli()
