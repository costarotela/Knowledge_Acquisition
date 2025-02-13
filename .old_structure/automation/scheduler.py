"""
Task scheduler for automated reports and notifications.
"""
from typing import Dict, Any, List, Optional, Union, Callable
import asyncio
import aiocron
from datetime import datetime, timedelta
import pytz
from pydantic import BaseModel
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
import aiohttp
import json
import logging

from export.exporters import ExportManager
from visualization.interactive.filters import SmartFilter
from visualization.interactive.customization import ChartFactory, ChartConfig

logger = logging.getLogger(__name__)

class EmailConfig(BaseModel):
    """Email configuration."""
    smtp_host: str
    smtp_port: int
    username: str
    password: str
    from_address: str
    use_tls: bool = True

class WebhookConfig(BaseModel):
    """Webhook configuration."""
    url: str
    method: str = "POST"
    headers: Dict[str, str] = {}
    retry_attempts: int = 3
    retry_delay: int = 5

class NotificationConfig(BaseModel):
    """Notification configuration."""
    email: Optional[EmailConfig] = None
    webhook: Optional[WebhookConfig] = None
    slack_webhook: Optional[str] = None

class ReportConfig(BaseModel):
    """Report configuration."""
    name: str
    description: Optional[str] = None
    schedule: str  # Cron expression
    timezone: str = "UTC"
    data_query: Dict[str, Any]
    export_formats: List[str]
    notification: NotificationConfig
    chart_config: Optional[ChartConfig] = None
    filters: Optional[Dict[str, Any]] = None

class NotificationManager:
    """Manager for sending notifications."""
    
    def __init__(self, config: NotificationConfig):
        """Initialize notification manager."""
        self.config = config
    
    async def send_email(
        self,
        subject: str,
        body: str,
        attachments: Optional[List[str]] = None
    ):
        """Send email notification."""
        if not self.config.email:
            return
        
        msg = MIMEMultipart()
        msg["From"] = self.config.email.from_address
        msg["Subject"] = subject
        
        # Add body
        msg.attach(MIMEText(body, "html"))
        
        # Add attachments
        if attachments:
            for filepath in attachments:
                with open(filepath, "rb") as f:
                    part = MIMEApplication(f.read())
                    part.add_header(
                        "Content-Disposition",
                        "attachment",
                        filename=filepath.split("/")[-1]
                    )
                    msg.attach(part)
        
        # Send email
        try:
            with smtplib.SMTP(
                self.config.email.smtp_host,
                self.config.email.smtp_port
            ) as server:
                if self.config.email.use_tls:
                    server.starttls()
                
                server.login(
                    self.config.email.username,
                    self.config.email.password
                )
                
                server.send_message(msg)
                
            logger.info(f"Email sent: {subject}")
            
        except Exception as e:
            logger.error(f"Error sending email: {str(e)}")
            raise
    
    async def send_webhook(
        self,
        data: Dict[str, Any]
    ):
        """Send webhook notification."""
        if not self.config.webhook:
            return
        
        async def _send_request(attempt: int = 1):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.request(
                        method=self.config.webhook.method,
                        url=self.config.webhook.url,
                        headers=self.config.webhook.headers,
                        json=data
                    ) as response:
                        response.raise_for_status()
                        logger.info(f"Webhook sent: {self.config.webhook.url}")
                        
            except Exception as e:
                if attempt < self.config.webhook.retry_attempts:
                    await asyncio.sleep(self.config.webhook.retry_delay)
                    await _send_request(attempt + 1)
                else:
                    logger.error(f"Error sending webhook: {str(e)}")
                    raise
        
        await _send_request()
    
    async def send_slack(
        self,
        message: str,
        attachments: Optional[List[Dict[str, Any]]] = None
    ):
        """Send Slack notification."""
        if not self.config.slack_webhook:
            return
        
        payload = {
            "text": message,
            "attachments": attachments or []
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.config.slack_webhook,
                json=payload
            ) as response:
                response.raise_for_status()
                logger.info("Slack notification sent")

