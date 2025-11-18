# Credentials & Connection Checklist

Use this checklist to keep track of all secrets and external connections required by Project Aurum. Populate them in your `.env` (or secret manager) before running production workloads.

| Category | Variable(s) | Purpose | Status |
|----------|-------------|---------|--------|
| **Database** | `DB_URL` | Primary SQL database connection (SQLite, Postgres, etc.) | ✅ Set to `sqlite:///data/trading_system.db` (local) |
| **LLM Provider** | `GOOGLE_API_KEY` | Gemini API key for multi-agent research | ✅ Supplied |
|  | `LLM_PROVIDER` | Must be `google` to use Gemini | ✅ Set |
|  | `OPENAI_API_KEY`, `ANTHROPIC_API_KEY` | Alternative LLMs (optional) | ⬜ Optional |
| **Market Data** | `ALPHA_VANTAGE_API_KEY` | Fundamentals/news ingestion | ⬜ Required for fundamentals pipeline |
|  | `IDX_API_KEY` | Official IDX feeds (optional fallback) | ⬜ Optional |
| **Notifications** | `EMAIL_ENABLED`, `EMAIL_CONFIG` | SMTP alerts | ⚠️ Currently enabled by default but lacks credentials |
|  | `TELEGRAM_ENABLED`, `TELEGRAM_BOT_TOKEN` | Telegram alerts | ⚠️ Enabled without token (disable or supply) |
|  | `SMS_ENABLED`, `TWILIO_CONFIG` | SMS alerts via Twilio | ⬜ Optional |
| **Webhooks** | `DEFAULT_WEBHOOK_URLS` | Slack/Teams/etc. | ⬜ Optional |
| **Caching / Queue** | `REDIS_*` | Redis connection (if using caching or Celery) | ⬜ Optional |
| **Monitoring** | `PROMETHEUS_*`, `GRAFANA_PASSWORD` | Observability stack | ⬜ Optional |
| **Backups** | `BACKUP_*` | Automated backup schedules | ⬜ Optional |

### Recommended Immediate Actions
1. **Disable unused channels**: Set `EMAIL_ENABLED=false`, `TELEGRAM_ENABLED=false`, `SMS_ENABLED=false` if you do not plan to send alerts yet. This suppresses configuration warnings.
2. **Provide fundamentals key**: Obtain an [Alpha Vantage](https://www.alphavantage.co/support/#api-key) key and set `ALPHA_VANTAGE_API_KEY` to enable fundamental ingestion.
3. **Database choice**: For production, replace the default SQLite URI with a managed Postgres instance.

Keep this document updated whenever new integrations are added.***
