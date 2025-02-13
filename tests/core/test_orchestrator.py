import pytest
from unittest.mock import Mock, patch
from core_system.agent_orchestrator import AgentOrchestrator
from core_system.monitoring import MonitoringSystem

@pytest.fixture
def mock_monitoring():
    return Mock(spec=MonitoringSystem)

@pytest.fixture
def orchestrator(mock_monitoring):
    return AgentOrchestrator(monitoring_system=mock_monitoring)

def test_agent_registration():
    """Test that agents can be registered with the orchestrator"""
    orchestrator = AgentOrchestrator()
    mock_agent = Mock()
    mock_agent.name = "test_agent"
    
    orchestrator.register_agent(mock_agent)
    assert "test_agent" in orchestrator.get_registered_agents()

def test_task_assignment():
    """Test that tasks are properly assigned to agents"""
    orchestrator = AgentOrchestrator()
    mock_agent = Mock()
    mock_agent.name = "test_agent"
    mock_agent.can_handle_task.return_value = True
    
    orchestrator.register_agent(mock_agent)
    task = {"type": "test_task", "data": "test_data"}
    
    orchestrator.assign_task(task)
    mock_agent.handle_task.assert_called_once_with(task)

def test_task_priority():
    """Test that tasks are processed according to their priority"""
    orchestrator = AgentOrchestrator()
    mock_agent = Mock()
    mock_agent.name = "test_agent"
    mock_agent.can_handle_task.return_value = True
    
    orchestrator.register_agent(mock_agent)
    high_priority_task = {"type": "test_task", "priority": "high", "data": "test_data"}
    low_priority_task = {"type": "test_task", "priority": "low", "data": "test_data"}
    
    orchestrator.assign_task(low_priority_task)
    orchestrator.assign_task(high_priority_task)
    
    # Verify high priority task was processed first
    assert mock_agent.handle_task.call_args_list[0][0][0] == high_priority_task

def test_error_handling():
    """Test that errors in agents are properly handled"""
    orchestrator = AgentOrchestrator()
    mock_agent = Mock()
    mock_agent.name = "test_agent"
    mock_agent.can_handle_task.return_value = True
    mock_agent.handle_task.side_effect = Exception("Test error")
    
    orchestrator.register_agent(mock_agent)
    task = {"type": "test_task", "data": "test_data"}
    
    with pytest.raises(Exception):
        orchestrator.assign_task(task)
    
    # Verify error was logged
    assert orchestrator.monitoring_system.log_error.called
