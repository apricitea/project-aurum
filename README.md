# Project Aurum

A quantitative trading system for the Indonesian Stock Exchange (IDX): ensemble ML signal generation, a FastAPI backend, a React/TypeScript dashboard, and multi-channel alerting, structured as a domain-driven Python monorepo.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)

## Quick start

Dependency management is via [uv](https://github.com/astral-sh/uv).

```bash
git clone https://github.com/apricitea/project-aurum.git
cd project-aurum

uv sync
uv run python scripts/setup_stock_data_pipeline.py  # bootstrap DB + seed IDX master data

docker-compose up -d
```

- API: `http://localhost:8000`
- Dashboard: `http://localhost:3000`

## Architecture

Domain-driven design, split by bounded context:

```
src/
├── domains/
│   ├── trading/          # signal generation, ML models
│   ├── market_data/      # IDX feeds, data validation
│   ├── risk_management/  # position limits, drawdown rules
│   ├── user_management/  # auth
│   └── analytics/        # backtesting, performance
├── shared/                # db, messaging, external APIs, monitoring
└── api/                   # FastAPI entry point, routers

apps/web_dashboard/        # React + TypeScript frontend
infrastructure/            # docker, k8s, terraform, monitoring configs
```

## Features

- Ensemble ML trading signals over IDX data
- Real-time dashboard (React/TypeScript)
- Risk management (position limits, drawdown controls)
- Alerting via email, Telegram, SMS
- IDX-specific: LQ45 focus, WIB timezone, IDR native

## Configuration

Copy `.env.example` to `.env` and set the keys you need — most integrations (alerts, alternative LLM backends, official IDX data feed) are optional and can be left disabled. See `docs/operations/credentials_checklist.md`.

## Status

Personal project, not backtested/validated against live market data yet — treat performance as unproven until stated otherwise here.

## Development

```bash
# Backend
cd src && uvicorn api.main:app --reload

# Frontend
cd apps/web_dashboard && npm run dev

# Tests
pytest src/
```

## License

MIT — see [LICENSE](LICENSE).
