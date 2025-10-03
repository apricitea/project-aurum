# Telegram Bot Implementation Plan
## Project Aurum - Interactive Trading Assistant

---

## Executive Summary

**Objective**: Transform the existing one-way Telegram alert system into a fully interactive trading assistant that allows users to query signals, manage portfolios, and receive personalized alerts through Telegram.

**Current State**:
- ✅ One-way alerts working (HIGH/CRITICAL priority only)
- ✅ TelegramNotifier class implemented
- ✅ Multi-channel alert infrastructure ready

**Target State**:
- ✅ Two-way interactive bot with command interface
- ✅ User authentication via Telegram
- ✅ Personalized portfolio management
- ✅ Real-time signal queries
- ✅ Custom alert preferences

---

## Strategic Goals & KPIs

### Goal 1: User Engagement
**Objective**: Increase platform interaction through accessible Telegram interface

**KPIs**:
- **Bot Activation Rate**: 80% of active users link their Telegram account within 30 days
- **Daily Active Users (DAU)**: 60% of registered users interact with bot daily
- **Command Usage**: Average 8-10 bot commands per user per day
- **Session Length**: Average 3-5 interactions per session

**Success Metrics**:
- ✅ 100+ bot commands processed daily (per 100 users)
- ✅ <2 second average response time
- ✅ 95%+ command success rate
- ✅ User satisfaction score >4.5/5

### Goal 2: Portfolio Management Accessibility
**Objective**: Enable mobile portfolio management without dashboard access

**KPIs**:
- **Mobile-First Adoption**: 70% of portfolio checks happen via Telegram vs web dashboard
- **Update Frequency**: Users check portfolio 3-5x daily via Telegram
- **Action Completion**: 90% of `/portfolio update` commands successfully execute
- **Data Accuracy**: 100% parity with web dashboard data

**Success Metrics**:
- ✅ Portfolio updates processed <3 seconds
- ✅ Position sync success rate >99%
- ✅ Zero data inconsistencies between Telegram and DB

### Goal 3: Signal Discovery & Actionability
**Objective**: Deliver trading signals instantly with context

**KPIs**:
- **Signal Delivery Speed**: Signals delivered <30 seconds after generation
- **Signal Click-Through**: 60% of signal recipients request detailed info
- **Conversion to Action**: 40% of high-confidence signals lead to portfolio updates
- **Signal Accuracy Tracking**: Real-time tracking of signal performance

**Success Metrics**:
- ✅ 95% of signals delivered within SLA (30s)
- ✅ Average signal confidence score >0.75
- ✅ <5% false positive rate (unprofitable signals)

### Goal 4: System Reliability & Security
**Objective**: Maintain production-grade uptime and data security

**KPIs**:
- **Uptime**: 99.9% bot availability (max 43 minutes downtime/month)
- **Security**: Zero unauthorized access incidents
- **Error Rate**: <0.1% failed commands due to system errors
- **Authentication Success**: 100% verified user access

**Success Metrics**:
- ✅ All Telegram users properly authenticated
- ✅ Rate limiting prevents abuse (<100 req/min per user)
- ✅ Audit log for all portfolio-modifying actions
- ✅ Encrypted sensitive data in transit and at rest

---

## Implementation Phases

### Phase 1: Foundation (Days 1-2)
**Objective**: Set up core bot infrastructure without breaking existing alerts

#### Deliverables:
1. ✅ Telegram bot service architecture
2. ✅ User authentication via Telegram
3. ✅ Basic command handlers (`/start`, `/help`, `/ping`)
4. ✅ Database schema updates (user-telegram linking)
5. ✅ Health checks and monitoring

#### KPIs:
- Bot responds to `/start` command <500ms
- 100% of test users successfully authenticate
- Zero disruption to existing alert delivery

