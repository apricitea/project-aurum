# Auction Market Theory Engine

## Overview
The AMT engine transforms intraday OHLCV bars into structured market profiles that capture
value areas, point of control, and intraday behavior traits. This provides structural context
for both systematic signals and LLM agent narratives.

## Components
- `IntradayStockPrice` table (new) supplies high-frequency bars gathered in Phase 1.
- `AuctionMarketTheoryCalculator` (`src/domains/market_data/infrastructure/auction_market_theory.py`)
  computes profiles per session, including value area, POC, initial balance, and day type.
- `AuctionMarketTheoryService` (`src/domains/market_data/application/amt_service.py`) orchestrates
  batch computations and serves profile lookups.
- `AuctionMarketProfile` table (`src/api/database_extensions.py`) stores the derived metrics with
  JSON metadata for additional diagnostics (session range, single prints, etc.).
- `UnifiedDataPipeline` now calculates AMT profiles after intraday ingestion and exports them to the
  feature store (`data/feature_store/amt/`).

## Key Metrics
| Metric | Description |
| --- | --- |
| Point of Control | Price level with maximum traded volume |
| Value Area (High/Low) | 70% volume envelope around POC |
| Initial Balance | High/low of the first 60 minutes, indicating open drive |
| Profile Type | Heuristic classification (trend up/down, neutral, double distribution, normal) |
| VWAP & Session Range | Additional context for execution and volatility |
| Single Prints | Price levels with sparse participation, highlighting excess or rejection |

## Usage
- **Backtesting**: join `auction_market_profiles` with daily bars to analyze performance of AMT-driven filters.
- **Dashboard**: visualise value area bands, POC, and day type for contextual storytelling (Phase 4).
- **Agents**: incorporate AMT metrics into prompts to provide market structure awareness.

## Next Enhancements
1. Incorporate TPO-based calculations once tick data is available.
2. Detect multi-day balance transitions and failed auctions.
3. Integrate AMT signals into risk sizing heuristics within the signal generator.
