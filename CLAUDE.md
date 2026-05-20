# Project Aurum — Developer Context

Indonesian Quantitative Trading Alert System for the IDX (Bursa Efek Indonesia).
Team repo with 4 collaborators (na-ive, mfalfath25, rizbud, apricitea).

---

## Stack

| Layer | Technology |
|---|---|
| API | FastAPI 0.115 + uvicorn/gunicorn |
| DB | PostgreSQL 15 (asyncpg + SQLAlchemy 2.0) |
| Migrations | Alembic — run `uv run alembic upgrade head` |
| Cache/Queue | Redis 7 (DB 1) + Celery 5 |
| ML | XGBoost, scikit-learn, statsmodels |
| AI Agents | LangChain 0.3 + LangGraph 0.4 |
| Notifications | Telegram bot (python-telegram-bot 21) |
| Frontend | React 18 + TypeScript + Vite + Tailwind |
| Dep mgmt | uv — always use `uv run` or `uv sync` |

---

## Database

```
Host: 127.0.0.1:5432
DB:   aurum
User: nyx (shared nyx-postgres container)
Password: from /home/vlain/infra/.env → POSTGRES_PASSWORD
```

All env vars in `/home/vlain/workspaces/project-aurum/.env`.

### Key tables
- `users` — auth + telegram integration (chat_id, username, linked_at)
- `trading_signals` — ML-generated BUY/SELL/HOLD signals with confidence scores
- `alerts` — user-facing trading alerts
- `portfolio` — user position tracking
- `risk_alerts` — automated risk breach notifications
- `telegram_preferences` — per-user bot config
- `pending_transactions` — 5-min TTL buy/sell confirmations
- `bot_command_log` — Telegram command audit log

---

## Dev Setup

```bash
cd /home/vlain/workspaces/project-aurum
uv sync                          # install deps
cp .env.example .env             # already done — .env exists
uv run uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

### Run migrations
```bash
uv run alembic upgrade head      # apply all pending migrations
uv run alembic revision --autogenerate -m "description"  # create new migration
```

### Run tests
```bash
uv run pytest tests/ -v
```

---

## Architecture

```
src/
  api/           — FastAPI app, auth, database, schemas, services
    main.py      — app entry point (celery_app exported here too)
    auth.py      — JWT + bcrypt auth (rounds=12), uses password_security.py
    database.py  — SQLAlchemy models + asyncpg pool (use get_db_manager() singleton)
    security_middleware.py — SecurityHeaders, RateLimiter, InputSanitizer
  data_pipeline/ — IDX data ingestion (Yahoo Finance, Alpha Vantage, news)
    unified_pipeline.py — main orchestrator: prices + intraday + fundamentals + news
  domains/
    ai_research/ — LangGraph research agents
    market_data/ — AMT (Auction Market Theory) profiles
    trading/     — ML signal generation, model ensemble
  shared/
    feature_store/ — ML feature export pipeline
```

---

## Git Workflow (Team Repo)

- **Always create a task branch**: `task/<queue_id>-<slug>`
- **Never push directly to main** without a PR
- **Autocommit format**: `git commit -m "description [nyx-auto]"`
- **PRs**: use `gh pr create` with descriptive body — the orchestrator handles this

---

## Key Constraints

- `ARRAY` type columns (telegram_preferences) need PostgreSQL — no SQLite fallback for those tables
- Market hours: IDX open Mon-Fri 09:00–15:49 WIB (Asia/Jakarta) — always use pytz for timezone math
- bcrypt rounds=12 everywhere — do not lower this
- Password policy: min 12 chars, uppercase + lowercase + digit + 2 special chars (enforced in auth.py)
- Celery app: `src.api.main:celery_app` — import this for any Celery task definitions
- DB pool: always use `get_db_manager()` from `database.py`, never instantiate `DatabaseManager()` directly in request handlers

---

## Documentation

All project docs live in `docs/`. Key files to read before working on each area:

| Area | Read first |
|---|---|
| Architecture | `docs/reference/architecture/system-overview.md` |
| API endpoints | `docs/reference/api/endpoints.md` |
| DB setup | `docs/how-to-guides/development/database-setup.md` |
| Frontend setup | `docs/how-to-guides/development/frontend-setup.md` |
| Running tests | `docs/how-to-guides/development/running-tests.md` |
| Deployment | `docs/how-to-guides/deployment/production-checklist.md` |
| AI research agents | `docs/reference/ai_research_agents.md` |
| Indonesian regulations | `docs/how-to-guides/compliance/indonesian-regulations.md` |
| Roadmap / changelog | `docs/project-meta/roadmap.md`, `docs/project-meta/changelog.md` |

---

## External APIs

| API | Env var | Status |
|---|---|---|
| Alpha Vantage | `ALPHA_VANTAGE_API_KEY` | Optional — fundamentals data |
| OpenAI | `OPENAI_API_KEY` | Optional — LangChain AI research |
| Anthropic | `ANTHROPIC_API_KEY` | Optional — Claude agent |
| Telegram | `TELEGRAM_BOT_TOKEN` | Optional — bot notifications |

All optional for dev. The pipeline falls back to Yahoo Finance if Alpha Vantage key is missing.