#### Technical Tasks:
```python
# New files to create:
- src/api/telegram_bot_service.py      # Main bot service
- src/api/telegram_handlers.py         # Command handlers
- src/api/telegram_auth.py             # Authentication logic
- tests/test_telegram_bot.py           # Unit tests

# Database migrations:
- Add telegram_chat_id to users table
- Add telegram_subscriptions table
- Add bot_command_log table
```

---

### Phase 2: Read-Only Commands (Days 3-4)
**Objective**: Allow users to query data without modifying state

#### Deliverables:
1. ✅ `/signals` - Today's top trading signals
2. ✅ `/signals <STOCK>` - Specific stock signal
3. ✅ `/portfolio` - Current portfolio overview
4. ✅ `/risk` - Risk metrics and alerts
5. ✅ `/market` - Market status and overview

#### KPIs:
- Command response time <2 seconds (95th percentile)
- Data accuracy 100% vs API endpoints
- User satisfaction >4.5/5 for command clarity

#### Technical Implementation:
```python
# Command handlers integrate with existing services:

async def cmd_signals(update, context):
    """Get today's top signals"""
    # Call: signal_service.get_daily_signals()
    # Format: Top 10 BUY/SELL signals with confidence
    # Return: Formatted message with inline buttons

async def cmd_portfolio(update, context):
    """Show portfolio summary"""
    # Call: signal_service.get_portfolio_summary(user_id)
    # Format: Total value, P&L, top positions
    # Return: Summary + detailed positions option

async def cmd_risk(update, context):
    """Risk metrics overview"""
    # Call: alert_engine.get_active_risk_alerts()
    # Format: Sector concentration, volatility, drawdown
    # Return: Risk dashboard with warnings
```

---

### Phase 3: Portfolio Updates (Days 5-6)
**Objective**: Enable portfolio management via Telegram

#### Deliverables:
1. ✅ `/buy <STOCK> <QUANTITY> <PRICE>` - Add position
2. ✅ `/sell <STOCK> <QUANTITY> <PRICE>` - Close/reduce position
3. ✅ `/update <STOCK> <NEW_QUANTITY>` - Update existing position
4. ✅ Transaction confirmation flow (2-step verification)
5. ✅ Audit logging for all portfolio changes

#### KPIs:
- Transaction success rate >95%
- Average completion time <30 seconds (including confirmation)
- Zero unauthorized portfolio modifications
- 100% audit trail coverage

#### Security Implementation:
```python
# Two-step confirmation for portfolio changes:

async def cmd_buy(update, context):
    """Initiate buy transaction"""
    # Parse: stock_code, quantity, price
    # Validate: position limits, risk rules
    # Generate: confirmation code
    # Send: "Confirm purchase: /confirm ABC123"
    # Store: pending_transaction in Redis (TTL: 5 min)

async def cmd_confirm(update, context):
    """Confirm pending transaction"""
    # Verify: confirmation code
    # Check: user_id matches
    # Execute: portfolio update
    # Log: audit trail
    # Notify: success/failure
```

---

### Phase 4: Advanced Features (Days 7-8)
**Objective**: Personalization and advanced analytics

#### Deliverables:
1. ✅ `/subscribe <preferences>` - Custom alert preferences
2. ✅ `/watchlist <add/remove> <STOCK>` - Personal watchlist
3. ✅ `/performance <period>` - Portfolio performance charts
4. ✅ `/backtest <STOCK> <strategy>` - Quick strategy backtest
5. ✅ Inline keyboards for easier navigation

#### KPIs:
- 70% of users set custom alert preferences
- Average 5-8 stocks per watchlist
- Performance charts generated <5 seconds
- Backtest completion <10 seconds

#### Enhanced UX:
```python
# Inline keyboard example:

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

async def cmd_signals(update, context):
    signals = await get_signals()

    keyboard = [
        [
            InlineKeyboardButton("💰 BUY Signals", callback_data='filter_buy'),
            InlineKeyboardButton("📉 SELL Signals", callback_data='filter_sell')
        ],
        [
            InlineKeyboardButton("⭐ High Confidence Only", callback_data='filter_high_conf'),
            InlineKeyboardButton("📊 Detailed View", callback_data='view_detailed')
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Today's Signals:", reply_markup=reply_markup)
```

