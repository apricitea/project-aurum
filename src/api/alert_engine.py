"""
Alert Engine for Indonesian Quantitative Trading System
Handles alert generation, processing, and multi-channel delivery
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
import json
import uuid
from dataclasses import dataclass
from enum import Enum
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import aioredis
import websockets
import telegram
from twilio.rest import Client as TwilioClient

from .database import DatabaseManager
from .config import settings

logger = logging.getLogger(__name__)


class AlertType(Enum):
    """Alert type enumeration"""
    HIGH_CONFIDENCE_SIGNAL = "high_confidence_signal"
    LARGE_POSITION = "large_position"
    SECTOR_CONCENTRATION = "sector_concentration"
    RISK_LIMIT_BREACH = "risk_limit_breach"
    POSITION_LOSS = "position_loss"
    MARKET_ANOMALY = "market_anomaly"
    SYSTEM_ERROR = "system_error"
    SIGNAL_GENERATION_COMPLETE = "signal_generation_complete"
    PORTFOLIO_REBALANCE = "portfolio_rebalance"
    DATA_QUALITY_ISSUE = "data_quality_issue"


class AlertPriority(Enum):
    """Alert priority levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertStatus(Enum):
    """Alert status enumeration"""
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    DISMISSED = "dismissed"
    EXPIRED = "expired"
    RESOLVED = "resolved"


@dataclass
class NotificationChannel:
    """Notification channel configuration"""
    name: str
    enabled: bool
    config: Dict[str, Any]
    delivery_method: Callable


class AlertRule:
    """Alert rule definition"""

    def __init__(self, rule_id: str, name: str, condition: Callable,
                 alert_type: AlertType, priority: AlertPriority,
                 message_template: str, metadata: Dict[str, Any] = None):
        self.rule_id = rule_id
        self.name = name
        self.condition = condition
        self.alert_type = alert_type
        self.priority = priority
        self.message_template = message_template
        self.metadata = metadata or {}
        self.enabled = True
        self.cooldown_minutes = 60  # Prevent spam
        self.last_triggered = None

    def should_trigger(self, data: Dict[str, Any]) -> bool:
        """Check if alert rule should trigger"""
        if not self.enabled:
            return False

        # Check cooldown period
        if self.last_triggered:
            time_since_last = datetime.now() - self.last_triggered
            if time_since_last.total_seconds() < (self.cooldown_minutes * 60):
                return False

        # Evaluate condition
        try:
            return self.condition(data)
        except Exception as e:
            logger.error(f"Error evaluating alert rule {self.rule_id}: {str(e)}")
            return False

    def generate_message(self, data: Dict[str, Any]) -> str:
        """Generate alert message from template"""
        try:
            return self.message_template.format(**data)
        except Exception as e:
            logger.error(f"Error generating alert message: {str(e)}")
            return f"Alert: {self.name} - Check system for details"

    def mark_triggered(self):
        """Mark rule as triggered"""
        self.last_triggered = datetime.now()