class ReportGenerator:
    """Generator for automated reports."""
    
    def __init__(
        self,
        export_manager: ExportManager,
        chart_factory: Optional[ChartFactory] = None
    ):
        """Initialize report generator."""
        self.export_manager = export_manager
        self.chart_factory = chart_factory
    
    async def generate_report(
        self,
        data: Any,
        config: ReportConfig
    ) -> Dict[str, str]:
        """Generate report with charts and exports."""
        results = {}
        
        # Apply filters if specified
        if config.filters:
            smart_filter = SmartFilter(data)
            for field, filter_config in config.filters.items():
                smart_filter.add_filter(
                    field,
                    filter_config["value"],
                    filter_config.get("operator")
                )
            data = smart_filter.apply()
        
        # Generate charts if configured
        if config.chart_config and self.chart_factory:
            chart_factory = ChartFactory(config.chart_config)
            
            # Example: create line chart for time series
            if "timestamp" in data.columns:
                fig = chart_factory.create_line(
                    x=data["timestamp"],
                    y=data["value"]
                )
                results["chart"] = fig
        
        # Export data
        export_results = await self.export_manager.export_multiple(
            data,
            config.export_formats
        )
        results.update(export_results)
        
        return results

class AutomationScheduler:
    """Scheduler for automated tasks."""
    
    def __init__(
        self,
        export_manager: ExportManager,
        chart_factory: Optional[ChartFactory] = None
    ):
        """Initialize scheduler."""
        self.export_manager = export_manager
        self.chart_factory = chart_factory
        self.report_generator = ReportGenerator(
            export_manager,
            chart_factory
        )
        self.tasks = {}
    
    async def _execute_report(
        self,
        config: ReportConfig,
        data_provider: Callable
    ):
        """Execute scheduled report."""
        try:
            # Get data
            data = await data_provider(**config.data_query)
            
            # Generate report
            results = await self.report_generator.generate_report(
                data,
                config
            )
            
            # Send notifications
            notification_manager = NotificationManager(config.notification)
            
            # Email notification
            if config.notification.email:
                await notification_manager.send_email(
                    subject=f"Automated Report: {config.name}",
                    body=f"Please find attached the automated report for {config.name}",
                    attachments=[results[fmt] for fmt in config.export_formats]
                )
            
            # Webhook notification
            if config.notification.webhook:
                await notification_manager.send_webhook({
                    "report_name": config.name,
                    "timestamp": datetime.now().isoformat(),
                    "results": results
                })
            
            # Slack notification
            if config.notification.slack_webhook:
                await notification_manager.send_slack(
                    message=f"New report generated: {config.name}",
                    attachments=[{
                        "title": "Report Details",
                        "fields": [
                            {
                                "title": "Generated At",
                                "value": datetime.now().isoformat(),
                                "short": True
                            },
                            {
                                "title": "Formats",
                                "value": ", ".join(config.export_formats),
                                "short": True
                            }
                        ]
                    }]
                )
            
            logger.info(f"Report executed successfully: {config.name}")
            
        except Exception as e:
            logger.error(f"Error executing report {config.name}: {str(e)}")
            # Send error notification
            if config.notification.slack_webhook:
                await notification_manager.send_slack(
                    message=f"Error generating report: {config.name}\n```{str(e)}```"
                )
    
    def schedule_report(
        self,
        config: ReportConfig,
        data_provider: Callable
    ):
        """Schedule new report."""
        tz = pytz.timezone(config.timezone)
        
        # Create cron job
        job = aiocron.crontab(
            config.schedule,
            func=self._execute_report,
            args=(config, data_provider),
            start=True,
            tz=tz
        )
        
        self.tasks[config.name] = job
        logger.info(f"Scheduled report: {config.name} ({config.schedule})")
    
    def remove_report(self, name: str):
        """Remove scheduled report."""
        if name in self.tasks:
            self.tasks[name].stop()
            del self.tasks[name]
            logger.info(f"Removed scheduled report: {name}")
    
    def list_reports(self) -> List[Dict[str, Any]]:
        """List all scheduled reports."""
        return [
            {
                "name": name,
                "schedule": job.spec,
                "next_run": job.next(default_utc=True)
            }
            for name, job in self.tasks.items()
        ]