---

### Phase 5: Testing & Optimization (Days 9-10)
**Objective**: Ensure production readiness

#### Deliverables:
1. ✅ Comprehensive unit tests (>90% coverage)
2. ✅ Integration tests (end-to-end scenarios)
3. ✅ Load testing (100 concurrent users)
4. ✅ Security audit (authentication, rate limiting)
5. ✅ Performance optimization (caching, query optimization)
6. ✅ Documentation (user guide, API docs)

#### KPIs:
- Test coverage >90%
- Load test: 100 concurrent users, <3s response time
- Security scan: 0 critical/high vulnerabilities
- Documentation completeness: 100% of commands documented

#### Testing Strategy:
```python
# Test categories:

1. Unit Tests (pytest):
   - test_command_handlers.py
   - test_authentication.py
   - test_portfolio_updates.py
   - test_signal_formatting.py

2. Integration Tests:
   - test_end_to_end_buy_flow.py
   - test_alert_delivery.py
   - test_user_onboarding.py

3. Load Tests (locust):
   - 100 concurrent users
   - 1000 requests/minute
   - Sustained load for 10 minutes

4. Security Tests:
   - SQL injection attempts
   - Rate limit bypass attempts
   - Unauthorized access tests
```

---

## Technical Architecture

### System Design

```
┌─────────────────────────────────────────────────────────────────┐
│                        TELEGRAM CLIENT                          │
│                    (User's Telegram App)                        │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             │ HTTPS (Webhook or Polling)
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                   TELEGRAM BOT SERVICE                          │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  TelegramBotService                                       │  │
│  │  - Command Router                                         │  │
│  │  - Authentication Middleware                              │  │
│  │  - Rate Limiter                                           │  │
│  │  - Error Handler                                          │  │
│  └────────────┬─────────────────────────────────────────────┘  │
└───────────────┼────────────────────────────────────────────────┘
                │
                │ (Command Dispatch)
                │
┌───────────────▼────────────────────────────────────────────────┐
│                    COMMAND HANDLERS                            │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────────────────┐   │
│  │ SignalCmd   │  │PortfolioCmd │  │  RiskCmd             │   │
│  │ - /signals  │  │ - /portfolio│  │  - /risk             │   │
│  │ - /stock    │  │ - /buy      │  │  - /alerts           │   │
│  │             │  │ - /sell     │  │                      │   │
│  └──────┬──────┘  └──────┬──────┘  └──────┬───────────────┘   │
└─────────┼────────────────┼────────────────┼────────────────────┘
          │                │                │
          │                │                │
┌─────────▼────────────────▼────────────────▼────────────────────┐
│                     EXISTING SERVICES                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐ │
│  │SignalService │  │DatabaseMgr   │  │  AlertEngine         │ │
│  │              │  │              │  │                      │ │
│  └──────────────┘  └──────────────┘  └──────────────────────┘ │
└────────────────────────────┬───────────────────────────────────┘
                             │
                             │
┌────────────────────────────▼───────────────────────────────────┐
│                  DATA LAYER                                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐ │
│  │ PostgreSQL   │  │    Redis     │  │  External APIs       │ │
│  │              │  │   (Cache)    │  │  (IDX, Yahoo)        │ │
│  └──────────────┘  └──────────────┘  └──────────────────────┘ │
└────────────────────────────────────────────────────────────────┘
```

### Database Schema Updates

