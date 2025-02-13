"""
Monitoring system implementation.
"""
from typing import Dict, Any, List, Optional, Union
import logging
import time
import asyncio
from datetime import datetime
import threading
from prometheus_client import start_http_server, Counter, Gauge, Histogram, Summary
import structlog
from opentelemetry import trace
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from .schemas import (
    MetricType, AlertSeverity, Metric, MetricValue,
    AlertRule, Alert, LogEntry, MonitoringConfig,
    Dashboard, DashboardPanel
)

class MonitoringSystem:
    """Central monitoring system."""
    
    def __init__(self, config: MonitoringConfig):
        """Initialize monitoring system."""
        self.config = config
        
        # Metrics
        self.metrics: Dict[str, Metric] = {}
        self.prometheus_metrics: Dict[str, Any] = {}
        
        # Alerts
        self.alert_rules: Dict[str, AlertRule] = {}
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: List[Alert] = []
        
        # Logging
        self.logger = self._setup_logging()
        
        # Tracing
        self.tracer = self._setup_tracing() if config.tracing_enabled else None
        
        # Dashboards
        self.dashboards: Dict[str, Dashboard] = {}
        
        # Start monitoring server if enabled
        if config.metrics_enabled:
            self._start_metrics_server()
        
        # Start alert checker if enabled
        if config.alerting_enabled:
            self._start_alert_checker()
    
    def _setup_logging(self) -> structlog.BoundLogger:
        """Setup structured logging."""
        structlog.configure(
            processors=[
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.JSONRenderer()
            ],
            context_class=dict,
            logger_factory=structlog.PrintLoggerFactory(),
            wrapper_class=structlog.BoundLogger,
            cache_logger_on_first_use=True,
        )
        
        return structlog.get_logger()
    
    def _setup_tracing(self) -> trace.Tracer:
        """Setup OpenTelemetry tracing."""
        jaeger_exporter = JaegerExporter(
            agent_host_name=self.config.jaeger_host,
            agent_port=self.config.jaeger_port,
        )
        
        provider = TracerProvider()
        processor = BatchSpanProcessor(jaeger_exporter)
        provider.add_span_processor(processor)
        trace.set_tracer_provider(provider)
        
        return trace.get_tracer(__name__)
    
    def _start_metrics_server(self):
        """Start Prometheus metrics server."""
        start_http_server(
            self.config.metrics_port,
            addr="0.0.0.0"
        )
    
    def _start_alert_checker(self):
        """Start alert checking thread."""
        def check_alerts():
            while True:
                try:
                    self._check_alert_rules()
                    time.sleep(self.config.alert_check_interval)
                except Exception as e:
                    self.logger.error("Error checking alerts", error=str(e))
        
        thread = threading.Thread(target=check_alerts, daemon=True)
        thread.start()
    
    def register_metric(
        self,
        name: str,
        metric_type: MetricType,
        description: str,
        unit: Optional[str] = None,
        labels: Optional[List[str]] = None
    ) -> bool:
        """Register a new metric."""
        try:
            if name in self.metrics:
                self.logger.warning("Metric already exists", metric_name=name)
                return False
            
            # Create Metric object
            metric = Metric(
                name=name,
                type=metric_type,
                description=description,
                unit=unit,
                labels=labels or []
            )
            
            # Create Prometheus metric
            if metric_type == MetricType.COUNTER:
                prom_metric = Counter(name, description, labels or [])
            elif metric_type == MetricType.GAUGE:
                prom_metric = Gauge(name, description, labels or [])
            elif metric_type == MetricType.HISTOGRAM:
                prom_metric = Histogram(name, description, labels or [])
            else:  # SUMMARY
                prom_metric = Summary(name, description, labels or [])
            
            self.metrics[name] = metric
            self.prometheus_metrics[name] = prom_metric
            
            self.logger.info("Registered metric", metric_name=name)
            return True
            
        except Exception as e:
            self.logger.error("Error registering metric", 
                            metric_name=name, error=str(e))
            return False
    
    def record_metric(
        self,
        name: str,
        value: Union[int, float],
        labels: Optional[Dict[str, str]] = None
    ):
        """Record a metric value."""
        try:
            if name not in self.metrics:
                self.logger.warning("Metric not found", metric_name=name)
                return
            
            metric = self.metrics[name]
            prom_metric = self.prometheus_metrics[name]
            
            # Record in Prometheus
            if labels:
                if metric.type == MetricType.COUNTER:
                    prom_metric.labels(**labels).inc(value)
                else:
                    prom_metric.labels(**labels).set(value)
            else:
                if metric.type == MetricType.COUNTER:
                    prom_metric.inc(value)
                else:
                    prom_metric.set(value)
            
            # Record in our storage
            metric_value = MetricValue(
                value=value,
                labels=labels or {}
            )
            metric.values.append(metric_value)
            
        except Exception as e:
            self.logger.error("Error recording metric",
                            metric_name=name, error=str(e))
    
    def register_alert_rule(self, rule: AlertRule) -> bool:
        """Register a new alert rule."""
        try:
            if rule.name in self.alert_rules:
                self.logger.warning("Alert rule already exists", rule_name=rule.name)
                return False
            
            self.alert_rules[rule.name] = rule
            self.logger.info("Registered alert rule", rule_name=rule.name)
            return True
            
        except Exception as e:
            self.logger.error("Error registering alert rule",
                            rule_name=rule.name, error=str(e))
            return False
    
    def _check_alert_rules(self):
        """Check all alert rules against current metrics."""
        for rule_name, rule in self.alert_rules.items():
            try:
                if rule.metric_name not in self.metrics:
                    continue
                
                metric = self.metrics[rule.metric_name]
                if not metric.values:
                    continue
                
                # Get latest value
                latest_value = metric.values[-1].value
                
                # Evaluate condition
                condition_vars = {
                    "value": latest_value,
                    "threshold": 0  # Can be made configurable
                }
                
                if eval(rule.condition, {}, condition_vars):
                    self._create_alert(rule, latest_value)
                
            except Exception as e:
                self.logger.error("Error checking alert rule",
                                rule_name=rule_name, error=str(e))
    
    def _create_alert(self, rule: AlertRule, value: float):
        """Create a new alert if needed."""
        # Check cooldown
        now = datetime.now()
        alert_key = f"{rule.name}_{rule.metric_name}"
        
        if (
            alert_key in self.active_alerts and
            not self.active_alerts[alert_key].resolved and
            (now - self.active_alerts[alert_key].timestamp).total_seconds() < rule.cooldown
        ):
            return
        
        # Create alert
        alert = Alert(
            alert_id=f"{alert_key}_{int(time.time())}",
            rule_name=rule.name,
            severity=rule.severity,
            message=f"Alert for {rule.metric_name}: {value}",
            metric_value=value,
            labels=rule.labels
        )
        
        self.active_alerts[alert_key] = alert
        self.alert_history.append(alert)
        
        # Handle alert
        self._handle_alert(alert)
    
    def _handle_alert(self, alert: Alert):
        """Handle a new alert."""
        self.logger.warning("Alert triggered",
                          alert_id=alert.alert_id,
                          severity=alert.severity,
                          message=alert.message)
        
        # Send to configured handlers
        for handler in self.config.alert_handlers:
            try:
                # Implement different alert handlers (email, Slack, etc.)
                pass
            except Exception as e:
                self.logger.error("Error in alert handler",
                                handler=handler, error=str(e))
    
    def log(
        self,
        level: str,
        message: str,
        source: str,
        trace_id: Optional[str] = None,
        **kwargs
    ):
        """Create a structured log entry."""
        try:
            entry = LogEntry(
                level=level,
                message=message,
                source=source,
                trace_id=trace_id,
                context=kwargs
            )
            
            # Log through structlog
            log_method = getattr(self.logger, level.lower())
            log_method(
                message,
                source=source,
                trace_id=trace_id,
                **kwargs
            )
            
            return entry
            
        except Exception as e:
            self.logger.error("Error creating log entry", error=str(e))
            return None
    
    def start_trace(
        self,
        name: str,
        attributes: Optional[Dict[str, str]] = None
    ) -> Optional[trace.Span]:
        """Start a new trace span."""
        if not self.tracer:
            return None
        
        try:
            return self.tracer.start_span(
                name,
                attributes=attributes
            )
        except Exception as e:
            self.logger.error("Error starting trace", error=str(e))
            return None
    
    def register_dashboard(self, dashboard: Dashboard) -> bool:
        """Register a new dashboard."""
        try:
            if dashboard.title in self.dashboards:
                self.logger.warning("Dashboard already exists",
                                  dashboard=dashboard.title)
                return False
            
            # Validate metrics exist
            for panel in dashboard.panels:
                for metric_name in panel.metrics:
                    if metric_name not in self.metrics:
                        raise ValueError(f"Metric not found: {metric_name}")
            
            self.dashboards[dashboard.title] = dashboard
            self.logger.info("Registered dashboard", dashboard=dashboard.title)
            return True
            
        except Exception as e:
            self.logger.error("Error registering dashboard",
                            dashboard=dashboard.title, error=str(e))
            return False
    
    def get_dashboard_data(
        self,
        title: str,
        time_range: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """Get data for a dashboard."""
        try:
            dashboard = self.dashboards.get(title)
            if not dashboard:
                return None
            
            data = {
                "title": dashboard.title,
                "panels": []
            }
            
            for panel in dashboard.panels:
                panel_data = {
                    "title": panel.title,
                    "type": panel.type,
                    "metrics": {}
                }
                
                for metric_name in panel.metrics:
                    metric = self.metrics.get(metric_name)
                    if not metric:
                        continue
                    
                    # Filter values by time range if specified
                    values = metric.values
                    if time_range:
                        cutoff = datetime.now().timestamp() - time_range
                        values = [
                            v for v in values
                            if v.timestamp.timestamp() > cutoff
                        ]
                    
                    panel_data["metrics"][metric_name] = [
                        {
                            "value": v.value,
                            "timestamp": v.timestamp.isoformat(),
                            "labels": v.labels
                        }
                        for v in values
                    ]
                
                data["panels"].append(panel_data)
            
            return data
            
        except Exception as e:
            self.logger.error("Error getting dashboard data",
                            dashboard=title, error=str(e))
            return None
