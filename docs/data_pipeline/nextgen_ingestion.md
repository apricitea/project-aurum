# Next-Generation Data Ingestion Overview

This document summarizes the upgraded data foundations that power Project Aurum's LLM agents and Auction Market Theory analytics.

## 1. Scope
- **Intraday OHLCV**: Five supported intervals (1m–60m) sourced from Yahoo Finance with hooks for IDX scraping.
- **Fundamentals**: Alpha Vantage coverage for annual and quarterly statements, with raw report provenance captured for reproducibility.
- **Market Narratives**: Aggregated Google News and Bisnis.com feeds with sentiment scoring tailored for financial text.
- **Feature Store**: Lightweight Parquet/CSV-backed store aligning datasets for ML, LLM, and AMT workloads.

## 2. Key Modules
| Module | Path | Description |
| --- | --- | --- |
| `IntradayPriceFetcher` | `src/data_pipeline/intraday_price_fetcher.py` | Fetches & upserts intraday bars with quality scoring |
| `FundamentalsIngestionService` | `src/data_pipeline/fundamentals_ingestion.py` | Collects Alpha Vantage payloads, normalizes metrics |
| `NewsIngestionService` | `src/data_pipeline/news_ingestion.py` | Scrapes news feeds, enriches articles with sentiment |
| `UnifiedDataPipeline` | `src/data_pipeline/unified_pipeline.py` | Orchestrates end-to-day cycle & feature-store exports |
| `FeatureStore` | `src/shared/feature_store/store.py` | Provides versioned dataset storage for downstream use |

## 3. Database Extensions
New SQLAlchemy models in `src/api/database_extensions.py`:
- `IntradayStockPrice`
- `MarketNewsArticle`
- `FundamentalReport`

These tables preserve data lineage via `DataRefreshLog` references and JSONB metadata for observability.

## 4. Feature Store Layout
```
data/feature_store/
├── ml/
│   ├── daily_prices-*.parquet
│   ├── fundamentals-*.parquet
│   └── daily manifest files
├── llm/
│   ├── stock_metadata-*.parquet
│   ├── news_articles-*.parquet
│   └── manifests
└── amt/
    └── (reserved for auction metrics in Phase 3)
```

## 5. Connectivity & Credentials
- Ensure outbound HTTPS access to the following domains (for Yahoo Finance and Google News fallbacks):
  - `query1.finance.yahoo.com`, `fc.yahoo.com`
  - `news.google.com`
  - `www.alphavantage.co`
- Provide the required API keys in `.env`:
  - `GOOGLE_API_KEY` for Gemini-powered agents and news sentiment.
  - `ALPHA_VANTAGE_API_KEY` for fundamentals ingestion (set `ALPHA_VANTAGE_ENABLED=true`).
- Optional IDX/OJK scraping requires stable access to `idx.co.id` and official filing portals; configure credentials where applicable.
- When network access is restricted, disable the affected fetchers via pipeline configuration to avoid partial runs.

## 6. Operational Notes
- Intraday fetch supports interval rotation; fallback scraper is stubbed for Phase 2 implementation.
- Fundamentals ingestion throttles API calls (12s) to honour Alpha Vantage free-tier limits.
- News sentiment prefers FinBERT; when unavailable, lexical heuristics provide deterministic scores.
- Unified pipeline exports curated datasets for agents (LLM) and models (ML), setting the stage for AMT-derived features.

## 7. Readiness Checklist
1. `uv sync` to install all dependencies from `pyproject.toml` (regenerate `uv.lock` if packages change).
2. Export credentials: `GOOGLE_API_KEY`, `ALPHA_VANTAGE_API_KEY`, and any IDX feed tokens.
3. Run `uv run python scripts/setup_stock_data_pipeline.py` to seed `stock_master`.
4. Execute the unified pipeline with the desired symbols:
   ```bash
   uv run python - <<'PY'
   from datetime import date
   from src.api.config import settings
   from src.data_pipeline.unified_pipeline import UnifiedDataPipeline, PipelineRunConfig
   pipeline = UnifiedDataPipeline(db_url=settings.get_database_url())
   pipeline.run_end_of_day(PipelineRunConfig(stock_codes=['BBCA','BBRI','TLKM']))
   PY
   ```
5. Verify readiness:
   ```bash
   sqlite3 data/trading_system.db "SELECT COUNT(*) FROM daily_stock_prices;"
   sqlite3 data/trading_system.db "SELECT COUNT(*) FROM intraday_stock_prices;"
   sqlite3 data/trading_system.db "SELECT COUNT(*) FROM auction_market_profiles;"
   ```
   All counts should be > 0 before enabling production signals.

## 8. Next Steps
1. Implement IDX scraper fallback for resilient intraday coverage.
2. Parse OJK/IDX filings into `FundamentalReport` storage.
3. Expand feature store tests & validation hooks for continuous integration.
4. Connect AMT calculations (Phase 3) to the reserved `amt` category.