```sql
-- Link Telegram accounts to users
ALTER TABLE users ADD COLUMN telegram_chat_id BIGINT UNIQUE;
ALTER TABLE users ADD COLUMN telegram_username VARCHAR(100);
ALTER TABLE users ADD COLUMN telegram_linked_at TIMESTAMP;

-- User preferences for bot
CREATE TABLE telegram_preferences (
    id SERIAL PRIMARY KEY,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    alert_types TEXT[],              -- ['high_confidence', 'risk_breach', 'large_position']
    signal_filter VARCHAR(20),       -- 'all', 'buy_only', 'sell_only', 'high_confidence'
    notification_hours INTEGER[],    -- [9, 10, 11, 14, 15] (WIB hours)
    watchlist TEXT[],                -- ['BBCA.JK', 'BMRI.JK', 'TLKM.JK']
    language VARCHAR(10) DEFAULT 'id', -- 'id' (Indonesian) or 'en' (English)
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Audit log for bot commands
CREATE TABLE bot_command_log (
    id SERIAL PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    telegram_chat_id BIGINT,
    command VARCHAR(100),
    parameters JSONB,
    response_status VARCHAR(20),     -- 'success', 'error', 'unauthorized'
    response_time_ms INTEGER,
    error_message TEXT,
    executed_at TIMESTAMP DEFAULT NOW()
);

-- Pending transactions (for 2-step confirmation)
CREATE TABLE pending_transactions (
    id SERIAL PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    transaction_type VARCHAR(20),    -- 'buy', 'sell', 'update'
    stock_code VARCHAR(10),
    quantity INTEGER,
    price FLOAT,
    confirmation_code VARCHAR(20) UNIQUE,
    created_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP,
    confirmed_at TIMESTAMP,
    status VARCHAR(20) DEFAULT 'pending'  -- 'pending', 'confirmed', 'expired', 'cancelled'
);

-- Indexes for performance
CREATE INDEX idx_telegram_prefs_user ON telegram_preferences(user_id);
CREATE INDEX idx_bot_log_user_time ON bot_command_log(user_id, executed_at DESC);
CREATE INDEX idx_pending_trans_user ON pending_transactions(user_id, status);
CREATE INDEX idx_pending_trans_code ON pending_transactions(confirmation_code);
```

---

## Security & Compliance

### Authentication Flow

```python
# 1. User initiates /start command
User → Telegram: "/start"

# 2. Bot generates authentication token
Bot → Database: CREATE auth_token FOR telegram_chat_id
Bot → User: "Visit: https://aurum.app/telegram-auth?token=ABC123"

# 3. User visits web link, logs in
User → Web App: Login with credentials
Web App → Database: VERIFY token, LINK telegram_chat_id to user_id
Web App → User: "✅ Telegram linked successfully!"

# 4. Bot confirms authentication
Bot → User: "✅ Authentication complete! Try /help"

# Alternative: Admin-based verification
Admin → Dashboard: Approve telegram_chat_id → user_id mapping
Bot → User: "✅ Verified by admin!"
```

### Security Measures

1. **Authentication**:
   - Required for all commands except `/start`, `/help`
   - JWT-based token verification
   - Session timeout: 7 days
   - Re-authentication for sensitive actions

2. **Authorization**:
   - Role-based access (Admin, Trader, Viewer)
   - Command-level permissions
   - Portfolio updates only for owners
   - Audit trail for all actions

3. **Rate Limiting**:
   ```python
   # Per user limits:
   - 60 requests/minute (general)
   - 10 requests/minute (portfolio updates)
   - 100 requests/hour (signal queries)

   # Global limits:
   - 1000 requests/minute (bot-wide)
   - Exponential backoff on rate limit
   ```

4. **Data Protection**:
   - No sensitive data in Telegram messages
   - Encrypted confirmation codes
   - Automatic message deletion (sensitive data)
   - GDPR compliance (data export/delete)

5. **Error Handling**:
   ```python
   # Never expose internal errors to users
   try:
       result = await execute_command()
   except ValidationError as e:
       await send_user_friendly_error(e)
   except Exception as e:
       logger.error(f"Internal error: {e}")
       await send_generic_error()
   ```

