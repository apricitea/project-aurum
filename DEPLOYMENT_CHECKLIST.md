# Project Aurum - Telegram Bot Deployment Checklist

## Pre-Deployment Checklist

### 1. Environment Configuration ✅

- [ ] Copy `.env.example` to `.env`
- [ ] Update database credentials
- [ ] Set secure JWT secret key
- [ ] Configure Redis connection
- [ ] Set up Telegram bot token
- [ ] Configure webhook URL (production only)
- [ ] Set web app URL for authentication

```bash
cp .env.example .env
# Edit .env with your values
```

### 2. Database Migration ✅

- [ ] Ensure PostgreSQL is running
- [ ] Run Telegram bot schema migration
- [ ] Verify all tables created successfully
- [ ] Check indexes are in place

```bash
# Run migration
psql -U postgres -d project_aurum -f migrations/versions/001_telegram_bot_schema.sql

# Verify tables
psql -U postgres -d project_aurum -c "\dt"
```

**Expected Tables:**
- ✅ telegram_auth_tokens
- ✅ telegram_preferences
- ✅ bot_command_log
- ✅ pending_transactions

### 3. Telegram Bot Setup ✅

- [ ] Create bot with [@BotFather](https://t.me/botfather)
- [ ] Copy bot token to `.env`
- [ ] Set bot description and about text
- [ ] Upload bot profile picture (optional)
- [ ] Set bot commands (optional)

```
BotFather Commands:
/newbot - Create your bot
/setdescription - Set bot description
/setabouttext - Set about text
/setcommands - Set command list
```

**Recommended Bot Commands to Set:**
```
start - Initialize bot and get auth link
help - Show available commands
signals - Get today's trading signals
portfolio - View your portfolio
risk - Check risk metrics
market - Check market status
buy - Buy stocks (format: /buy STOCK QTY PRICE)
sell - Sell stocks (format: /sell STOCK QTY PRICE)
watchlist - Manage your watchlist
subscribe - Manage alert preferences
```

### 4. Dependencies Installation ✅

- [ ] Install Python dependencies
- [ ] Verify all packages installed correctly
- [ ] Check version compatibility

```bash
pip install -r requirements.txt

# Verify critical packages
pip show python-telegram-bot  # Should be 21.8
pip show fastapi              # Should be 0.115.4
pip show asyncpg              # Should be 0.30.0
```

### 5. Code Integration ✅

- [ ] Update `main.py` with Telegram integration
- [ ] Update `config.py` with new settings
- [ ] Register Telegram routes
- [ ] Update health check endpoint

**Files to Modify:**

1. **src/api/main.py** - Add Telegram initialization
   ```python
   from src.api.telegram_integration import (
       initialize_telegram_bot,
       shutdown_telegram_bot,
       register_telegram_routes
   )
   ```

2. **src/api/config.py** - Add settings
   ```python
   TELEGRAM_WEBHOOK_URL: str = ""
   WEB_APP_URL: str = "http://localhost:3000"
   ```

### 6. Testing ✅

- [ ] Run unit tests
- [ ] Test authentication flow
- [ ] Test all bot commands
- [ ] Test transaction flow
- [ ] Test error handling
- [ ] Load test (100 concurrent users)

```bash
# Run all tests
pytest tests/test_telegram_bot.py -v

# Run with coverage
pytest tests/test_telegram_bot.py --cov=src.api --cov-report=html

# Load test
locust -f tests/load_test.py --headless -u 100 -r 10 --run-time 5m
```

### 7. Security Audit ✅

- [ ] Verify JWT secret is strong and unique
- [ ] Check rate limiting is enabled
- [ ] Verify authentication middleware works
- [ ] Test permission system
- [ ] Review audit logging
- [ ] Scan for SQL injection vulnerabilities
- [ ] Check input validation

```bash
# Security scan (optional)
bandit -r src/api/

# Check for secrets in code
git secrets --scan
```

### 8. Monitoring Setup ✅

- [ ] Configure Prometheus metrics
- [ ] Set up Grafana dashboards
- [ ] Configure alert rules
- [ ] Test health check endpoints
- [ ] Set up log aggregation

```bash
# Test health endpoint
curl http://localhost:8000/health/detailed

# Check Telegram status
curl http://localhost:8000/telegram/status
```

### 9. Documentation ✅

- [ ] Update README.md
- [ ] Document deployment process
- [ ] Create user guide for bot
- [ ] Document troubleshooting steps
- [ ] Create runbooks for common issues

### 10. Backup & Recovery ✅

- [ ] Set up database backups
- [ ] Test restore procedure
- [ ] Document rollback plan
- [ ] Create disaster recovery plan

---

## Deployment Steps

### Development Environment

```bash
# 1. Clone repository
git clone <repo-url>
cd project-aurum

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up environment
cp .env.example .env
# Edit .env with your values

# 5. Start services (Docker)
docker-compose up -d postgres redis

# 6. Run migrations
psql -U postgres -d project_aurum -f migrations/versions/001_telegram_bot_schema.sql

# 7. Start application
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

# 8. Test bot
# Open Telegram and search for your bot
# Send /start command
```

### Staging Environment

```bash
# 1. Pull latest code
git pull origin develop

# 2. Update dependencies
pip install -r requirements.txt --upgrade

# 3. Run migrations
alembic upgrade head

# 4. Run tests
pytest tests/ -v

# 5. Start with gunicorn
gunicorn src.api.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --log-level info

# 6. Smoke test
curl http://staging.yourdomain.com/health
curl http://staging.yourdomain.com/telegram/status
```

### Production Environment

```bash
# 1. Create release branch
git checkout -b release/v1.0.0

# 2. Update version
# Edit version in main.py and package.json

# 3. Tag release
git tag -a v1.0.0 -m "Release v1.0.0 with Telegram bot"
git push origin v1.0.0

# 4. Deploy to production
# Use your CI/CD pipeline or manual deployment

# 5. Set webhook (if using webhook mode)
curl -X POST "https://api.telegram.org/bot<TOKEN>/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{"url":"https://yourdomain.com/telegram/webhook"}'

# 6. Verify deployment
curl https://yourdomain.com/health/detailed
curl https://yourdomain.com/telegram/status

# 7. Monitor logs
tail -f logs/trading_system.log

# 8. Test in production
# Send /start command to bot
# Verify all commands work
```

---

## Post-Deployment Verification

### Functional Tests

- [ ] Bot responds to /start
- [ ] Authentication flow works end-to-end
- [ ] User can view signals via /signals
- [ ] Portfolio commands work
- [ ] Transaction flow (buy/sell/confirm) works
- [ ] Watchlist operations work
- [ ] Alert preferences can be updated
- [ ] Rate limiting triggers correctly

### Performance Tests

- [ ] Response time < 2 seconds (95th percentile)
- [ ] Can handle 100 concurrent users
- [ ] Database queries optimized
- [ ] Redis caching working
- [ ] No memory leaks

### Monitoring Checks

- [ ] Prometheus metrics being collected
- [ ] Grafana dashboards showing data
- [ ] Alerts configured and firing
- [ ] Logs being aggregated
- [ ] Error tracking active

### Security Checks

- [ ] Authentication required for protected commands
- [ ] Rate limiting prevents abuse
- [ ] No sensitive data in logs
- [ ] HTTPS enabled (production)
- [ ] Webhook signature verified (if using webhooks)

---

## Rollback Plan

If deployment fails or critical issues arise:

### Immediate Actions

1. **Disable Telegram bot**
   ```bash
   # Set in .env
   TELEGRAM_ENABLED=false

   # Restart application
   systemctl restart trading-system
   ```

2. **Switch to previous version**
   ```bash
   git checkout v0.9.0
   systemctl restart trading-system
   ```

3. **Notify users**
   - Send message via existing alert channels
   - Post status update
   - Inform team

### Database Rollback

```bash
# If schema changes need to be reverted
psql -U postgres -d project_aurum <<EOF
DROP TABLE IF EXISTS telegram_auth_tokens CASCADE;
DROP TABLE IF EXISTS pending_transactions CASCADE;
DROP TABLE IF EXISTS bot_command_log CASCADE;
DROP TABLE IF EXISTS telegram_preferences CASCADE;
ALTER TABLE users DROP COLUMN IF EXISTS telegram_chat_id;
ALTER TABLE users DROP COLUMN IF EXISTS telegram_username;
ALTER TABLE users DROP COLUMN IF EXISTS telegram_linked_at;
EOF
```

### Post-Rollback

1. Investigate issue
2. Fix in development
3. Test thoroughly
4. Re-deploy with fix

---

## Common Issues & Solutions

### Issue 1: Bot Not Responding

**Symptoms:** Bot doesn't reply to commands

**Solutions:**
1. Check `TELEGRAM_ENABLED=true` in `.env`
2. Verify bot token is correct
3. Check logs for errors: `tail -f logs/trading_system.log`
4. Test bot status: `curl http://localhost:8000/telegram/status`
5. Restart application

### Issue 2: Authentication Fails

**Symptoms:** Users can't link Telegram account

**Solutions:**
1. Verify `WEB_APP_URL` is correct in `.env`
2. Check `telegram_auth_tokens` table exists
3. Verify web app can reach API
4. Check token expiration (5 minutes)
5. Review browser console for errors

### Issue 3: Commands Return Errors

**Symptoms:** Commands work but return error messages

**Solutions:**
1. Verify database connection
2. Check user has required permissions
3. Review `bot_command_log` table for details
4. Check service initialization in logs
5. Verify all migrations ran successfully

### Issue 4: High Response Time

**Symptoms:** Bot takes >3 seconds to respond

**Solutions:**
1. Check database query performance
2. Verify Redis is running and connected
3. Review connection pool settings
4. Switch to webhook mode (production)
5. Increase worker count

### Issue 5: Rate Limiting Too Strict

**Symptoms:** Users frequently hit rate limits

**Solutions:**
1. Review rate limit settings in `telegram_bot_service.py`
2. Increase limits for specific command types
3. Implement user-specific rate limits
4. Add rate limit reset mechanism

---

## Maintenance Tasks

### Daily

- [ ] Check bot health status
- [ ] Review error logs
- [ ] Monitor response times
- [ ] Check active user count

### Weekly

- [ ] Review bot command statistics
- [ ] Analyze usage patterns
- [ ] Check for failed transactions
- [ ] Clean up expired auth tokens
- [ ] Review security logs

### Monthly

- [ ] Database performance tuning
- [ ] Update dependencies
- [ ] Review and update rate limits
- [ ] Analyze user feedback
- [ ] Update documentation

### Quarterly

- [ ] Security audit
- [ ] Load testing
- [ ] Disaster recovery drill
- [ ] Feature usage analysis
- [ ] Cost optimization review

---

## Support & Resources

### Documentation
- 📖 [Telegram Integration Guide](TELEGRAM_INTEGRATION_GUIDE.md)
- 📖 [Implementation Plan](TELEGRAM_BOT_IMPLEMENTATION_PLAN.md)
- 📖 [Quick Start Guide](TELEGRAM_BOT_QUICKSTART.md)
- 📖 [Test Results](TEST_RESULTS.md)

### Monitoring Dashboards
- Grafana: http://localhost:3000
- Prometheus: http://localhost:9090
- Bot Status: http://localhost:8000/telegram/status

### Useful Commands
```bash
# Check bot status
curl http://localhost:8000/telegram/status | jq

# View recent bot commands
psql -U postgres -d project_aurum -c "SELECT * FROM bot_command_log ORDER BY executed_at DESC LIMIT 10"

# View active Telegram users
psql -U postgres -d project_aurum -c "SELECT * FROM active_telegram_users"

# Check pending transactions
psql -U postgres -d project_aurum -c "SELECT * FROM pending_transactions WHERE status = 'pending'"

# View bot command analytics
psql -U postgres -d project_aurum -c "SELECT * FROM bot_command_analytics LIMIT 20"
```

---

## Success Metrics

Track these KPIs after deployment:

### User Engagement
- Bot activation rate (target: 80%)
- Daily active users (target: 60%)
- Commands per user per day (target: 8-10)
- Session length (target: 3-5 interactions)

### Performance
- Response time P95 (target: <2s)
- Command success rate (target: >95%)
- Uptime (target: 99.9%)
- Error rate (target: <0.1%)

### Business Impact
- Portfolio updates via Telegram (target: 70% of all updates)
- Signal adoption rate (target: 40% conversion)
- Support ticket reduction (target: -30%)

---

**Deployment Status**: ⏳ Ready for deployment

**Version**: 1.0.0

**Last Updated**: October 2, 2025