class EmailNotifier:
    """Email notification handler"""

    def __init__(self, smtp_config: Dict[str, Any]):
        self.smtp_server = smtp_config.get('server', 'smtp.gmail.com')
        self.smtp_port = smtp_config.get('port', 587)
        self.username = smtp_config.get('username')
        self.password = smtp_config.get('password')
        self.from_email = smtp_config.get('from_email', self.username)

    async def send_alert(self, alert: Dict[str, Any], recipients: List[str]):
        """Send alert via email"""
        try:
            msg = MIMEMultipart()
            msg['From'] = self.from_email
            msg['To'] = ', '.join(recipients)
            msg['Subject'] = f"Trading Alert: {alert['alert_type']} ({alert['priority'].upper()})"

            # Create email body
            body = self._create_email_body(alert)
            msg.attach(MIMEText(body, 'html'))

            # Send email
            context = ssl.create_default_context()
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls(context=context)
                server.login(self.username, self.password)
                server.send_message(msg)

            logger.info(f"Email alert sent to {len(recipients)} recipients")
            return True

        except Exception as e:
            logger.error(f"Failed to send email alert: {str(e)}")
            return False

    def _create_email_body(self, alert: Dict[str, Any]) -> str:
        """Create HTML email body"""
        priority_colors = {
            'low': '#28a745',
            'medium': '#ffc107',
            'high': '#fd7e14',
            'critical': '#dc3545'
        }

        color = priority_colors.get(alert['priority'], '#6c757d')

        return f"""
        <html>
        <body>
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <div style="background-color: {color}; color: white; padding: 20px; border-radius: 8px 8px 0 0;">
                    <h2 style="margin: 0;">🚨 Trading Alert</h2>
                    <p style="margin: 5px 0 0 0; opacity: 0.9;">
                        {alert['alert_type'].replace('_', ' ').title()} - {alert['priority'].upper()} Priority
                    </p>
                </div>

                <div style="background-color: #f8f9fa; padding: 20px; border: 1px solid #dee2e6;">
                    <h3 style="color: #495057; margin-top: 0;">Alert Details</h3>
                    <p style="font-size: 16px; line-height: 1.5; color: #495057;">
                        <strong>Message:</strong> {alert['message']}
                    </p>

                    <div style="margin: 15px 0;">
                        <p style="margin: 5px 0;"><strong>Stock:</strong> {alert.get('stock_code', 'N/A')}</p>
                        <p style="margin: 5px 0;"><strong>Time:</strong> {alert['created_at']}</p>
                        <p style="margin: 5px 0;"><strong>Status:</strong> {alert['status'].title()}</p>
                    </div>
                </div>

                <div style="background-color: #ffffff; padding: 20px; border: 1px solid #dee2e6; border-top: none; border-radius: 0 0 8px 8px;">
                    <p style="margin: 0; color: #6c757d; font-size: 14px;">
                        <em>Indonesian Quantitative Trading System</em><br>
                        This is an automated alert. Please review your dashboard for more details.
                    </p>
                </div>
            </div>
        </body>
        </html>
        """


class TelegramNotifier:
    """Telegram notification handler"""

    def __init__(self, bot_token: str):
        self.bot = telegram.Bot(token=bot_token)

    async def send_alert(self, alert: Dict[str, Any], chat_ids: List[str]):
        """Send alert via Telegram"""
        try:
            # Create message
            priority_emoji = {
                'low': '🟢',
                'medium': '🟡',
                'high': '🟠',
                'critical': '🔴'
            }

            emoji = priority_emoji.get(alert['priority'], '⚪')

            message = f"""
{emoji} *TRADING ALERT*

*Type:* {alert['alert_type'].replace('_', ' ').title()}
*Priority:* {alert['priority'].upper()}
*Stock:* {alert.get('stock_code', 'N/A')}

*Message:*
{alert['message']}

*Time:* {alert['created_at']}
            """.strip()

            # Send to each chat
            for chat_id in chat_ids:
                await self.bot.send_message(
                    chat_id=chat_id,
                    text=message,
                    parse_mode='Markdown'
                )

            logger.info(f"Telegram alert sent to {len(chat_ids)} chats")
            return True

        except Exception as e:
            logger.error(f"Failed to send Telegram alert: {str(e)}")
            return False


class SMSNotifier:
    """SMS notification handler using Twilio"""

    def __init__(self, twilio_config: Dict[str, Any]):
        self.client = TwilioClient(
            twilio_config['account_sid'],
            twilio_config['auth_token']
        )
        self.from_number = twilio_config['from_number']

    async def send_alert(self, alert: Dict[str, Any], phone_numbers: List[str]):
        """Send alert via SMS"""
        try:
            # Create short message for SMS
            message = (
                f"TRADING ALERT ({alert['priority'].upper()}): "
                f"{alert['alert_type'].replace('_', ' ').title()} - "
                f"{alert.get('stock_code', 'N/A')} - "
                f"{alert['message'][:100]}..."
            )

            # Send to each phone number
            for phone in phone_numbers:
                self.client.messages.create(
                    body=message,
                    from_=self.from_number,
                    to=phone
                )

            logger.info(f"SMS alert sent to {len(phone_numbers)} numbers")
            return True

        except Exception as e:
            logger.error(f"Failed to send SMS alert: {str(e)}")
            return False


