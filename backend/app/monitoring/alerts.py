"""
Alert management system for monitoring critical events.
"""
import asyncio
import json
import smtplib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart
from dataclasses import dataclass, asdict
from enum import Enum
import aiohttp
import structlog
from ..core.config import settings

logger = structlog.get_logger(__name__)

class AlertSeverity(Enum):
    """Alert severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"

class AlertStatus(Enum):
    """Alert status states."""
    ACTIVE = "active"
    RESOLVED = "resolved"
    ACKNOWLEDGED = "acknowledged"
    SUPPRESSED = "suppressed"

@dataclass
class Alert:
    """Alert data structure."""
    id: str
    title: str
    description: str
    severity: AlertSeverity
    status: AlertStatus
    source: str
    metric_name: Optional[str] = None
    metric_value: Optional[float] = None
    threshold: Optional[float] = None
    created_at: datetime = None
    updated_at: datetime = None
    resolved_at: Optional[datetime] = None
    tags: Dict[str, str] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.updated_at is None:
            self.updated_at = self.created_at
        if self.tags is None:
            self.tags = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert alert to dictionary."""
        data = asdict(self)
        data["severity"] = self.severity.value
        data["status"] = self.status.value
        data["created_at"] = self.created_at.isoformat()
        data["updated_at"] = self.updated_at.isoformat()
        if self.resolved_at:
            data["resolved_at"] = self.resolved_at.isoformat()
        return data

class AlertRule:
    """Alert rule configuration."""
    
    def __init__(
        self,
        name: str,
        metric_name: str,
        condition: str,  # "gt", "lt", "eq", "gte", "lte"
        threshold: float,
        severity: AlertSeverity,
        duration: timedelta = timedelta(minutes=1),
        description: str = "",
        tags: Dict[str, str] = None
    ):
        self.name = name
        self.metric_name = metric_name
        self.condition = condition
        self.threshold = threshold
        self.severity = severity
        self.duration = duration
        self.description = description
        self.tags = tags or {}
        self.breach_start_time = None
        self.last_alert_time = None
    
    def evaluate(self, metric_value: float) -> bool:
        """Evaluate if metric value breaches the rule."""
        conditions = {
            "gt": lambda v, t: v > t,
            "lt": lambda v, t: v < t,
            "gte": lambda v, t: v >= t,
            "lte": lambda v, t: v <= t,
            "eq": lambda v, t: v == t,
        }
        
        condition_func = conditions.get(self.condition)
        if not condition_func:
            logger.error(f"Unknown condition: {self.condition}")
            return False
        
        return condition_func(metric_value, self.threshold)
    
    def should_alert(self, metric_value: float) -> bool:
        """Determine if an alert should be triggered."""
        now = datetime.utcnow()
        is_breaching = self.evaluate(metric_value)
        
        if is_breaching:
            if self.breach_start_time is None:
                self.breach_start_time = now
            
            # Check if breach duration exceeded
            if now - self.breach_start_time >= self.duration:
                # Avoid duplicate alerts (cooldown period)
                if (self.last_alert_time is None or 
                    now - self.last_alert_time >= timedelta(minutes=5)):
                    self.last_alert_time = now
                    return True
        else:
            # Reset breach tracking when condition is no longer met
            self.breach_start_time = None
        
        return False

class NotificationChannel:
    """Base class for notification channels."""
    
    async def send_alert(self, alert: Alert) -> bool:
        """Send alert notification. Return True if successful."""
        raise NotImplementedError

