# Telegram Bot Quick Start Guide

## 5-Minute Setup

### Step 1: Get Your Bot Token (2 minutes)

1. Open Telegram and search for `@BotFather`
2. Send: `/newbot`
3. Choose a name: `Indonesian Trading Bot`
4. Choose a username: `indonesian_trading_bot` (must end with 'bot')
5. Copy the bot token (looks like: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)

### Step 2: Configure Environment (1 minute)

Add to your `.env` file:

```env
TELEGRAM_ENABLED=true
TELEGRAM_BOT_TOKEN=paste_your_bot_token_here
WEB_APP_URL=http://localhost:3000
```

### Step 3: Update Configuration (1 minute)

Edit `src/api/config.py`, find the line with `DEFAULT_TELEGRAM_CHATS: List[str] = []` and add after it:

```python
TELEGRAM_WEBHOOK_URL: str = ""  # Leave empty for polling mode
WEB_APP_URL: str = "http://localhost:3000"
```

### Step 4: Run Database Migration (1 minute)

```bash
# Connect to PostgreSQL
psql -U postgres -d trading_system

# Run migration
\i src/api/migrations/add_telegram_bot_tables.sql

# Verify tables created
\dt telegram*

# Exit
\q
```

### Step 5: Start the Bot

```bash
# Run the example
cd C:\Code\passion\personal\github\active\project-aurum
python examples/telegram_bot_example.py
```

## Test Your Bot

1. Open Telegram
2. Search for your bot username (e.g., `@indonesian_trading_bot`)
3. Send: `/start`
4. Bot should respond with authentication link
5. Send: `/ping` to verify bot is working

## Available Commands

Once authenticated, try:

- `/signals` - Get today's top trading signals
- `/portfolio` - View your portfolio
- `/risk` - Check risk metrics
- `/market` - Market status
- `/help` - See all commands

## Troubleshooting

### Bot not responding?

```bash
# Check if Redis is running
redis-cli ping
# Should return: PONG

# Check if PostgreSQL is running
psql -U postgres -d trading_system -c "SELECT 1;"
# Should return: 1
```

### Can't find configuration?

Configuration priority:
1. Environment variables (`.env` file)
2. `src/api/config.py` defaults

### Database connection error?

Verify your database settings in `.env`:
```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=trading_system
DB_USER=postgres
DB_PASSWORD=your_password
```

### Import errors?

Make sure you're in the project root:
```bash
cd C:\Code\passion\personal\github\active\project-aurum
python examples/telegram_bot_example.py
```

## Next Steps

1. **Set up authentication flow**: Configure your web app to handle the `/telegram-auth` endpoint
2. **Customize messages**: Edit `src/api/telegram_handlers.py` to change message formats
3. **Add custom commands**: Follow the pattern in `TelegramCommandHandlers`
4. **Enable notifications**: Set up alert broadcasting for your users
5. **Production deployment**: Switch to webhook mode for better performance

## Production Checklist

- [ ] Set strong `JWT_SECRET_KEY` in production
- [ ] Enable webhook mode (set `TELEGRAM_WEBHOOK_URL`)
- [ ] Set up SSL certificate for webhook
- [ ] Configure production database
- [ ] Set up Redis with persistence
- [ ] Enable logging to file
- [ ] Set up monitoring (Prometheus/Grafana)
- [ ] Configure backup strategy
- [ ] Set up rate limiting in production
- [ ] Enable all security features

## Support Resources

- **Full Documentation**: `TELEGRAM_BOT_README.md`
- **Implementation Plan**: `TELEGRAM_BOT_IMPLEMENTATION_PLAN.md`
- **Example Code**: `examples/telegram_bot_example.py`
- **Database Schema**: `src/api/migrations/add_telegram_bot_tables.sql`

## Common Use Cases

### Use Case 1: Daily Signal Alerts

Schedule this to run every morning:
```python
import asyncio
from datetime import date

# In your scheduler
async def send_daily_signals():
    signals = await signal_service.get_daily_signals(date.today())
    alert = create_alert_from_signals(signals)
    await telegram_bot.broadcast_alert(alert)

asyncio.run(send_daily_signals())
```

### Use Case 2: Risk Alert Notifications

Monitor portfolio risk and alert users:
```python
async def check_risk_and_alert():
    portfolio = await signal_service.get_portfolio_summary()

    # Check sector concentration
    max_sector = max(portfolio['sector_breakdown'].values())
    if max_sector > 0.30:  # 30% limit
        alert = {
            'alert_type': 'risk_warning',
            'priority': 'high',
            'message': f'Sector concentration exceeded: {max_sector:.1%}'
        }
        await telegram_bot.broadcast_alert(alert)
```

### Use Case 3: Custom User Notifications

Send personalized alerts based on watchlist:
```python
async def notify_watchlist_signals():
    # Get user preferences
    users = await db.fetch("""
        SELECT u.telegram_chat_id, tp.watchlist
        FROM users u
        JOIN telegram_preferences tp ON u.id = tp.user_id
        WHERE tp.notifications_enabled = TRUE
    """)

    # Get today's signals
    signals = await signal_service.get_daily_signals(date.today())

    # Send to each user
    for user in users:
        watchlist = user['watchlist']
        relevant_signals = [s for s in signals if s['stock_code'] in watchlist]

        if relevant_signals:
            alert = create_watchlist_alert(relevant_signals)
            await telegram_bot.send_alert_to_user(user['telegram_chat_id'], alert)
```

## Integration with FastAPI

Add to your `main.py`:

```python
from fastapi import FastAPI
from src.api.telegram_bot_service import create_telegram_bot_service

app = FastAPI()
telegram_bot = None

@app.on_event("startup")
async def startup():
    global telegram_bot

    # Initialize services
    db_manager = DatabaseManager()
    await db_manager.initialize()

    signal_service = SignalService(db_manager)
    await signal_service.initialize()

    alert_engine = AlertEngine(db_manager)
    await alert_engine.initialize()

    # Start Telegram bot
    telegram_bot = await create_telegram_bot_service(
        db_manager, signal_service, alert_engine
    )
    await telegram_bot.start()

@app.on_event("shutdown")
async def shutdown():
    if telegram_bot:
        await telegram_bot.stop()

@app.get("/health/telegram")
async def telegram_health():
    return await telegram_bot.health_check()

@app.post("/api/telegram/broadcast")
async def broadcast_alert(alert: dict):
    await telegram_bot.broadcast_alert(alert)
    return {"status": "sent"}
```

---

**Ready to go!** Start the bot and try `/start` in Telegram.

For detailed documentation, see `TELEGRAM_BOT_README.md`.
