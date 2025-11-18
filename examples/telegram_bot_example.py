"""
Example: How to integrate and run the Telegram Bot Service
Indonesian Quantitative Trading System
"""

import asyncio
import logging
from pathlib import Path
import sys

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from src.api.database import DatabaseManager
from src.api.signal_service import SignalService
from src.api.alert_engine import AlertEngine
from src.api.telegram_bot_service import create_telegram_bot_service
from src.api.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def main():
    """
    Main function to initialize and run Telegram bot
    """
    db_manager = None
    signal_service = None
    alert_engine = None
    telegram_bot = None

    try:
        logger.info("Starting Telegram bot initialization...")

        # Step 1: Initialize Database Manager
        logger.info("Initializing database...")
        db_manager = DatabaseManager()
        await db_manager.initialize()

        # Verify database health
        db_healthy = await db_manager.health_check()
        if not db_healthy:
            raise Exception("Database health check failed")
        logger.info("Database initialized and healthy")

        # Step 2: Initialize Signal Service
        logger.info("Initializing signal service...")
        signal_service = SignalService(db_manager)
        await signal_service.initialize()

        # Verify signal service
        signal_health = await signal_service.health_check()
        logger.info(f"Signal service initialized: {signal_health}")

        # Step 3: Initialize Alert Engine
        logger.info("Initializing alert engine...")
        alert_engine = AlertEngine(db_manager)
        await alert_engine.initialize()
        logger.info("Alert engine initialized")

        # Step 4: Create and Initialize Telegram Bot
        logger.info("Creating Telegram bot service...")
        telegram_bot = await create_telegram_bot_service(
            db_manager=db_manager,
            signal_service=signal_service,
            alert_engine=alert_engine
        )
        logger.info("Telegram bot service created")

        # Step 5: Start Telegram Bot
        logger.info("Starting Telegram bot...")
        await telegram_bot.start()
        logger.info("Telegram bot started successfully!")

        # Step 6: Health Check
        health = await telegram_bot.health_check()
        logger.info(f"Bot health check: {health}")

        # Keep the bot running
        logger.info("Bot is now running. Press Ctrl+C to stop.")
        logger.info(f"Bot mode: {'Webhook' if telegram_bot.webhook_mode else 'Polling'}")
        logger.info(f"Bot token configured: {bool(settings.TELEGRAM_BOT_TOKEN)}")

        # Keep running until interrupted
        while True:
            await asyncio.sleep(60)

            # Periodic health check
            if telegram_bot.is_running:
                health = await telegram_bot.health_check()
                logger.debug(f"Health check: {health['status']}")
            else:
                logger.warning("Bot is not running!")
                break

    except KeyboardInterrupt:
        logger.info("Received shutdown signal...")

    except Exception as e:
        logger.error(f"Error in main: {str(e)}", exc_info=True)

    finally:
        # Cleanup
        logger.info("Shutting down services...")

        if telegram_bot:
            logger.info("Stopping Telegram bot...")
            await telegram_bot.stop()

        if alert_engine:
            logger.info("Closing alert engine...")
            # Add cleanup if needed

        if signal_service:
            logger.info("Closing signal service...")
            # Add cleanup if needed

        if db_manager:
            logger.info("Closing database connections...")
            await db_manager.close()

        logger.info("Shutdown complete")


async def test_bot_features():
    """
    Example: Testing specific bot features
    """
    logger.info("Testing bot features...")

    # Initialize services
    db_manager = DatabaseManager()
    await db_manager.initialize()

    signal_service = SignalService(db_manager)
    await signal_service.initialize()

    alert_engine = AlertEngine(db_manager)
    await alert_engine.initialize()

    telegram_bot = await create_telegram_bot_service(
        db_manager, signal_service, alert_engine
    )
    await telegram_bot.start()

    try:
        # Test 1: Health Check
        logger.info("Test 1: Health Check")
        health = await telegram_bot.health_check()
        logger.info(f"Health: {health}")

        # Test 2: Send Alert to Specific User (if you have a test chat_id)
        # Uncomment and replace with your test chat_id
        """
        logger.info("Test 2: Send Test Alert")
        test_alert = {
            'alert_type': 'test_alert',
            'priority': 'low',
            'message': 'This is a test alert from the bot',
            'stock_code': 'TEST',
            'created_at': '2025-10-02 10:00:00'
        }
        await telegram_bot.send_alert_to_user(
            chat_id=YOUR_CHAT_ID_HERE,
            alert=test_alert
        )
        logger.info("Test alert sent")
        """

        # Test 3: Broadcast Alert to All Users
        # Uncomment to test broadcasting
        """
        logger.info("Test 3: Broadcast Alert")
        broadcast_alert = {
            'alert_type': 'system_announcement',
            'priority': 'medium',
            'message': 'System maintenance scheduled for tonight',
            'created_at': '2025-10-02 10:00:00'
        }
        await telegram_bot.broadcast_alert(broadcast_alert)
        logger.info("Broadcast complete")
        """

        # Keep running for manual testing
        logger.info("Bot running for manual testing. Press Ctrl+C to stop.")
        while True:
            await asyncio.sleep(60)

    except KeyboardInterrupt:
        logger.info("Test interrupted")

    finally:
        await telegram_bot.stop()
        await db_manager.close()


async def example_send_daily_signals():
    """
    Example: Send daily signals to all users
    """
    logger.info("Sending daily signals to users...")

    db_manager = DatabaseManager()
    await db_manager.initialize()

    signal_service = SignalService(db_manager)
    await signal_service.initialize()

    alert_engine = AlertEngine(db_manager)
    await alert_engine.initialize()

    telegram_bot = await create_telegram_bot_service(
        db_manager, signal_service, alert_engine
    )
    await telegram_bot.start()

    try:
        # Generate signals (if not already generated)
        from datetime import date
        today = date.today()
        signals = await signal_service.get_daily_signals(today)

        if not signals:
            logger.warning("No signals available for today")
            return

        # Create alert for top signals
        top_signals = sorted(signals, key=lambda x: x['confidence'], reverse=True)[:5]

        message_parts = [f"Top 5 Signals for {today}:"]
        for i, signal in enumerate(top_signals, 1):
            message_parts.append(
                f"{i}. {signal['stock_code']} - {signal['signal_type']} "
                f"(Confidence: {signal['confidence']:.1%})"
            )

        alert = {
            'alert_type': 'daily_signals',
            'priority': 'medium',
            'message': '\n'.join(message_parts),
            'created_at': str(today)
        }

        # Broadcast to all users
        await telegram_bot.broadcast_alert(alert)
        logger.info("Daily signals sent to all users")

    finally:
        await telegram_bot.stop()
        await db_manager.close()


if __name__ == "__main__":
    # Run main bot
    asyncio.run(main())

    # Or run tests
    # asyncio.run(test_bot_features())

    # Or send daily signals
    # asyncio.run(example_send_daily_signals())
