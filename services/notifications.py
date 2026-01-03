"""Notification service for automated reporting and alerts.

Supports email and Slack notifications for:
- Pipeline completion reports
- Anomaly detection alerts
- Error notifications
"""

from __future__ import annotations

import logging
import smtplib
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional
import json

try:
    import requests
except ImportError:
    requests = None

try:
    from config import settings
except ImportError:
    class _FallbackSettings:
        SMTP_HOST = ""
        SMTP_PORT = 587
        SMTP_USER = ""
        SMTP_PASSWORD = ""
        SMTP_FROM = ""
        SLACK_WEBHOOK_URL = ""
        NOTIFICATION_ENABLED = False
    settings = _FallbackSettings()

logger = logging.getLogger(__name__)


@dataclass
class NotificationPayload:
    """Notification content."""
    title: str
    message: str
    level: str = "info"  # info, warning, error, success
    details: dict = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class NotificationChannel(ABC):
    """Abstract base class for notification channels."""
    
    @abstractmethod
    def send(self, payload: NotificationPayload) -> bool:
        """Send notification. Returns True if successful."""
        pass


class EmailChannel(NotificationChannel):
    """Email notification channel via SMTP."""
    
    def __init__(
        self,
        smtp_host: str = "",
        smtp_port: int = 587,
        smtp_user: str = "",
        smtp_password: str = "",
        from_address: str = "",
        to_addresses: list[str] = None,
    ):
        self.smtp_host = smtp_host or getattr(settings, 'SMTP_HOST', '')
        self.smtp_port = smtp_port or getattr(settings, 'SMTP_PORT', 587)
        self.smtp_user = smtp_user or getattr(settings, 'SMTP_USER', '')
        self.smtp_password = smtp_password or getattr(settings, 'SMTP_PASSWORD', '')
        self.from_address = from_address or getattr(settings, 'SMTP_FROM', '')
        self.to_addresses = to_addresses or []
    
    def send(self, payload: NotificationPayload) -> bool:
        if not all([self.smtp_host, self.smtp_user, self.to_addresses]):
            logger.warning("Email notification not configured")
            return False
        
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"[CACTI Automation] {payload.level.upper()}: {payload.title}"
            msg['From'] = self.from_address
            msg['To'] = ", ".join(self.to_addresses)
            
            # Plain text version
            text_content = f"""
{payload.title}
{'=' * len(payload.title)}

{payload.message}

Timestamp: {payload.timestamp}

Details:
{json.dumps(payload.details, indent=2) if payload.details else 'N/A'}
"""
            
            # HTML version
            level_colors = {
                'info': '#3498db',
                'warning': '#f39c12',
                'error': '#e74c3c',
                'success': '#2ecc71'
            }
            color = level_colors.get(payload.level, '#3498db')
            
            html_content = f"""
<!DOCTYPE html>
<html>
<head><style>
body {{ font-family: Arial, sans-serif; margin: 20px; }}
.header {{ background: {color}; color: white; padding: 15px; border-radius: 5px; }}
.content {{ padding: 20px; background: #f5f5f5; margin-top: 10px; border-radius: 5px; }}
.details {{ background: #fff; padding: 10px; border: 1px solid #ddd; border-radius: 3px; margin-top: 10px; }}
pre {{ background: #2d2d2d; color: #f8f8f2; padding: 10px; border-radius: 3px; overflow-x: auto; }}
</style></head>
<body>
<div class="header">
    <h2 style="margin:0;">{payload.title}</h2>
    <small>Level: {payload.level.upper()} | {payload.timestamp}</small>
</div>
<div class="content">
    <p>{payload.message}</p>
    {'<div class="details"><strong>Details:</strong><pre>' + json.dumps(payload.details, indent=2) + '</pre></div>' if payload.details else ''}
</div>
</body>
</html>
"""
            
            msg.attach(MIMEText(text_content, 'plain'))
            msg.attach(MIMEText(html_content, 'html'))
            
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.sendmail(self.from_address, self.to_addresses, msg.as_string())
            
            logger.info("Email notification sent: %s", payload.title)
            return True
            
        except Exception as e:
            logger.error("Failed to send email notification: %s", e)
            return False