class WebhookNotifier:
    """Webhook notification handler"""

    def __init__(self):
        self.session = None

    async def send_alert(self, alert: Dict[str, Any], webhook_urls: List[str]):
        """Send alert via webhook"""
        import aiohttp

        try:
            if not self.session:
                self.session = aiohttp.ClientSession()

            # Prepare payload
            payload = {
                'alert_id': alert['id'],
                'alert_type': alert['alert_type'],
                'priority': alert['priority'],
                'message': alert['message'],
                'stock_code': alert.get('stock_code'),
                'timestamp': alert['created_at'],
                'metadata': alert.get('metadata', {})
            }

            # Send to each webhook
            for url in webhook_urls:
                async with self.session.post(
                    url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        logger.info(f"Webhook alert sent successfully to {url}")
                    else:
                        logger.warning(f"Webhook failed with status {response.status}: {url}")

            return True

        except Exception as e:
            logger.error(f"Failed to send webhook alert: {str(e)}")
            return False


class AlertEngine:
    """
    Main alert engine that manages alert rules, processing, and delivery
    """

    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.redis_client = None
        self.notification_channels: Dict[str, NotificationChannel] = {}
        self.alert_rules: Dict[str, AlertRule] = {}
        self.websocket_clients: Dict[str, Any] = {}
        self.is_running = False

        # Initialize notification channels
        self._initialize_notification_channels()

        # Initialize alert rules
        self._initialize_alert_rules()

    async def initialize(self):
        """Initialize alert engine"""
        try:
            # Connect to Redis for caching and pub/sub
            self.redis_client = await aioredis.from_url(
                f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}",
                encoding="utf-8",
                decode_responses=True
            )

            # Start background alert processor
            asyncio.create_task(self._alert_processor())

            self.is_running = True
            logger.info("Alert engine initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize alert engine: {str(e)}")
            raise

    def _initialize_notification_channels(self):
        """Initialize notification channels"""
        # Email channel
        if settings.EMAIL_ENABLED:
            email_notifier = EmailNotifier(settings.EMAIL_CONFIG)
            self.notification_channels['email'] = NotificationChannel(
                name='email',
                enabled=True,
                config=settings.EMAIL_CONFIG,
                delivery_method=email_notifier.send_alert
            )

        # Telegram channel
        if settings.TELEGRAM_ENABLED:
            telegram_notifier = TelegramNotifier(settings.TELEGRAM_BOT_TOKEN)
            self.notification_channels['telegram'] = NotificationChannel(
                name='telegram',
                enabled=True,
                config={'bot_token': settings.TELEGRAM_BOT_TOKEN},
                delivery_method=telegram_notifier.send_alert
            )

        # SMS channel
        if settings.SMS_ENABLED:
            sms_notifier = SMSNotifier(settings.TWILIO_CONFIG)
            self.notification_channels['sms'] = NotificationChannel(
                name='sms',
                enabled=True,
                config=settings.TWILIO_CONFIG,
                delivery_method=sms_notifier.send_alert
            )

        # Webhook channel
        webhook_notifier = WebhookNotifier()
        self.notification_channels['webhook'] = NotificationChannel(
            name='webhook',
            enabled=True,
            config={},
            delivery_method=webhook_notifier.send_alert
        )

    def _initialize_alert_rules(self):
        """Initialize default alert rules"""

        # High confidence signal rule
        self.alert_rules['high_confidence'] = AlertRule(
            rule_id='high_confidence',
            name='High Confidence Signal',
            condition=lambda data: data.get('confidence', 0) > 0.8,
            alert_type=AlertType.HIGH_CONFIDENCE_SIGNAL,
            priority=AlertPriority.HIGH,
            message_template="High confidence {signal_type} signal for {stock_code} (confidence: {confidence:.2f})"
        )

        # Large position rule
        self.alert_rules['large_position'] = AlertRule(
            rule_id='large_position',
            name='Large Position Alert',
            condition=lambda data: data.get('position_size', 0) > 0.03,
            alert_type=AlertType.LARGE_POSITION,
            priority=AlertPriority.MEDIUM,
            message_template="Large position recommendation for {stock_code} ({position_size:.1%} of portfolio)"
        )

        # Risk limit breach rule
        self.alert_rules['risk_limit'] = AlertRule(
            rule_id='risk_limit',
            name='Risk Limit Breach',
            condition=lambda data: data.get('risk_level', 0) > 0.9,
            alert_type=AlertType.RISK_LIMIT_BREACH,
            priority=AlertPriority.CRITICAL,
            message_template="Risk limit breached: {risk_level:.1%} of risk budget utilized"
        )

        # Position loss rule
        self.alert_rules['position_loss'] = AlertRule(
            rule_id='position_loss',
            name='Position Loss Alert',
            condition=lambda data: data.get('unrealized_pnl_percent', 0) < -0.05,
            alert_type=AlertType.POSITION_LOSS,
            priority=AlertPriority.HIGH,
            message_template="Position {stock_code} down {unrealized_pnl_percent:.1%}"
        )

        # System error rule
        self.alert_rules['system_error'] = AlertRule(
            rule_id='system_error',
            name='System Error',
            condition=lambda data: data.get('error_severity') == 'critical',
            alert_type=AlertType.SYSTEM_ERROR,
            priority=AlertPriority.CRITICAL,
            message_template="System error: {error_message}"
        )

    async def create_alert(self, alert_type: str, message: str, priority: str = "medium",
                          metadata: Dict[str, Any] = None, user_id: str = None,
                          stock_code: str = None, expires_at: datetime = None) -> Dict[str, Any]:
        """Create new alert"""
        try:
            alert_data = {
                'alert_type': alert_type,
                'message': message,
                'priority': priority,
                'metadata': metadata or {},
                'user_id': user_id,
                'stock_code': stock_code,
                'expires_at': expires_at
            }

            # Save to database
            alert = await self.db_manager.create_alert(alert_data)

            # Cache alert for quick access
            await self.redis_client.setex(
                f"alert:{alert['id']}",
                3600,  # 1 hour TTL
                json.dumps(alert, default=str)
            )

            # Queue alert for processing
            await self.redis_client.lpush("alert_queue", alert['id'])

            logger.info(f"Alert created: {alert['id']} - {alert_type}")
            return alert

        except Exception as e:
            logger.error(f"Failed to create alert: {str(e)}")
            raise

    async def process_alert(self, alert_id: int):
        """Process and deliver alert"""
        try:
            # Get alert from cache or database
            cached_alert = await self.redis_client.get(f"alert:{alert_id}")

            if cached_alert:
                alert = json.loads(cached_alert)
            else:
                alerts = await self.db_manager.get_alerts(limit=1, offset=0)
                alert = next((a for a in alerts if a['id'] == alert_id), None)

            if not alert:
                logger.error(f"Alert {alert_id} not found")
                return

            # Determine delivery channels based on priority
            channels = self._get_delivery_channels(alert['priority'])

            # Get recipients for each channel
            recipients = await self._get_alert_recipients(alert, channels)

            # Deliver through each channel
            delivery_results = {}
            for channel_name in channels:
                if channel_name in self.notification_channels:
                    channel = self.notification_channels[channel_name]
                    if channel.enabled and channel_name in recipients:
                        try:
                            success = await channel.delivery_method(alert, recipients[channel_name])
                            delivery_results[channel_name] = 'success' if success else 'failed'
                        except Exception as e:
                            logger.error(f"Failed to deliver via {channel_name}: {str(e)}")
                            delivery_results[channel_name] = f'error: {str(e)}'

            # Update alert with delivery status
            metadata = alert.get('metadata', {})
            metadata['delivery_results'] = delivery_results
            metadata['processed_at'] = datetime.now().isoformat()

            # Send real-time update to WebSocket clients
            await self._broadcast_alert_update(alert)

            logger.info(f"Alert {alert_id} processed: {delivery_results}")

        except Exception as e:
            logger.error(f"Failed to process alert {alert_id}: {str(e)}")

    def _get_delivery_channels(self, priority: str) -> List[str]:
        """Get delivery channels based on alert priority"""
        channels = ['webhook']  # Always send webhooks

        if priority in ['high', 'critical']:
            channels.extend(['email', 'telegram'])

        if priority == 'critical':
            channels.append('sms')

        return channels

    async def _get_alert_recipients(self, alert: Dict[str, Any], channels: List[str]) -> Dict[str, List[str]]:
        """Get recipients for each delivery channel"""
        recipients = {}

        # Default recipients (could be loaded from database/config)
        default_recipients = {
            'email': settings.DEFAULT_EMAIL_RECIPIENTS,
            'telegram': settings.DEFAULT_TELEGRAM_CHATS,
            'sms': settings.DEFAULT_SMS_NUMBERS,
            'webhook': settings.DEFAULT_WEBHOOK_URLS
        }

        for channel in channels:
            recipients[channel] = default_recipients.get(channel, [])

        return recipients

    async def _broadcast_alert_update(self, alert: Dict[str, Any]):
        """Broadcast alert update to WebSocket clients"""
        if not self.websocket_clients:
            return

        message = {
            'type': 'alert_update',
            'data': alert
        }

        # Send to all connected clients
        disconnected_clients = []
        for client_id, websocket in self.websocket_clients.items():
            try:
                await websocket.send(json.dumps(message, default=str))
            except Exception:
                disconnected_clients.append(client_id)

        # Clean up disconnected clients
        for client_id in disconnected_clients:
            self.websocket_clients.pop(client_id, None)

    async def add_websocket_client(self, websocket) -> str:
        """Add WebSocket client for real-time updates"""
        client_id = str(uuid.uuid4())
        self.websocket_clients[client_id] = websocket
        logger.info(f"WebSocket client added: {client_id}")
        return client_id

    async def remove_websocket_client(self, client_id: str):
        """Remove WebSocket client"""
        self.websocket_clients.pop(client_id, None)
        logger.info(f"WebSocket client removed: {client_id}")

    async def check_alert_conditions(self, data: Dict[str, Any]):
        """Check all alert rules against data"""
        triggered_alerts = []

        for rule in self.alert_rules.values():
            if rule.should_trigger(data):
                message = rule.generate_message(data)

                alert = await self.create_alert(
                    alert_type=rule.alert_type.value,
                    message=message,
                    priority=rule.priority.value,
                    metadata={'rule_id': rule.rule_id, 'trigger_data': data},
                    stock_code=data.get('stock_code')
                )

                rule.mark_triggered()
                triggered_alerts.append(alert)

        return triggered_alerts

    async def _alert_processor(self):
        """Background alert processor"""
        while self.is_running:
            try:
                # Get alerts from queue
                alert_id = await self.redis_client.brpop("alert_queue", timeout=5)

                if alert_id:
                    alert_id = int(alert_id[1])  # brpop returns (key, value)
                    await self.process_alert(alert_id)

            except Exception as e:
                logger.error(f"Alert processor error: {str(e)}")
                await asyncio.sleep(1)

    async def get_alerts(self, limit: int = 100, offset: int = 0, status: str = None,
                        priority: str = None, start_date: datetime = None,
                        end_date: datetime = None, user_id: str = None) -> List[Dict[str, Any]]:
        """Get alerts with filtering"""
        return await self.db_manager.get_alerts(
            user_id=user_id,
            limit=limit,
            offset=offset,
            status=status,
            priority=priority,
            start_date=start_date,
            end_date=end_date
        )

    async def update_alert_status(self, alert_id: int, status: str, notes: str = None,
                                user_id: str = None) -> Dict[str, Any]:
        """Update alert status"""
        return await self.db_manager.update_alert_status(
            alert_id=alert_id,
            status=status,
            notes=notes,
            user_id=user_id
        )

    async def get_alert_statistics(self, days: int = 30) -> Dict[str, Any]:
        """Get alert statistics"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        alerts = await self.get_alerts(
            start_date=start_date,
            end_date=end_date,
            limit=10000
        )

        # Calculate statistics
        total_alerts = len(alerts)
        by_priority = {}
        by_type = {}
        by_status = {}

        for alert in alerts:
            priority = alert['priority']
            alert_type = alert['alert_type']
            status = alert['status']

            by_priority[priority] = by_priority.get(priority, 0) + 1
            by_type[alert_type] = by_type.get(alert_type, 0) + 1
            by_status[status] = by_status.get(status, 0) + 1

        return {
            'total_alerts': total_alerts,
            'by_priority': by_priority,
            'by_type': by_type,
            'by_status': by_status,
            'period_days': days
        }