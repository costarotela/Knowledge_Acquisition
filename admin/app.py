"""
Admin interface for knowledge acquisition system.
"""
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta

from core_system.integration.agent_coordinator import AgentCoordinator
from core_system.pipeline.processor import PipelineProcessor
from core_system.monitoring.monitor import MonitoringSystem
from config.schemas import SystemConfig

def load_config():
    """Load system configuration."""
    return SystemConfig.from_yaml("config/config.yaml")

def init_session_state():
    """Initialize session state variables."""
    if "refresh_interval" not in st.session_state:
        st.session_state.refresh_interval = 30
    if "last_refresh" not in st.session_state:
        st.session_state.last_refresh = datetime.now()

def should_refresh():
    """Check if data should be refreshed."""
    now = datetime.now()
    if (now - st.session_state.last_refresh).seconds >= st.session_state.refresh_interval:
        st.session_state.last_refresh = now
        return True
    return False

def render_sidebar():
    """Render sidebar with controls."""
    st.sidebar.title("Knowledge Acquisition")
    
    st.sidebar.subheader("Refresh Settings")
    st.session_state.refresh_interval = st.sidebar.slider(
        "Refresh Interval (seconds)",
        min_value=5,
        max_value=300,
        value=st.session_state.refresh_interval
    )
    
    if st.sidebar.button("Refresh Now"):
        st.session_state.last_refresh = datetime.now() - timedelta(seconds=st.session_state.refresh_interval)

def render_metrics(monitoring: MonitoringSystem):
    """Render system metrics."""
    st.header("System Metrics")
    
    # Create metrics grid
    cols = st.columns(3)
    
    # Display key metrics
    for i, (name, metric) in enumerate(monitoring.metrics.items()):
        if metric.values:
            with cols[i % 3]:
                latest = metric.values[-1]
                st.metric(
                    label=name,
                    value=f"{latest.value:.2f}",
                    delta=f"{latest.value - metric.values[-2].value:.2f}"
                    if len(metric.values) > 1 else None
                )
    
    # Metrics over time
    st.subheader("Metrics Over Time")
    
    selected_metrics = st.multiselect(
        "Select metrics to display",
        options=list(monitoring.metrics.keys()),
        default=list(monitoring.metrics.keys())[:3]
    )
    
    if selected_metrics:
        fig = go.Figure()
        
        for name in selected_metrics:
            metric = monitoring.metrics[name]
            values = [v.value for v in metric.values]
            timestamps = [v.timestamp for v in metric.values]
            
            fig.add_trace(go.Scatter(
                x=timestamps,
                y=values,
                name=name,
                mode="lines+markers"
            ))
        
        fig.update_layout(
            title="Metrics Trends",
            xaxis_title="Time",
            yaxis_title="Value",
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)

def render_alerts(monitoring: MonitoringSystem):
    """Render system alerts."""
    st.header("Active Alerts")
    
    if not monitoring.active_alerts:
        st.info("No active alerts")
        return
    
    for alert in monitoring.active_alerts.values():
        severity_color = {
            "critical": "red",
            "error": "orange",
            "warning": "yellow",
            "info": "blue"
        }.get(alert.severity.value, "grey")
        
        st.error(
            f"**{alert.severity.value.upper()}**: {alert.message}\n\n"
            f"Time: {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
        ) if severity_color == "red" else st.warning(
            f"**{alert.severity.value.upper()}**: {alert.message}\n\n"
            f"Time: {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
        )

def render_agents(coordinator: AgentCoordinator):
    """Render agent status and management."""
    st.header("Agent Status")
    
    # Agent status grid
    cols = st.columns(4)
    for i, (agent_id, agent) in enumerate(coordinator.agents.items()):
        with cols[i % 4]:
            st.metric(
                label=f"{agent.__class__.__name__}",
                value=agent.state.value,
                delta=f"{agent.tasks_completed} tasks"
            )
    
    # Agent details
    st.subheader("Agent Details")
    
    selected_agent = st.selectbox(
        "Select agent",
        options=list(coordinator.agents.keys())
    )
    
    if selected_agent:
        agent = coordinator.agents[selected_agent]
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Configuration**")
            st.json(agent.config.dict())
        
        with col2:
            st.write("**Recent Tasks**")
            if agent.recent_tasks:
                for task in agent.recent_tasks[-5:]:
                    st.write(f"- {task.task_type}: {task.status.value}")
            else:
                st.write("No recent tasks")

def render_pipeline(processor: PipelineProcessor):
    """Render pipeline status and management."""
    st.header("Pipeline Status")
    
    # Pipeline overview
    for pipeline_id, pipeline in processor.pipelines.items():
        state = processor.get_pipeline_state(pipeline_id)
        
        st.subheader(f"Pipeline: {pipeline_id}")
        
        cols = st.columns(4)
        cols[0].metric("Status", state.status)
        cols[1].metric("Nodes", len(pipeline.nodes))
        cols[2].metric("Pending Tasks", len(state.pending_tasks))
        cols[3].metric("Completed Tasks", len(state.completed_tasks))
        
        # Node details
        st.write("**Node Status**")
        
        for node in pipeline.nodes:
            node_state = state.node_states.get(node.node_id)
            if node_state:
                st.write(
                    f"- {node.node_id} ({node.stage.value}): "
                    f"{node_state.status} - {len(node_state.processed_items)} items processed"
                )

def main():
    """Main admin interface."""
    st.set_page_config(
        page_title="Knowledge Acquisition Admin",
        page_icon="🧠",
        layout="wide"
    )
    
    init_session_state()
    render_sidebar()
    
    # Initialize systems
    config = load_config()
    coordinator = AgentCoordinator(config)
    processor = PipelineProcessor(config, coordinator)
    monitoring = MonitoringSystem(config.monitoring)
    
    # Refresh data if needed
    if should_refresh():
        st.experimental_rerun()
    
    # Render components
    render_metrics(monitoring)
    st.markdown("---")
    render_alerts(monitoring)
    st.markdown("---")
    render_agents(coordinator)
    st.markdown("---")
    render_pipeline(processor)

if __name__ == "__main__":
    main()