---

## Monitoring & Observability

### Metrics to Track

```python
# Prometheus metrics to add:

# Command metrics
telegram_commands_total = Counter(
    'telegram_commands_total',
    'Total bot commands processed',
    ['command', 'status']
)

telegram_command_duration = Histogram(
    'telegram_command_duration_seconds',
    'Command processing duration',
    ['command']
)

# User metrics
telegram_active_users = Gauge(
    'telegram_active_users',
    'Number of active Telegram users'
)

telegram_auth_attempts = Counter(
    'telegram_auth_attempts_total',
    'Authentication attempts',
    ['status']
)

# Transaction metrics
telegram_portfolio_updates = Counter(
    'telegram_portfolio_updates_total',
    'Portfolio updates via Telegram',
    ['type', 'status']
)

# Error metrics
telegram_errors = Counter(
    'telegram_errors_total',
    'Telegram bot errors',
    ['error_type']
)
```

### Grafana Dashboard

**Panels to create**:
1. **Bot Health**:
   - Uptime percentage
   - Error rate (5xx, 4xx)
   - Average response time
   - Active connections

2. **User Engagement**:
   - Daily active users (DAU)
   - Commands per user
   - Most used commands
   - Authentication success rate

3. **Portfolio Activity**:
   - Buy/sell transactions per day
   - Transaction success rate
   - Average transaction value
   - Position update frequency

4. **Performance**:
   - P95 response time per command
   - Database query time
   - Redis cache hit rate
   - External API latency

5. **Alerts**:
   - High error rate (>5%)
   - Slow responses (>3s P95)
   - Authentication failures spike
   - Unusual command patterns

---

## Rollout Strategy

### Phase 1: Alpha Testing (Internal)
**Duration**: Days 1-3
**Participants**: 3-5 internal users
**Focus**: Core functionality, bug identification

**Entry Criteria**:
- ✅ All basic commands working
- ✅ Authentication flow complete
- ✅ Unit tests passing

**Success Criteria**:
- Zero critical bugs
- <2 second average response time
- 100% authentication success

### Phase 2: Beta Testing (Limited)
**Duration**: Days 4-6
**Participants**: 20-30 selected users
**Focus**: Real-world usage, edge cases

**Entry Criteria**:
- ✅ Alpha testing complete
- ✅ Portfolio updates working
- ✅ Monitoring dashboard live

**Success Criteria**:
- <5 bugs per 100 commands
- 95% user satisfaction
- Zero security issues

### Phase 3: General Availability
**Duration**: Day 7+
**Participants**: All users
**Focus**: Scale, stability

**Entry Criteria**:
- ✅ Beta testing successful
- ✅ Load testing passed
- ✅ Documentation complete

**Success Criteria**:
- 99.9% uptime
- <0.1% error rate
- >4.5/5 user rating

### Rollback Plan
```python
# If critical issues arise:

1. Immediate Actions:
   - Disable bot webhook
   - Revert to alert-only mode
   - Notify users via existing channels

2. Investigation:
   - Review error logs
   - Analyze failed transactions
   - Identify root cause

3. Fix & Redeploy:
   - Apply hotfix
   - Test in staging
   - Gradual re-enablement

4. Post-Mortem:
   - Document incident
   - Update runbooks
   - Improve monitoring
```

---

## Success Criteria & Exit Conditions

### Must-Have (Phase 1-2)
- [x] ✅ Users can authenticate via Telegram
- [x] ✅ `/signals` returns today's top 10 signals
- [x] ✅ `/portfolio` shows accurate portfolio summary
- [x] ✅ `/risk` displays current risk metrics
- [x] ✅ All commands respond <2 seconds
- [x] ✅ Zero data inconsistencies with web app
- [x] ✅ Existing alert system unaffected

