"""
Tests for automation components.
"""
import pytest
import asyncio
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from unittest.mock import Mock, patch, AsyncMock

from automation.scheduler import (
    ReportConfig,
    NotificationConfig,
    EmailConfig,
    AutomationScheduler
)
from automation.webhooks import (
    WebhookEndpoint,
    WebhookManager,
    WebhookServer,
    WebhookClient
)
from automation.alerts import (
    AlertManager,
    AlertRule,
    AlertCondition,
    AlertAction,
    AlertSeverity,
    MetricMonitor
)

# Scheduler Tests
@pytest.mark.asyncio
async def test_report_generation():
    """Test report generation functionality."""
    # Mock dependencies
    export_manager = Mock()
    export_manager.export_multiple = AsyncMock(
        return_value={
            "pdf": "/path/to/report.pdf",
            "excel": "/path/to/report.xlsx"
        }
    )
    
    # Create scheduler
    scheduler = AutomationScheduler(export_manager)
    
    # Configure test report
    config = ReportConfig(
        name="Test Report",
        schedule="*/5 * * * *",
        data_query={"table": "metrics"},
        export_formats=["pdf", "excel"],
        notification=NotificationConfig(
            email=EmailConfig(
                smtp_host="localhost",
                smtp_port=25,
                username="test",
                password="test",
                from_address="test@example.com"
            )
        )
    )
    
    # Mock data provider
    async def data_provider(**kwargs):
        return pd.DataFrame({
            "timestamp": pd.date_range(start="2025-01-01", periods=10),
            "value": np.random.randn(10)
        })
    
    # Schedule report
    scheduler.schedule_report(config, data_provider)
    
    # Verify report was scheduled
    assert "Test Report" in scheduler.tasks
    
    # Trigger report execution
    await scheduler._execute_report(config, data_provider)
    
    # Verify export was called
    export_manager.export_multiple.assert_called_once()
    args = export_manager.export_multiple.call_args[0]
    assert isinstance(args[0], pd.DataFrame)
    assert args[1] == ["pdf", "excel"]

# Webhook Tests
@pytest.mark.asyncio
async def test_webhook_dispatch():
    """Test webhook event dispatch."""
    # Create webhook manager
    manager = WebhookManager()
    
    # Register test endpoint
    endpoint = WebhookEndpoint(
        url="http://localhost:8000/webhook",
        secret="test-secret",
        events=["test.event"]
    )
    manager.register_endpoint("test", endpoint)
    
    # Mock aiohttp client
    with patch("aiohttp.ClientSession.post") as mock_post:
        mock_post.return_value.__aenter__.return_value.status = 200
        
        # Dispatch test event
        await manager.dispatch_event(
            "test.event",
            {"message": "Test payload"}
        )
        
        # Verify webhook was sent
        mock_post.assert_called_once()
        args = mock_post.call_args
        assert args[0][0] == "http://localhost:8000/webhook"
        assert "X-Webhook-Signature" in args[1]["headers"]

@pytest.mark.asyncio
async def test_webhook_server():
    """Test webhook server functionality."""
    # Create webhook server
    server = WebhookServer(host="localhost", port=8000)
    
    # Mock handler
    async def handler(payload):
        assert payload["event"] == "test.event"
        return {"status": "processed"}
    
    # Add route
    server.add_route("/webhook", handler)
    
    # Start server
    runner, site = await server.start()
    
    try:
        # Create test client
        client = WebhookClient("http://localhost:8000")
        
        # Send test webhook
        response = await client.send(
            "webhook",
            {"event": "test.event"}
        )
        
        assert response["status"] == "processed"
        
    finally:
        await runner.cleanup()

# Alert Tests
@pytest.mark.asyncio
async def test_alert_triggering():
    """Test alert triggering and actions."""
    # Create alert manager
    manager = AlertManager()
    
    # Mock action handler
    mock_handler = AsyncMock()
    manager.register_handler("test", mock_handler)
    
    # Create test rule
    rule = AlertRule(
        name="Test Alert",
        condition=AlertCondition(
            metric="test_metric",
            operator="gt",
            threshold=10,
            severity=AlertSeverity.WARNING
        ),
        actions=[
            AlertAction(
                type="test",
                config={"url": "http://example.com"}
            )
        ]
    )
    manager.add_rule(rule)
    
    # Test alert triggering
    await manager.process_metric("test_metric", 15)
    
    # Verify handler was called
    mock_handler.assert_called_once()
    args = mock_handler.call_args[1]
    assert args["rule"].name == "Test Alert"
    assert args["value"] == 15
    assert args["is_trigger"] is True
    
    # Test alert resolution
    await manager.process_metric("test_metric", 5)
    
    assert mock_handler.call_count == 2
    args = mock_handler.call_args[1]
    assert args["is_trigger"] is False

