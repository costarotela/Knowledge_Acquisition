"""
Alert system for monitoring and notifications.
"""
from typing import Dict, Any, List, Optional, Union, Callable
from pydantic import BaseModel
from datetime import datetime, timedelta
import asyncio
import logging
import json
from enum import Enum

logger = logging.getLogger(__name__)

class AlertSeverity(str, Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class AlertCondition(BaseModel):
    """Alert condition configuration."""
    metric: str
    operator: str  # gt, lt, eq, neq
    threshold: Union[int, float]
    duration: Optional[int] = None  # Duration in seconds
    severity: AlertSeverity = AlertSeverity.WARNING

class AlertAction(BaseModel):
    """Alert action configuration."""
    type: str  # email, webhook, slack
    config: Dict[str, Any]

class AlertRule(BaseModel):
    """Alert rule configuration."""
    name: str
    description: Optional[str] = None
    condition: AlertCondition
    actions: List[AlertAction]
    enabled: bool = True
    cooldown: Optional[int] = None  # Cooldown in seconds

class AlertState(BaseModel):
    """Alert state tracking."""
    active: bool = False
    last_triggered: Optional[datetime] = None
    last_resolved: Optional[datetime] = None
    trigger_count: int = 0

class AlertManager:
    """Manager for alert operations."""
    
    def __init__(self):
        """Initialize alert manager."""
        self.rules: Dict[str, AlertRule] = {}
        self.states: Dict[str, AlertState] = {}
        self.handlers: Dict[str, Callable] = {}
    
    def add_rule(self, rule: AlertRule):
        """Add new alert rule."""
        self.rules[rule.name] = rule
        self.states[rule.name] = AlertState()
        logger.info(f"Added alert rule: {rule.name}")
    
    def remove_rule(self, name: str):
        """Remove alert rule."""
        if name in self.rules:
            del self.rules[name]
            del self.states[name]
            logger.info(f"Removed alert rule: {name}")
    
    def register_handler(
        self,
        action_type: str,
        handler: Callable
    ):
        """Register action handler."""
        self.handlers[action_type] = handler
        logger.info(f"Registered handler for action type: {action_type}")
    
    def _check_condition(
        self,
        condition: AlertCondition,
        value: Union[int, float]
    ) -> bool:
        """Check if condition is met."""
        if condition.operator == "gt":
            return value > condition.threshold
        elif condition.operator == "lt":
            return value < condition.threshold
        elif condition.operator == "eq":
            return value == condition.threshold
        elif condition.operator == "neq":
            return value != condition.threshold
        else:
            raise ValueError(f"Invalid operator: {condition.operator}")
    
    async def _execute_actions(
        self,
        rule: AlertRule,
        value: Union[int, float],
        is_trigger: bool
    ):
        """Execute alert actions."""
        for action in rule.actions:
            if action.type not in self.handlers:
                logger.warning(
                    f"No handler for action type: {action.type}"
                )
                continue
            
            try:
                handler = self.handlers[action.type]
                await handler(
                    rule=rule,
                    value=value,
                    is_trigger=is_trigger,
                    config=action.config
                )
                
            except Exception as e:
                logger.error(
                    f"Error executing action {action.type}: {str(e)}"
                )
    
    async def process_metric(
        self,
        metric: str,
        value: Union[int, float]
    ):
        """Process metric value against alert rules."""
        for rule in self.rules.values():
            if not rule.enabled:
                continue
            
            if rule.condition.metric != metric:
                continue
            
            state = self.states[rule.name]
            condition_met = self._check_condition(
                rule.condition,
                value
            )
            
            # Check if alert should be triggered
            if condition_met and not state.active:
                # Check cooldown
                if (
                    rule.cooldown and
                    state.last_triggered and
                    datetime.now() - state.last_triggered <
                    timedelta(seconds=rule.cooldown)
                ):
                    continue
                
                # Check duration
                if rule.condition.duration:
                    # Start duration timer
                    await asyncio.sleep(rule.condition.duration)
                    # Recheck condition
                    if not self._check_condition(
                        rule.condition,
                        value
                    ):
                        continue
                
                # Trigger alert
                state.active = True
                state.last_triggered = datetime.now()
                state.trigger_count += 1
                
                await self._execute_actions(rule, value, True)
                
                logger.info(
                    f"Alert triggered: {rule.name} "
                    f"(value: {value}, threshold: {rule.condition.threshold})"
                )
            
            # Check if alert should be resolved
            elif not condition_met and state.active:
                state.active = False
                state.last_resolved = datetime.now()
                
                await self._execute_actions(rule, value, False)
                
                logger.info(f"Alert resolved: {rule.name}")

class MetricMonitor:
    """Monitor for tracking metrics and triggering alerts."""
    
    def __init__(self, alert_manager: AlertManager):
        """Initialize metric monitor."""
        self.alert_manager = alert_manager
        self.metrics: Dict[str, List[Dict[str, Any]]] = {}
    
    def record_metric(
        self,
        name: str,
        value: Union[int, float],
        labels: Optional[Dict[str, str]] = None
    ):
        """Record metric value."""
        if name not in self.metrics:
            self.metrics[name] = []
        
        self.metrics[name].append({
            "timestamp": datetime.now(),
            "value": value,
            "labels": labels or {}
        })
        
        # Process alerts
        asyncio.create_task(
            self.alert_manager.process_metric(name, value)
        )
    
    def get_metric_values(
        self,
        name: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        labels: Optional[Dict[str, str]] = None
    ) -> List[Dict[str, Any]]:
        """Get metric values with optional filtering."""
        if name not in self.metrics:
            return []
        
        values = self.metrics[name]
        
        # Apply time filters
        if start_time:
            values = [v for v in values if v["timestamp"] >= start_time]
        if end_time:
            values = [v for v in values if v["timestamp"] <= end_time]
        
        # Apply label filters
        if labels:
            values = [
                v for v in values
                if all(
                    v["labels"].get(k) == v
                    for k, v in labels.items()
                )
            ]
        
        return values
    
    def clear_old_metrics(
        self,
        max_age: timedelta
    ):
        """Clear metrics older than max_age."""
        cutoff = datetime.now() - max_age
        
        for name in self.metrics:
            self.metrics[name] = [
                v for v in self.metrics[name]
                if v["timestamp"] >= cutoff
            ]

class AlertHandler:
    """Default handlers for alert actions."""
    
    @staticmethod
    async def handle_email(
        rule: AlertRule,
        value: Union[int, float],
        is_trigger: bool,
        config: Dict[str, Any]
    ):
        """Handle email alert action."""
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        import smtplib
        
        # Create message
        msg = MIMEMultipart()
        msg["From"] = config["from_address"]
        msg["To"] = config["to_address"]
        
        if is_trigger:
            msg["Subject"] = f"Alert Triggered: {rule.name}"
            body = (
                f"Alert {rule.name} has been triggered\n\n"
                f"Metric: {rule.condition.metric}\n"
                f"Value: {value}\n"
                f"Threshold: {rule.condition.threshold}\n"
                f"Severity: {rule.condition.severity}"
            )
        else:
            msg["Subject"] = f"Alert Resolved: {rule.name}"
            body = f"Alert {rule.name} has been resolved"
        
        msg.attach(MIMEText(body, "plain"))
        
        # Send email
        with smtplib.SMTP(config["smtp_host"], config["smtp_port"]) as server:
            if config.get("use_tls"):
                server.starttls()
            
            if config.get("username"):
                server.login(
                    config["username"],
                    config["password"]
                )
            
            server.send_message(msg)
    
    @staticmethod
    async def handle_webhook(
        rule: AlertRule,
        value: Union[int, float],
        is_trigger: bool,
        config: Dict[str, Any]
    ):
        """Handle webhook alert action."""
        import aiohttp
        
        payload = {
            "alert": rule.name,
            "metric": rule.condition.metric,
            "value": value,
            "threshold": rule.condition.threshold,
            "severity": rule.condition.severity.value,
            "status": "triggered" if is_trigger else "resolved",
            "timestamp": datetime.now().isoformat()
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                config["url"],
                json=payload,
                headers=config.get("headers", {})
            ) as response:
                response.raise_for_status()
    
    @staticmethod
    async def handle_slack(
        rule: AlertRule,
        value: Union[int, float],
        is_trigger: bool,
        config: Dict[str, Any]
    ):
        """Handle Slack alert action."""
        import aiohttp
        
        if is_trigger:
            color = {
                AlertSeverity.INFO: "#36a64f",
                AlertSeverity.WARNING: "#ffcc00",
                AlertSeverity.ERROR: "#ff9900",
                AlertSeverity.CRITICAL: "#ff0000"
            }[rule.condition.severity]
            
            attachment = {
                "color": color,
                "title": f"Alert Triggered: {rule.name}",
                "fields": [
                    {
                        "title": "Metric",
                        "value": rule.condition.metric,
                        "short": True
                    },
                    {
                        "title": "Value",
                        "value": str(value),
                        "short": True
                    },
                    {
                        "title": "Threshold",
                        "value": str(rule.condition.threshold),
                        "short": True
                    },
                    {
                        "title": "Severity",
                        "value": rule.condition.severity.value,
                        "short": True
                    }
                ],
                "ts": int(datetime.now().timestamp())
            }
        else:
            attachment = {
                "color": "#36a64f",
                "title": f"Alert Resolved: {rule.name}",
                "text": (
                    f"The alert for metric {rule.condition.metric} "
                    f"has been resolved."
                ),
                "ts": int(datetime.now().timestamp())
            }
        
        payload = {
            "attachments": [attachment]
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                config["webhook_url"],
                json=payload
            ) as response:
                response.raise_for_status()