class EmailNotificationChannel(NotificationChannel):
    """Email notification channel."""
    
    def __init__(self, smtp_host: str, smtp_port: int, username: str, 
                 password: str, from_email: str, to_emails: List[str]):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.from_email = from_email
        self.to_emails = to_emails
    
    async def send_alert(self, alert: Alert) -> bool:
        """Send alert via email."""
        try:
            # Create message
            msg = MimeMultipart()
            msg['From'] = self.from_email
            msg['To'] = ', '.join(self.to_emails)
            msg['Subject'] = f"[{alert.severity.value.upper()}] {alert.title}"
            
            # Create HTML body
            html_body = self._create_html_body(alert)
            msg.attach(MimeText(html_body, 'html'))
            
            # Send email
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.username, self.password)
                text = msg.as_string()
                server.sendmail(self.from_email, self.to_emails, text)
            
            logger.info("Alert email sent successfully", alert_id=alert.id)
            return True
            
        except Exception as e:
            logger.error("Failed to send alert email", error=str(e), alert_id=alert.id)
            return False
    
    def _create_html_body(self, alert: Alert) -> str:
        """Create HTML email body for alert."""
        severity_colors = {
            AlertSeverity.CRITICAL: "#dc3545",
            AlertSeverity.HIGH: "#fd7e14",
            AlertSeverity.MEDIUM: "#ffc107",
            AlertSeverity.LOW: "#28a745",
            AlertSeverity.INFO: "#17a2b8"
        }
        
        color = severity_colors.get(alert.severity, "#6c757d")
        
        return f"""
        <html>
        <body>
            <div style="font-family: Arial, sans-serif; max-width: 600px;">
                <div style="background-color: {color}; color: white; padding: 20px; border-radius: 5px 5px 0 0;">
                    <h2 style="margin: 0;">{alert.title}</h2>
                    <p style="margin: 5px 0 0 0;">Severity: {alert.severity.value.upper()}</p>
                </div>
                
                <div style="border: 1px solid #ddd; padding: 20px; border-radius: 0 0 5px 5px;">
                    <h3>Alert Details</h3>
                    <p><strong>Description:</strong> {alert.description}</p>
                    <p><strong>Source:</strong> {alert.source}</p>
                    <p><strong>Created:</strong> {alert.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
                    
                    {f'<p><strong>Metric:</strong> {alert.metric_name}</p>' if alert.metric_name else ''}
                    {f'<p><strong>Current Value:</strong> {alert.metric_value}</p>' if alert.metric_value is not None else ''}
                    {f'<p><strong>Threshold:</strong> {alert.threshold}</p>' if alert.threshold is not None else ''}
                    
                    {self._format_tags(alert.tags)}
                </div>
            </div>
        </body>
        </html>
        """
    
    def _format_tags(self, tags: Dict[str, str]) -> str:
        """Format tags for HTML display."""
        if not tags:
            return ""
        
        tag_html = "<p><strong>Tags:</strong></p><ul>"
        for key, value in tags.items():
            tag_html += f"<li>{key}: {value}</li>"
        tag_html += "</ul>"
        return tag_html

class SlackNotificationChannel(NotificationChannel):
    """Slack notification channel."""
    
    def __init__(self, webhook_url: str, channel: str = None):
        self.webhook_url = webhook_url
        self.channel = channel
    
    async def send_alert(self, alert: Alert) -> bool:
        """Send alert to Slack."""
        try:
            # Color coding for different severities
            severity_colors = {
                AlertSeverity.CRITICAL: "danger",
                AlertSeverity.HIGH: "warning",
                AlertSeverity.MEDIUM: "warning",
                AlertSeverity.LOW: "good",
                AlertSeverity.INFO: "#17a2b8"
            }
            
            color = severity_colors.get(alert.severity, "good")
            
            # Create Slack message
            payload = {
                "text": f"🚨 Alert: {alert.title}",
                "attachments": [
                    {
                        "color": color,
                        "fields": [
                            {
                                "title": "Severity",
                                "value": alert.severity.value.upper(),
                                "short": True
                            },
                            {
                                "title": "Source",
                                "value": alert.source,
                                "short": True
                            },
                            {
                                "title": "Description",
                                "value": alert.description,
                                "short": False
                            }
                        ],
                        "ts": int(alert.created_at.timestamp())
                    }
                ]
            }
            
            if self.channel:
                payload["channel"] = self.channel
            
            # Add metric information if available
            if alert.metric_name:
                payload["attachments"][0]["fields"].extend([
                    {
                        "title": "Metric",
                        "value": alert.metric_name,
                        "short": True
                    },
                    {
                        "title": "Value",
                        "value": str(alert.metric_value),
                        "short": True
                    }
                ])
            
            # Send to Slack
            async with aiohttp.ClientSession() as session:
                async with session.post(self.webhook_url, json=payload) as response:
                    if response.status == 200:
                        logger.info("Alert sent to Slack successfully", alert_id=alert.id)
                        return True
                    else:
                        logger.error("Failed to send Slack alert", 
                                   status=response.status, alert_id=alert.id)
                        return False
                        
        except Exception as e:
            logger.error("Failed to send Slack alert", error=str(e), alert_id=alert.id)
            return False

