"""
Integration module for automation system.
"""
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timedelta
import asyncio
import logging
from pathlib import Path

from .scheduler import (
    AutomationScheduler,
    ReportConfig,
    NotificationConfig
)
from .webhooks import (
    WebhookManager,
    WebhookEndpoint,
    WebhookServer
)
from .alerts import (
    AlertManager,
    MetricMonitor,
    AlertRule,
    AlertCondition,
    AlertAction,
    AlertSeverity
)

from ..agents.specialized.academic_agent import AcademicAgent
from ..agents.specialized.social_media_agent import SocialMediaAgent
from ..export.exporters import ExportManager
from ..visualization.dashboards.academic_dashboard import AcademicDashboard
from ..visualization.dashboards.social_dashboard import SocialDashboard

logger = logging.getLogger(__name__)

class AutomationSystem:
    """
    Main automation system that integrates all components.
    """
    
    def __init__(
        self,
        export_dir: Union[str, Path],
        webhook_host: str = "0.0.0.0",
        webhook_port: int = 8000
    ):
        """Initialize automation system."""
        self.export_dir = Path(export_dir)
        self.export_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize components
        self.export_manager = ExportManager(self.export_dir)
        self.scheduler = AutomationScheduler(self.export_manager)
        self.webhook_manager = WebhookManager()
        self.webhook_server = WebhookServer(webhook_host, webhook_port)
        self.alert_manager = AlertManager()
        self.metric_monitor = MetricMonitor(self.alert_manager)
        
        # Initialize agents
        self.academic_agent = AcademicAgent()
        self.social_agent = SocialMediaAgent()
        
        # Initialize dashboards
        self.academic_dashboard = AcademicDashboard()
        self.social_dashboard = SocialDashboard()
        
        # Setup default handlers
        self._setup_default_handlers()
    
    def _setup_default_handlers(self):
        """Setup default alert and webhook handlers."""
        from .alerts import AlertHandler
        
        # Register alert handlers
        self.alert_manager.register_handler(
            "email",
            AlertHandler.handle_email
        )
        self.alert_manager.register_handler(
            "webhook",
            AlertHandler.handle_webhook
        )
        self.alert_manager.register_handler(
            "slack",
            AlertHandler.handle_slack
        )
        
        # Register webhook routes
        self.webhook_server.add_route(
            "/webhook/academic",
            self._handle_academic_webhook
        )
        self.webhook_server.add_route(
            "/webhook/social",
            self._handle_social_webhook
        )
    
    async def _handle_academic_webhook(self, payload: Dict[str, Any]):
        """Handle academic agent webhooks."""
        event_type = payload.get("type")
        
        if event_type == "paper_processed":
            # Update metrics
            self.metric_monitor.record_metric(
                "papers_processed",
                1,
                labels={"source": payload.get("source")}
            )
            
            # Update dashboard
            await self.academic_dashboard.update_metrics(payload)
            
        elif event_type == "citation_found":
            self.metric_monitor.record_metric(
                "citations_found",
                1,
                labels={"paper_id": payload.get("paper_id")}
            )
    
    async def _handle_social_webhook(self, payload: Dict[str, Any]):
        """Handle social media agent webhooks."""
        event_type = payload.get("type")
        
        if event_type == "post_processed":
            # Update metrics
            self.metric_monitor.record_metric(
                "posts_processed",
                1,
                labels={"platform": payload.get("platform")}
            )
            
            # Update dashboard
            await self.social_dashboard.update_metrics(payload)
            
        elif event_type == "engagement_update":
            self.metric_monitor.record_metric(
                "engagement_rate",
                payload.get("engagement_rate", 0),
                labels={"platform": payload.get("platform")}
            )
    
    def setup_default_alerts(self):
        """Setup default alert rules."""
        # Error rate alert
        self.alert_manager.add_rule(
            AlertRule(
                name="High Error Rate",
                condition=AlertCondition(
                    metric="error_rate",
                    operator="gt",
                    threshold=0.05,
                    duration=300,  # 5 minutes
                    severity=AlertSeverity.ERROR
                ),
                actions=[
                    AlertAction(
                        type="email",
                        config={
                            "to_address": "admin@example.com",
                            "subject": "High Error Rate Alert"
                        }
                    ),
                    AlertAction(
                        type="slack",
                        config={
                            "channel": "#alerts"
                        }
                    )
                ],
                cooldown=1800  # 30 minutes
            )
        )
        
        # Low processing rate alert
        self.alert_manager.add_rule(
            AlertRule(
                name="Low Processing Rate",
                condition=AlertCondition(
                    metric="items_processed_per_minute",
                    operator="lt",
                    threshold=10,
                    duration=600,  # 10 minutes
                    severity=AlertSeverity.WARNING
                ),
                actions=[
                    AlertAction(
                        type="email",
                        config={
                            "to_address": "admin@example.com",
                            "subject": "Low Processing Rate Alert"
                        }
                    )
                ],
                cooldown=3600  # 1 hour
            )
        )
    
    def setup_default_reports(self):
        """Setup default automated reports."""
        # Daily academic report
        self.scheduler.schedule_report(
            ReportConfig(
                name="Daily Academic Analysis",
                schedule="0 9 * * *",  # Daily at 9 AM
                data_query={
                    "type": "academic",
                    "timeframe": "1d"
                },
                export_formats=["pdf", "excel"],
                notification=NotificationConfig(
                    email={
                        "to_address": "research@example.com",
                        "subject": "Daily Academic Report"
                    },
                    slack_webhook="https://hooks.slack.com/..."
                )
            ),
            self.academic_dashboard.get_daily_metrics
        )
        
        # Weekly social media report
        self.scheduler.schedule_report(
            ReportConfig(
                name="Weekly Social Analysis",
                schedule="0 10 * * MON",  # Monday at 10 AM
                data_query={
                    "type": "social",
                    "timeframe": "7d"
                },
                export_formats=["pdf", "excel"],
                notification=NotificationConfig(
                    email={
                        "to_address": "social@example.com",
                        "subject": "Weekly Social Media Report"
                    }
                )
            ),
            self.social_dashboard.get_weekly_metrics
        )
    
    async def start(self):
        """Start the automation system."""
        try:
            # Start webhook server
            self.webhook_runner, self.webhook_site = (
                await self.webhook_server.start()
            )
            logger.info("Webhook server started")
            
            # Setup default configurations
            self.setup_default_alerts()
            self.setup_default_reports()
            logger.info("Default alerts and reports configured")
            
            # Start metric cleanup task
            asyncio.create_task(self._cleanup_metrics())
            logger.info("Metric cleanup task started")
            
            logger.info("Automation system started successfully")
            
        except Exception as e:
            logger.error(f"Error starting automation system: {str(e)}")
            raise
    
    async def stop(self):
        """Stop the automation system."""
        try:
            # Stop webhook server
            if hasattr(self, 'webhook_runner'):
                await self.webhook_runner.cleanup()
            
            # Cancel all scheduled tasks
            self.scheduler.cancel_all()
            
            logger.info("Automation system stopped")
            
        except Exception as e:
            logger.error(f"Error stopping automation system: {str(e)}")
            raise
    
    async def _cleanup_metrics(self):
        """Periodically clean up old metrics."""
        while True:
            try:
                # Clean up metrics older than 30 days
                self.metric_monitor.clear_old_metrics(
                    timedelta(days=30)
                )
                
                # Wait for next cleanup
                await asyncio.sleep(86400)  # 24 hours
                
            except Exception as e:
                logger.error(f"Error in metric cleanup: {str(e)}")
                await asyncio.sleep(300)  # 5 minutes