### Should-Have (Phase 3-4)
- [x] ✅ Users can update portfolios via `/buy`, `/sell`
- [x] ✅ Two-step confirmation for transactions
- [x] ✅ Custom alert preferences via `/subscribe`
- [x] ✅ Personal watchlists via `/watchlist`
- [x] ✅ Inline keyboards for better UX
- [x] ✅ Audit logging for compliance

### Nice-to-Have (Phase 5+)
- [x] ✅ Performance charts via `/performance`
- [x] ✅ Quick backtests via `/backtest`
- [x] ✅ Multi-language support (ID/EN)
- [x] ✅ Voice command support
- [x] ✅ Integration with broker APIs

### Exit Conditions (Project Complete)
1. ✅ All must-have features deployed
2. ✅ 80% of users activated Telegram bot
3. ✅ 99.9% uptime for 30 consecutive days
4. ✅ User satisfaction >4.5/5
5. ✅ Zero critical security incidents
6. ✅ Performance KPIs met for 14 days
7. ✅ Documentation 100% complete
8. ✅ Team trained on maintenance

---

## Risk Management

### Identified Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| **Breaking existing alerts** | Critical | Medium | Thorough testing, feature flags, rollback plan |
| **Authentication bypass** | Critical | Low | Security audit, penetration testing |
| **Database performance degradation** | High | Medium | Query optimization, read replicas, caching |
| **Rate limit abuse** | Medium | High | Implement strict rate limiting, monitoring |
| **Data inconsistency** | High | Low | Transactions, validation, reconciliation jobs |
| **Bot API changes** | Medium | Low | Version pinning, upgrade testing |
| **User confusion** | Medium | Medium | Clear documentation, onboarding flow |
| **Scale issues (>1000 users)** | High | Medium | Load testing, horizontal scaling plan |

### Mitigation Strategies

1. **Feature Flags**:
   ```python
   TELEGRAM_BOT_ENABLED = os.getenv("TELEGRAM_BOT_ENABLED", "false")
   TELEGRAM_PORTFOLIO_UPDATES_ENABLED = os.getenv("TELEGRAM_PORTFOLIO_UPDATES", "false")
   ```

2. **Circuit Breaker**:
   ```python
   # Auto-disable on high error rate
   if error_rate > 0.05:  # 5% errors
       disable_bot()
       alert_team()
   ```

3. **Gradual Rollout**:
   ```python
   # Percentage-based enablement
   enabled_percentage = 0.1  # Start with 10% of users
   if user_id % 10 < enabled_percentage * 10:
       enable_telegram_bot(user)
   ```

---

## Timeline & Milestones

### Week 1: Foundation & Read-Only
| Day | Milestone | Deliverable | Owner |
|-----|-----------|-------------|-------|
| 1 | Bot infrastructure | Service setup, auth flow | Backend Team |
| 2 | Basic commands | /start, /help, /ping | Backend Team |
| 3 | Signal commands | /signals, /stock | Backend Team |
| 4 | Portfolio/Risk commands | /portfolio, /risk | Backend Team |
| 5 | Testing & refinement | Unit tests, bug fixes | QA Team |

### Week 2: Portfolio Updates & Launch
| Day | Milestone | Deliverable | Owner |
|-----|-----------|-------------|-------|
| 6 | Portfolio updates | /buy, /sell, confirmation | Backend Team |
| 7 | Advanced features | /subscribe, /watchlist | Backend Team |
| 8 | Load testing | 100 concurrent users | QA Team |
| 9 | Beta launch | 30 selected users | Product Team |
| 10 | GA launch | All users enabled | Product Team |

---

## Budget & Resources

### Development Resources
- **Backend Developer**: 10 days × 8 hours = 80 hours
- **QA Engineer**: 5 days × 6 hours = 30 hours
- **DevOps Engineer**: 3 days × 4 hours = 12 hours
- **Product Manager**: 10 days × 2 hours = 20 hours

**Total**: 142 person-hours