class AlertManager:
    """Central alert management system."""
    
    def __init__(self):
        self.rules: List[AlertRule] = []
        self.active_alerts: Dict[str, Alert] = {}
        self.notification_channels: List[NotificationChannel] = []
        self.alert_history: List[Alert] = []
        self.suppression_rules: List[Dict] = []
        
        # Initialize notification channels
        self._init_notification_channels()
        
        # Define default alert rules
        self._init_default_rules()
    
    def _init_notification_channels(self):
        """Initialize notification channels from configuration."""
        # Email notifications
        if hasattr(settings, 'SMTP_HOST') and settings.SMTP_HOST:
            email_channel = EmailNotificationChannel(
                smtp_host=settings.SMTP_HOST,
                smtp_port=getattr(settings, 'SMTP_PORT', 587),
                username=getattr(settings, 'SMTP_USERNAME', ''),
                password=getattr(settings, 'SMTP_PASSWORD', ''),
                from_email=getattr(settings, 'ALERT_FROM_EMAIL', 'alerts@parking-system.com'),
                to_emails=getattr(settings, 'ALERT_TO_EMAILS', ['admin@parking-system.com'])
            )
            self.notification_channels.append(email_channel)
        
        # Slack notifications
        if hasattr(settings, 'SLACK_WEBHOOK_URL') and settings.SLACK_WEBHOOK_URL:
            slack_channel = SlackNotificationChannel(
                webhook_url=settings.SLACK_WEBHOOK_URL,
                channel=getattr(settings, 'SLACK_CHANNEL', '#alerts')
            )
            self.notification_channels.append(slack_channel)
    
    def _init_default_rules(self):
        """Initialize default alert rules."""
        default_rules = [
            # System resource alerts
            AlertRule(
                name="high_cpu_usage",
                metric_name="system_cpu_usage_percent",
                condition="gt",
                threshold=85.0,
                severity=AlertSeverity.HIGH,
                duration=timedelta(minutes=2),
                description="System CPU usage is above 85%",
                tags={"category": "system", "resource": "cpu"}
            ),
            AlertRule(
                name="high_memory_usage",
                metric_name="system_memory_usage_percent",
                condition="gt",
                threshold=90.0,
                severity=AlertSeverity.HIGH,
                duration=timedelta(minutes=1),
                description="System memory usage is above 90%",
                tags={"category": "system", "resource": "memory"}
            ),
            AlertRule(
                name="low_disk_space",
                metric_name="system_disk_usage_percent",
                condition="gt",
                threshold=95.0,
                severity=AlertSeverity.CRITICAL,
                duration=timedelta(seconds=30),
                description="Disk space usage is above 95%",
                tags={"category": "system", "resource": "disk"}
            ),
            
            # Application performance alerts
            AlertRule(
                name="slow_api_responses",
                metric_name="http_request_duration_seconds",
                condition="gt",
                threshold=3.0,
                severity=AlertSeverity.MEDIUM,
                duration=timedelta(minutes=1),
                description="API response times are consistently slow",
                tags={"category": "performance", "component": "api"}
            ),
            AlertRule(
                name="high_error_rate",
                metric_name="application_errors_total",
                condition="gt",
                threshold=10.0,
                severity=AlertSeverity.HIGH,
                duration=timedelta(minutes=1),
                description="High application error rate detected",
                tags={"category": "errors", "component": "application"}
            ),
            
            # Database alerts
            AlertRule(
                name="slow_database_queries",
                metric_name="database_query_duration_seconds",
                condition="gt",
                threshold=2.0,
                severity=AlertSeverity.MEDIUM,
                duration=timedelta(minutes=2),
                description="Database queries are running slowly",
                tags={"category": "performance", "component": "database"}
            ),
            AlertRule(
                name="low_database_connections",
                metric_name="database_connection_pool_size",
                condition="lt",
                threshold=5.0,
                severity=AlertSeverity.HIGH,
                duration=timedelta(seconds=30),
                description="Low number of available database connections",
                tags={"category": "database", "resource": "connections"}
            ),
        ]
        
        self.rules.extend(default_rules)
    
    def add_rule(self, rule: AlertRule):
        """Add a new alert rule."""
        self.rules.append(rule)
        logger.info("Alert rule added", rule_name=rule.name)
    
    def remove_rule(self, rule_name: str):
        """Remove an alert rule."""
        self.rules = [r for r in self.rules if r.name != rule_name]
        logger.info("Alert rule removed", rule_name=rule_name)
    
    async def evaluate_metric(self, metric_name: str, metric_value: float, tags: Dict[str, str] = None):
        """Evaluate metric value against all applicable rules."""
        for rule in self.rules:
            if rule.metric_name == metric_name:
                if rule.should_alert(metric_value):
                    await self._trigger_alert(rule, metric_value, tags or {})
    
    async def _trigger_alert(self, rule: AlertRule, metric_value: float, tags: Dict[str, str]):
        """Trigger an alert based on rule violation."""
        alert_id = f"{rule.name}_{int(datetime.utcnow().timestamp())}"
        
        alert = Alert(
            id=alert_id,
            title=f"Alert: {rule.name}",
            description=rule.description,
            severity=rule.severity,
            status=AlertStatus.ACTIVE,
            source="alert_manager",
            metric_name=rule.metric_name,
            metric_value=metric_value,
            threshold=rule.threshold,
            tags={**rule.tags, **tags}
        )
        
        # Check if alert should be suppressed
        if self._is_suppressed(alert):
            logger.info("Alert suppressed", alert_id=alert.id, rule_name=rule.name)
            return
        
        # Store active alert
        self.active_alerts[alert.id] = alert
        self.alert_history.append(alert)
        
        # Send notifications
        await self._send_notifications(alert)
        
        logger.warning("Alert triggered", 
                      alert_id=alert.id, 
                      rule_name=rule.name, 
                      metric_value=metric_value)
    
    async def _send_notifications(self, alert: Alert):
        """Send alert notifications through all configured channels."""
        for channel in self.notification_channels:
            try:
                success = await channel.send_alert(alert)
                if not success:
                    logger.error("Failed to send notification", 
                               channel=type(channel).__name__, 
                               alert_id=alert.id)
            except Exception as e:
                logger.error("Notification channel error", 
                           channel=type(channel).__name__, 
                           error=str(e), 
                           alert_id=alert.id)
    
    def _is_suppressed(self, alert: Alert) -> bool:
        """Check if alert should be suppressed based on suppression rules."""
        for suppression in self.suppression_rules:
            if self._matches_suppression_rule(alert, suppression):
                return True
        return False
    
    def _matches_suppression_rule(self, alert: Alert, suppression: Dict) -> bool:
        """Check if alert matches a suppression rule."""
        # Simple tag-based suppression matching
        if "tags" in suppression:
            for key, value in suppression["tags"].items():
                if alert.tags.get(key) != value:
                    return False
        
        if "severity" in suppression:
            if alert.severity.value not in suppression["severity"]:
                return False
        
        return True
    
    def resolve_alert(self, alert_id: str):
        """Manually resolve an alert."""
        if alert_id in self.active_alerts:
            alert = self.active_alerts[alert_id]
            alert.status = AlertStatus.RESOLVED
            alert.resolved_at = datetime.utcnow()
            alert.updated_at = datetime.utcnow()
            
            del self.active_alerts[alert_id]
            
            logger.info("Alert resolved", alert_id=alert_id)
    
    def acknowledge_alert(self, alert_id: str):
        """Acknowledge an alert."""
        if alert_id in self.active_alerts:
            alert = self.active_alerts[alert_id]
            alert.status = AlertStatus.ACKNOWLEDGED
            alert.updated_at = datetime.utcnow()
            
            logger.info("Alert acknowledged", alert_id=alert_id)
    
    def get_active_alerts(self) -> List[Alert]:
        """Get all active alerts."""
        return list(self.active_alerts.values())
    
    def get_alert_history(self, limit: int = 100) -> List[Alert]:
        """Get alert history."""
        return self.alert_history[-limit:]
    
    def add_suppression_rule(self, suppression: Dict):
        """Add an alert suppression rule."""
        self.suppression_rules.append(suppression)
        logger.info("Suppression rule added", suppression=suppression)

# Global alert manager instance
alert_manager = AlertManager()
