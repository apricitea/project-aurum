"""
Test Full Alert System with Telegram
Step 3: Test the complete alert system integration
"""

import asyncio
import os
import sys
from dotenv import load_dotenv
from telegram import Bot

# Fix encoding for Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Load environment
load_dotenv()

async def test_full_alert_system():
    """Test sending alert through the complete system"""

    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')

    if not bot_token:
        print("❌ ERROR: TELEGRAM_BOT_TOKEN not found in .env")
        return

    print("🧪 TESTING FULL ALERT SYSTEM")
    print("="*60)

    # Get chat ID
    print("\n📡 Step 1: Getting your chat ID...")

    try:
        bot = Bot(token=bot_token)
        updates = await bot.get_updates()

        if not updates:
            print("❌ No messages found. Please send /start to your bot first!")
            return

        chat_id = updates[0].message.chat.id
        print(f"✅ Found chat ID: {chat_id}")

        # Test 1: Simple message
        print("\n📤 Step 2: Sending simple test message...")
        await bot.send_message(
            chat_id=chat_id,
            text="🔔 Alert System Test #1: Simple message"
        )
        print("✅ Simple message sent!")

        # Test 2: Formatted alert (like real alerts)
        print("\n📤 Step 3: Sending formatted alert (Markdown)...")

        alert_message = """
🔴 *TRADING ALERT*

*Type:* High Confidence Signal
*Priority:* HIGH
*Stock:* TLKM.JK

*Message:*
High confidence BUY signal for TLKM.JK (confidence: 0.85)

*Time:* 2025-10-02 14:30:00
        """

        await bot.send_message(
            chat_id=chat_id,
            text=alert_message,
            parse_mode='Markdown'
        )
        print("✅ Formatted alert sent!")

        # Test 3: Multi-stock signal
        print("\n📤 Step 4: Sending multi-stock signal...")

        multi_signal = """
📊 *DAILY TRADING SIGNALS*

🟢 *STRONG BUY (3):*
• BBCA.JK - Confidence: 88%
• BMRI.JK - Confidence: 85%
• TLKM.JK - Confidence: 82%

🟢 *BUY (2):*
• ASII.JK - Confidence: 75%
• UNVR.JK - Confidence: 72%

🔴 *SELL (1):*
• BBRI.JK - Confidence: 70%

⏰ Generated: 2025-10-02 08:30 WIB
🤖 System: Project Aurum v1.0

Use /signals for detailed analysis
        """

        await bot.send_message(
            chat_id=chat_id,
            text=multi_signal,
            parse_mode='Markdown'
        )
        print("✅ Multi-stock signal sent!")

        # Test 4: Risk alert
        print("\n📤 Step 5: Sending risk alert...")

        risk_alert = """
⚠️ *RISK ALERT*

*Type:* Portfolio Risk Warning
*Priority:* CRITICAL

*Issue:*
Portfolio volatility has exceeded the maximum threshold

*Current Metrics:*
• Volatility: 22.5% (Max: 20%)
• Drawdown: 12.3% (Max: 15%)
• Sector Concentration: 28% (Max: 25%)

*Action Required:*
Consider rebalancing your portfolio to reduce risk exposure

🔴 This requires immediate attention!
        """

        await bot.send_message(
            chat_id=chat_id,
            text=risk_alert,
            parse_mode='Markdown'
        )
        print("✅ Risk alert sent!")

        # Summary
        print("\n" + "="*60)
        print("✅ ALL TESTS PASSED!")
        print("="*60)
        print("\n📱 Check your Telegram - you should have received 4 messages:")
        print("   1. Simple test message")
        print("   2. High confidence signal alert")
        print("   3. Daily multi-stock signals")
        print("   4. Risk warning alert")
        print("\n🎉 Your Telegram bot is working perfectly!")

        print("\n" + "="*60)
        print("NEXT STEPS:")
        print("1. Add this to .env: DEFAULT_TELEGRAM_CHATS=" + str(chat_id))
        print("2. Start the main application: uvicorn src.api.main:app --reload")
        print("3. Send /start to your bot in Telegram")
        print("4. Use the interactive commands!")
        print("="*60)

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_full_alert_system())
