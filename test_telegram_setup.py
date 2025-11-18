"""
Test Telegram Bot Setup
Step 1: Verify bot token and get bot info
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

async def test_bot_token():
    """Test if bot token is valid and get bot info"""

    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')

    if not bot_token:
        print("❌ ERROR: TELEGRAM_BOT_TOKEN not found in .env")
        return False

    print(f"🔑 Bot Token Found: {bot_token[:20]}..." + "*" * 20)
    print("\n📡 Testing connection to Telegram...")

    try:
        bot = Bot(token=bot_token)
        bot_info = await bot.get_me()

        print("\n✅ SUCCESS! Bot is configured correctly!")
        print(f"\n🤖 Bot Information:")
        print(f"   ID: {bot_info.id}")
        print(f"   Username: @{bot_info.username}")
        print(f"   Name: {bot_info.first_name}")
        print(f"   Can Join Groups: {bot_info.can_join_groups}")
        print(f"   Can Read Messages: {bot_info.can_read_all_group_messages}")

        print(f"\n📱 To talk to your bot, search for: @{bot_info.username}")
        print(f"   Or use this link: https://t.me/{bot_info.username}")

        return True

    except TelegramError as e:
        print(f"\n❌ ERROR: {e}")
        print("\nPossible issues:")
        print("1. Invalid bot token")
        print("2. No internet connection")
        print("3. Telegram API is down")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_bot_token())

    if success:
        print("\n" + "="*60)
        print("NEXT STEP:")
        print("1. Open Telegram app")
        print("2. Search for your bot (see username above)")
        print("3. Click START or send /start")
        print("4. Then run: python test_telegram_chat_id.py")
        print("="*60)
