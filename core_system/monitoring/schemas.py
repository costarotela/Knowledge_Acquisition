"""
Schemas for monitoring system.
"""
from typing import Dict, Any, List, Optional, Union
from enum import Enum
from datetime import datetime
from pydantic import BaseModel, Field, validator

class MetricType(str, Enum):
    """Types of metrics that can be collected."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"

class AlertSeverity(str, Enum):
    """Severity levels for alerts."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class MetricValue(BaseModel):
    """Value of a metric with metadata."""
    value: Union[int, float]
    timestamp: datetime = Field(default_factory=datetime.now)
    labels: Dict[str, str] = Field(default_factory=dict)

class Metric(BaseModel):
    """Definition of a metric."""
    name: str
    type: MetricType
    description: str
    unit: Optional[str] = None
    labels: List[str] = Field(default_factory=list)
    values: List[MetricValue] = Field(default_factory=list)

class AlertRule(BaseModel):
    """Rule for generating alerts."""
    name: str
    metric_name: str
    condition: str  # Python expression as string
    severity: AlertSeverity
    cooldown: int = Field(default=300)  # seconds
    labels: Dict[str, str] = Field(default_factory=dict)
    description: str
    
    @validator("condition")
    def validate_condition(cls, v):
        """Validate condition can be evaluated."""
        try:
            # Simple validation - just check if it's a valid Python expression
            compile(v, "<string>", "eval")
            return v
        except Exception as e:
            raise ValueError(f"Invalid condition: {e}")

class Alert(BaseModel):
    """Generated alert."""
    alert_id: str
    rule_name: str
    severity: AlertSeverity
    message: str
    metric_value: float
    timestamp: datetime = Field(default_factory=datetime.now)
    labels: Dict[str, str] = Field(default_factory=dict)
    acknowledged: bool = False
    resolved: bool = False

class LogLevel(str, Enum):
    """Log levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

class LogEntry(BaseModel):
    """Structured log entry."""
    timestamp: datetime = Field(default_factory=datetime.now)
    level: LogLevel
    message: str
    source: str
    trace_id: Optional[str] = None
    context: Dict[str, Any] = Field(default_factory=dict)
    exception: Optional[str] = None

class MonitoringConfig(BaseModel):
    """Configuration for monitoring system."""
    metrics_enabled: bool = True
    metrics_port: int = Field(default=9090)
    metrics_path: str = Field(default="/metrics")
    
    alerting_enabled: bool = True
    alert_check_interval: int = Field(default=60)
    alert_handlers: List[str] = Field(default_factory=list)
    
    logging_enabled: bool = True
    log_format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    log_file: str = Field(default="logs/knowledge_acquisition.log")
    
    tracing_enabled: bool = False
    jaeger_host: Optional[str] = None
    jaeger_port: Optional[int] = None

class DashboardPanel(BaseModel):
    """Panel configuration for dashboard."""
    title: str
    type: str  # graph, gauge, table, etc.
    metrics: List[str]
    description: Optional[str] = None
    options: Dict[str, Any] = Field(default_factory=dict)

class Dashboard(BaseModel):
    """Dashboard configuration."""
    title: str
    panels: List[DashboardPanel]
    refresh_interval: int = Field(default=60)
    variables: Dict[str, Any] = Field(default_factory=dict)
