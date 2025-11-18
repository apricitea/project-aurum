"""
Test Telegram Bot - Get Chat ID and Send Test Message
Step 2: Get your chat ID and send a test trading signal
"""

import asyncio
import os
import sys
from dotenv import load_dotenv
from telegram import Bot
from telegram.error import TelegramError

# Fix encoding for Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Load environment
load_dotenv()

async def get_chat_id_and_send_test():
    """Get user's chat ID and send test message"""

    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')

    if not bot_token:
        print("❌ ERROR: TELEGRAM_BOT_TOKEN not found in .env")
        return

    print("🔍 Searching for your chat ID...")
    print("   (Make sure you sent /start to the bot first!)\n")

    try:
        bot = Bot(token=bot_token)
        updates = await bot.get_updates()

        if not updates:
            print("⚠️  No messages found!")
            print("\nPlease do this:")
            print("1. Open Telegram")
            print("2. Find your bot")
            print("3. Send /start command")
            print("4. Wait 5 seconds")
            print("5. Run this script again")
            return

        print(f"✅ Found {len(updates)} message(s)!\n")

        # Show all chat IDs found
        chat_ids = set()
        for update in updates:
            if update.message:
                chat_id = update.message.chat.id
                username = update.message.from_user.username or "No username"
                first_name = update.message.from_user.first_name
                message_text = update.message.text[:50] if update.message.text else "No text"

                chat_ids.add(chat_id)

                print(f"📱 Chat ID: {chat_id}")
                print(f"   From: {first_name} (@{username})")
                print(f"   Message: {message_text}")
                print()

        # Send test message to all found chats
        print("="*60)
        print("📤 SENDING TEST TRADING SIGNAL...")
        print("="*60)

        test_signal = """
🟢 *TEST TRADING SIGNAL* 🟢

📊 *Stock:* BBCA.JK (Bank Central Asia)
💰 *Signal:* STRONG BUY
📈 *Confidence:* 87%
💵 *Current Price:* IDR 8,750
🎯 *Target Price:* IDR 9,500 (+8.6%)
🛡️ *Stop Loss:* IDR 8,500 (-2.9%)

*Technical Analysis:*
• RSI: 58 (Neutral)
• MACD: Bullish crossover
• Volume: Above average (+15%)

*Fundamental:*
• P/E Ratio: 18.5
• ROE: 15.2%
• Sector: Financial

⏰ *Generated:* Just now
🤖 *Confidence Score:* 0.87

✅ *This is a TEST message!*
Your Telegram bot is working correctly! 🎉

Try these commands:
• /help - See all commands
• /signals - Get real signals
• /portfolio - View portfolio
        """

        for chat_id in chat_ids:
            await bot.send_message(
                chat_id=chat_id,
                text=test_signal,
                parse_mode='Markdown'
            )
            print(f"✅ Test signal sent to chat_id: {chat_id}")

        print("\n" + "="*60)
        print("SUCCESS! Check your Telegram for the message! 📱")
        print("="*60)

        # Save chat ID to .env suggestion
        if chat_ids:
            first_chat_id = list(chat_ids)[0]
            print(f"\n💡 TIP: Add this to your .env file:")
            print(f"   DEFAULT_TELEGRAM_CHATS={first_chat_id}")
            print(f"\n   This way you'll receive HIGH/CRITICAL alerts automatically!")

    except TelegramError as e:
        print(f"\n❌ ERROR: {e}")
        print("\nTroubleshooting:")
        print("1. Make sure you sent /start to the bot")
        print("2. Wait a few seconds and try again")
        print("3. Check your internet connection")

if __name__ == "__main__":
    asyncio.run(get_chat_id_and_send_test())