### Infrastructure Costs (Monthly)
- **Telegram Bot API**: Free (official API)
- **Additional Redis Cache**: ~$10/month (increased memory)
- **Database Storage**: ~$5/month (additional tables)
- **Monitoring (Grafana Cloud)**: ~$15/month
- **SMS Alerts (Twilio)**: ~$20/month (100 critical alerts)

**Total**: ~$50/month

### ROI Projection
**Increased User Engagement**:
- Current: 20% daily active users
- Target: 60% daily active users
- Value: 3x engagement → better signal adoption → higher trading volume

**Reduced Support Burden**:
- Self-service via Telegram: -30% support tickets
- Estimated savings: 10 hours/month support time

**Improved Signal Execution**:
- Faster signal delivery: -5 minutes avg response time
- Better execution prices: ~0.5% improvement
- For $100K portfolio: ~$500/month value

---

## Appendix: Command Reference

### User Commands

| Command | Description | Example | Auth Required |
|---------|-------------|---------|---------------|
| `/start` | Initialize bot, get auth link | `/start` | No |
| `/help` | Show command list | `/help` | No |
| `/login <token>` | Authenticate with token | `/login ABC123` | No |
| `/signals` | Today's top signals | `/signals` | Yes |
| `/signals <STOCK>` | Specific stock signal | `/signals BBCA` | Yes |
| `/portfolio` | Portfolio overview | `/portfolio` | Yes |
| `/buy <STOCK> <QTY> <PRICE>` | Initiate buy | `/buy BBCA 1000 4500` | Yes |
| `/sell <STOCK> <QTY> <PRICE>` | Initiate sell | `/sell BBCA 500 4600` | Yes |
| `/confirm <CODE>` | Confirm transaction | `/confirm XYZ789` | Yes |
| `/risk` | Risk metrics | `/risk` | Yes |
| `/watchlist` | Show watchlist | `/watchlist` | Yes |
| `/watchlist add <STOCK>` | Add to watchlist | `/watchlist add TLKM` | Yes |
| `/subscribe` | Alert preferences | `/subscribe` | Yes |
| `/market` | Market status | `/market` | Yes |
| `/performance <PERIOD>` | Performance charts | `/performance 7d` | Yes |

### Admin Commands

| Command | Description | Example | Role Required |
|---------|-------------|---------|---------------|
| `/admin stats` | Bot statistics | `/admin stats` | Admin |
| `/admin users` | Active users list | `/admin users` | Admin |
| `/admin verify <CHAT_ID> <USER_ID>` | Manual verification | `/admin verify 123456 uuid` | Admin |
| `/admin broadcast <MSG>` | Send to all users | `/admin broadcast "Maintenance at 10 PM"` | Admin |
| `/admin disable <USER_ID>` | Disable user access | `/admin disable uuid` | Admin |

---

## Glossary

- **DAU**: Daily Active Users
- **P95**: 95th percentile (performance metric)
- **TTL**: Time To Live (cache expiration)
- **IDX**: Indonesia Stock Exchange
- **WIB**: Western Indonesian Time (UTC+7)
- **LQ45**: 45 most liquid stocks on IDX
- **OHLCV**: Open, High, Low, Close, Volume (price data)
- **P&L**: Profit and Loss
- **Sharpe Ratio**: Risk-adjusted return metric

---

**Document Version**: 1.0
**Last Updated**: October 2, 2025
**Status**: Ready for Implementation
**Approval Required**: Product Owner, Tech Lead

---

## Next Steps

1. **Review & Approve Plan**: Stakeholder sign-off
2. **Create Development Branch**: `feature/telegram-bot-v1`
3. **Set Up Monitoring**: Grafana dashboards, alerts
4. **Begin Phase 1**: Bot infrastructure setup
5. **Schedule Daily Standups**: Track progress, blockers

**Let's build an amazing Telegram trading assistant! 🚀**