class SlackChannel(NotificationChannel):
    """Slack notification channel via webhook."""
    
    def __init__(self, webhook_url: str = ""):
        self.webhook_url = webhook_url or getattr(settings, 'SLACK_WEBHOOK_URL', '')
    
    def send(self, payload: NotificationPayload) -> bool:
        if not self.webhook_url:
            logger.warning("Slack webhook not configured")
            return False
        
        if not requests:
            logger.error("requests library not installed")
            return False
        
        try:
            # Map levels to emoji
            level_emoji = {
                'info': ':information_source:',
                'warning': ':warning:',
                'error': ':x:',
                'success': ':white_check_mark:'
            }
            emoji = level_emoji.get(payload.level, ':bell:')
            
            # Build Slack message blocks
            slack_payload = {
                "blocks": [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": f"{emoji} {payload.title}",
                            "emoji": True
                        }
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": payload.message
                        }
                    },
                    {
                        "type": "context",
                        "elements": [
                            {
                                "type": "mrkdwn",
                                "text": f"*Level:* {payload.level.upper()} | *Time:* {payload.timestamp}"
                            }
                        ]
                    }
                ]
            }
            
            # Add details if present
            if payload.details:
                slack_payload["blocks"].append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"```{json.dumps(payload.details, indent=2)}```"
                    }
                })
            
            response = requests.post(
                self.webhook_url,
                json=slack_payload,
                timeout=10
            )
            response.raise_for_status()
            
            logger.info("Slack notification sent: %s", payload.title)
            return True
            
        except Exception as e:
            logger.error("Failed to send Slack notification: %s", e)
            return False


class NotificationService:
    """Main notification service that dispatches to multiple channels."""
    
    def __init__(self):
        self.channels: list[NotificationChannel] = []
    
    def add_channel(self, channel: NotificationChannel) -> 'NotificationService':
        """Add a notification channel. Returns self for chaining."""
        self.channels.append(channel)
        return self
    
    def notify(self, payload: NotificationPayload) -> dict[str, bool]:
        """Send notification to all configured channels. Returns success status per channel."""
        if not getattr(settings, 'NOTIFICATION_ENABLED', True):
            logger.debug("Notifications disabled")
            return {}
        
        results = {}
        for channel in self.channels:
            channel_name = type(channel).__name__
            results[channel_name] = channel.send(payload)
        return results
    
    # Convenience methods
    def notify_success(self, title: str, message: str, details: dict = None) -> dict:
        return self.notify(NotificationPayload(title, message, "success", details or {}))
    
    def notify_error(self, title: str, message: str, details: dict = None) -> dict:
        return self.notify(NotificationPayload(title, message, "error", details or {}))
    
    def notify_warning(self, title: str, message: str, details: dict = None) -> dict:
        return self.notify(NotificationPayload(title, message, "warning", details or {}))
    
    def notify_info(self, title: str, message: str, details: dict = None) -> dict:
        return self.notify(NotificationPayload(title, message, "info", details or {}))


# ==========================================================================
# Pipeline Notification Helpers
# ==========================================================================
def notify_pipeline_complete(
    run_id: str,
    success_count: int,
    fail_count: int,
    duration_seconds: float,
    csv_path: str = ""
) -> None:
    """Send notification when pipeline completes."""
    total = success_count + fail_count
    success_rate = (success_count / total * 100) if total > 0 else 0
    
    title = f"Pipeline Complete: {run_id}"
    message = f"Processed {total} items in {duration_seconds:.1f}s"
    
    level = "success" if fail_count == 0 else ("warning" if success_rate >= 90 else "error")
    
    details = {
        "run_id": run_id,
        "success": success_count,
        "failed": fail_count,
        "success_rate": f"{success_rate:.1f}%",
        "duration": f"{duration_seconds:.1f}s",
        "csv_output": csv_path
    }
    
    service = get_notification_service()
    service.notify(NotificationPayload(title, message, level, details))


def notify_anomaly_detected(
    metric_name: str,
    current_value: float,
    baseline_value: float,
    threshold: float
) -> None:
    """Send notification when anomaly is detected."""
    deviation = abs(current_value - baseline_value)
    deviation_pct = (deviation / baseline_value * 100) if baseline_value else 0
    
    title = f"Anomaly Detected: {metric_name}"
    message = f"Value {current_value:.2f} deviates {deviation_pct:.1f}% from baseline {baseline_value:.2f}"
    
    details = {
        "metric": metric_name,
        "current": current_value,
        "baseline": baseline_value,
        "deviation": deviation,
        "threshold": threshold
    }
    
    service = get_notification_service()
    service.notify(NotificationPayload(title, message, "warning", details))


# ==========================================================================
# Singleton service instance
# ==========================================================================
_notification_service: Optional[NotificationService] = None

def get_notification_service() -> NotificationService:
    """Get or create the notification service singleton."""
    global _notification_service
    if _notification_service is None:
        _notification_service = NotificationService()
        
        # Add email channel if configured
        if getattr(settings, 'SMTP_HOST', ''):
            _notification_service.add_channel(EmailChannel())
        
        # Add Slack channel if configured
        if getattr(settings, 'SLACK_WEBHOOK_URL', ''):
            _notification_service.add_channel(SlackChannel())
    
    return _notification_service