def test_metric_monitor():
    """Test metric monitoring functionality."""
    # Create alert manager
    alert_manager = AlertManager()
    
    # Create metric monitor
    monitor = MetricMonitor(alert_manager)
    
    # Record test metrics
    monitor.record_metric(
        "test_metric",
        value=15,
        labels={"env": "test"}
    )
    
    monitor.record_metric(
        "test_metric",
        value=5,
        labels={"env": "prod"}
    )
    
    # Get metric values
    values = monitor.get_metric_values(
        "test_metric",
        labels={"env": "test"}
    )
    
    assert len(values) == 1
    assert values[0]["value"] == 15
    
    # Test metric cleanup
    monitor.clear_old_metrics(timedelta(hours=1))
    
    values = monitor.get_metric_values("test_metric")
    assert len(values) == 2  # Both metrics still within time range

@pytest.mark.asyncio
async def test_alert_cooldown():
    """Test alert cooldown functionality."""
    # Create alert manager
    manager = AlertManager()
    
    # Mock action handler
    mock_handler = AsyncMock()
    manager.register_handler("test", mock_handler)
    
    # Create test rule with cooldown
    rule = AlertRule(
        name="Test Alert",
        condition=AlertCondition(
            metric="test_metric",
            operator="gt",
            threshold=10
        ),
        actions=[
            AlertAction(
                type="test",
                config={}
            )
        ],
        cooldown=60  # 60 second cooldown
    )
    manager.add_rule(rule)
    
    # Trigger alert
    await manager.process_metric("test_metric", 15)
    assert mock_handler.call_count == 1
    
    # Try to trigger again immediately
    await manager.process_metric("test_metric", 15)
    assert mock_handler.call_count == 1  # Should not trigger due to cooldown
    
    # Mock time passage
    manager.states["Test Alert"].last_triggered = (
        datetime.now() - timedelta(seconds=61)
    )
    
    # Try to trigger again
    await manager.process_metric("test_metric", 15)
    assert mock_handler.call_count == 2  # Should trigger after cooldown

@pytest.mark.asyncio
async def test_alert_duration():
    """Test alert duration requirement."""
    # Create alert manager
    manager = AlertManager()
    
    # Mock action handler
    mock_handler = AsyncMock()
    manager.register_handler("test", mock_handler)
    
    # Create test rule with duration
    rule = AlertRule(
        name="Test Alert",
        condition=AlertCondition(
            metric="test_metric",
            operator="gt",
            threshold=10,
            duration=5  # 5 second duration requirement
        ),
        actions=[
            AlertAction(
                type="test",
                config={}
            )
        ]
    )
    manager.add_rule(rule)
    
    # Start processing metric
    task = asyncio.create_task(
        manager.process_metric("test_metric", 15)
    )
    
    # Verify alert not triggered immediately
    assert mock_handler.call_count == 0
    
    # Wait for duration
    await asyncio.sleep(6)
    await task
    
    # Verify alert triggered after duration
    assert mock_handler.call_count == 1

# Integration Tests
@pytest.mark.asyncio
async def test_full_automation_flow():
    """Test complete automation flow."""
    # Create components
    export_manager = Mock()
    export_manager.export_multiple = AsyncMock(
        return_value={"pdf": "/path/to/report.pdf"}
    )
    
    scheduler = AutomationScheduler(export_manager)
    webhook_manager = WebhookManager()
    alert_manager = AlertManager()
    
    # Configure webhook endpoint
    endpoint = WebhookEndpoint(
        url="http://localhost:8000/webhook",
        events=["alert.triggered"]
    )
    webhook_manager.register_endpoint("alerts", endpoint)
    
    # Configure alert rule
    rule = AlertRule(
        name="Critical Error",
        condition=AlertCondition(
            metric="error_rate",
            operator="gt",
            threshold=0.1,
            severity=AlertSeverity.CRITICAL
        ),
        actions=[
            AlertAction(
                type="webhook",
                config={"url": "http://localhost:8000/webhook"}
            )
        ]
    )
    alert_manager.add_rule(rule)
    
    # Configure automated report
    config = ReportConfig(
        name="Error Report",
        schedule="*/5 * * * *",
        data_query={"metric": "error_rate"},
        export_formats=["pdf"],
        notification=NotificationConfig(
            webhook=endpoint
        )
    )
    
    async def data_provider(**kwargs):
        return pd.DataFrame({
            "timestamp": [datetime.now()],
            "error_rate": [0.15]
        })
    
    # Schedule report
    scheduler.schedule_report(config, data_provider)
    
    # Mock webhook calls
    with patch("aiohttp.ClientSession.post") as mock_post:
        mock_post.return_value.__aenter__.return_value.status = 200
        
        # Execute report
        await scheduler._execute_report(config, data_provider)
        
        # Verify export and webhook calls
        assert export_manager.export_multiple.call_count == 1
        assert mock_post.call_count >= 1  # At least one webhook call
