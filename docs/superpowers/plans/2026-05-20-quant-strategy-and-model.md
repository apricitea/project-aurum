# Quantitative Trading Strategy & Model Architecture Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Evolve Project Aurum from a basic ML signal system into a production-grade quantitative trading alert system using multi-asset data (IDX stocks + gold + forex + crypto), best-practice labeling, walk-forward validation, and a proper backtesting engine.

**Architecture:** Three independent layers — (1) a multi-asset data pipeline feeding gold, forex, and crypto prices into the DB, (2) a feature engineering overhaul that replaces placeholder cross-asset stubs with real computed features and fixes labeling, and (3) a model pipeline that replaces the naive train/test approach with walk-forward validation, LightGBM, a meta-labeler, and a backtesting engine with transaction costs. Each layer is a separate implementation sub-plan.

**Tech Stack:** yfinance (gold/forex), Binance REST API (crypto), LightGBM, pytorch-forecasting (TFT), vectorbt (backtesting), SHAP, scikit-learn (walk-forward CV)

---

## Part 0: Scope Assessment & Realism Check

### What "high-frequency trading" actually means here

**True HFT (microsecond execution) is not feasible from this setup:**
- IDX does not expose order book depth or tick data to retail participants
- Network latency from a homelab rules out sub-second execution
- True HFT requires co-location at the exchange, specialized hardware, and direct market access

**What IS feasible — and still highly alpha-generative:**

| Style | Hold period | Data needed | Feasibility |
|---|---|---|---|
| Intraday swing | 30 min – 1 day | 1m, 5m bars | ✅ fully feasible |
| Multi-day swing | 1–10 days | 1h, daily bars | ✅ current focus |
| Position trading | weeks–months | daily, fundamentals | ✅ fully feasible |
| True HFT | microseconds | tick data + co-location | ❌ not feasible from homelab |

**Decision: build for intraday swing + multi-day swing.** This is where the new multi-asset data (gold, forex, crypto) provides the most edge.

---

## Part 1: What Each Asset Class Actually Tells Us

### Gold (XAU/USD)
- **Risk-off indicator**: when global risk appetite falls, gold rises and IDX falls
- **Inflation hedge**: rising gold → inflation pressure → Bank Indonesia rate hike risk → banking stocks (BBCA, BBRI) underperform
- **IDR-gold**: gold priced in IDR is a direct inflation/currency signal for Indonesian investors
- **Useful for**: macro regime detection, sector rotation signals (mining vs financials)

### USD/IDR (and EUR/IDR, JPY/IDR)
- **Strongest macro driver for IDX** — directly affects:
  - Import-heavy stocks (UNVR, ICBP, HMSP): hurt by weak IDR (higher input costs)
  - Export stocks (ADRO, PTBA, INCO): helped by weak IDR (revenues in USD)
  - Banking stocks: IDR weakness = BI rate hike risk = NIM compression
- **IDR momentum**: consecutive days of IDR weakening → risk-off signal for the whole IDX
- **Useful for**: sector rotation, risk adjustment of position sizes

### Bitcoin / Crypto (BTC, ETH)
- **Risk-on/risk-off barometer**: BTC leads global risk appetite by 1–24h
- **Correlation with GOTO, BUKA, EMTK** (Indonesian tech stocks) is measurable
- **BTC volatility (30d)** is a useful global risk regime feature
- **NOT a direct trading signal for IDX** — use as a feature, not as primary signal

### High-frequency data usage (1m, 5m, 1h bars)
- 1m crypto (Binance): BTC opening range breakout as intraday sentiment signal
- 5m IDX stocks: opening auction momentum, VWAP deviation, intraday mean reversion
- 1h gold: session-to-session range for intraday volatility estimation
- **Retention policy**: 1m data → keep 60 days; 1h data → keep 1 year; daily → forever

---

## Part 2: Current Model Problems (What Must Be Fixed)

### Problem 1: Naive labeling (CRITICAL)
**Current code** (`model_ensemble.py:80`):
```python
targets = pd.qcut(forward_returns, q=4, labels=['Sell', 'Hold', 'Buy', 'Strong_Buy'])
```
**Why this is wrong:**
- Forces equal class distribution regardless of market conditions
- Ignores that a +1% return in a low-vol regime is very different from +1% in a high-vol regime
- No consideration of path — the stock might go -5% before recovering to +2%
- Creates overlapping labels across training samples (look-ahead bias if not handled)

**Fix: Triple-Barrier Labeling** (Advances in Financial Machine Learning, López de Prado 2018)
```
For each bar, set three barriers:
  - Upper barrier: +pt (profit-take, e.g. +2% × ATR ratio)
  - Lower barrier: -sl (stop-loss, e.g. -1% × ATR ratio)  
  - Vertical barrier: max holding days (e.g. 20 days)
Label = +1 if upper barrier hit first
Label = -1 if lower barrier hit first  
Label =  0 if vertical barrier hit first (time exit)
```
This produces labels that reflect actual tradeable outcomes.

### Problem 2: Training/validation data leakage
**Current code**: `TimeSeriesSplit(n_splits=5)` — better than random split but still leaks because:
- Adjacent samples are highly correlated (autocorrelation in price data)
- There's no embargo gap between train and test folds

**Fix: Walk-Forward Validation with Purging**
```
Train window: rolling 252 days (1 year)
Test window: next 63 days (1 quarter)
Embargo: 5 days between train end and test start
Repeat until end of data
```

### Problem 3: No backtesting
Currently the system generates signals but there is no way to know if they would have been profitable after:
- IDX brokerage commission: ~0.15% buy + 0.25% sell = 0.4% round-trip
- Market impact / slippage: ~0.1–0.3% for small-mid cap
- Min lot size: 100 shares (must be accounted for in position sizing)

Without this, we cannot know if signals actually generate alpha or if they're noise.

### Problem 4: Cross-asset features are stubs
`feature_engineering.py:182–194` is entirely placeholder comments. The new data pipeline (sub-plan A) enables filling these in properly.

### Problem 5: Model is missing a temporal component
XGBoost/RandomForest treat each row independently. They can't capture:
- Multi-day momentum patterns
- Volatility clustering
- Regime persistence

A sequence model (LSTM or Temporal Fusion Transformer) captures these patterns.

---

## Part 3: Recommended Target Architecture

```
Multi-Asset Data Layer
├── IDX stocks (daily + 5m intraday)          [EXISTS]
├── Gold (daily + 1h)                          [SUB-PLAN A]
├── Forex: USDIDR, EURUSD, JPYIDR (daily + 1h)[SUB-PLAN A]
└── Crypto: BTC, ETH (daily + 1m via Binance) [SUB-PLAN A]

Feature Engineering Layer
├── Price features: multi-timeframe returns    [SUB-PLAN B]
│   (1d, 5d, 10d, 20d, 60d returns + vols)
├── Technical indicators: RSI, MACD, BB, ATR  [EXISTS - keep]
├── Cross-asset features (filled, not stubs)   [SUB-PLAN B]
│   (gold/stock correlation, IDR momentum,
│    BTC risk-on score, sector relative strength)
├── Fundamental: P/E, P/B, ROE, growth        [EXISTS - keep]
├── Market regime: volatility regime,          [SUB-PLAN B]
│   trend strength, BTC regime
└── Triple-barrier labels                      [SUB-PLAN C]

Model Pipeline
├── Layer 1 — LightGBM tabular model          [SUB-PLAN C]
│   (replaces XGBoost/RF/GB ensemble)
│   Input: all engineered features
│   Output: directional signal + confidence
├── Layer 2 — Temporal Fusion Transformer     [SUB-PLAN C]
│   (optional, for stocks with sufficient data)
│   Input: 60-day look-back sequences
│   Output: multi-horizon forecast + uncertainty
├── Layer 3 — Meta-Labeler                    [SUB-PLAN C]
│   Input: Layer 1+2 signals + market regime
│   Output: "is this signal reliable?" (0/1)
│   (prevents signal in bad market conditions)
└── Ensemble: weighted average, calibrated    [SUB-PLAN C]
    on walk-forward OOS results

Validation & Backtesting
├── Walk-Forward engine                        [SUB-PLAN C]
│   (train 252d, test 63d, embargo 5d)
├── Backtest engine (vectorbt)                 [SUB-PLAN C]
│   - Commission: 0.15% buy + 0.25% sell
│   - Slippage: 0.2% per trade
│   - Min lot: 100 shares
│   - Max position: 5% of portfolio
└── Performance metrics                        [SUB-PLAN C]
    Sharpe, Calmar, max drawdown, win rate,
    profit factor, average hold time

Risk & Execution
├── Position sizing: Kelly(1/4 fraction)       [EXISTS - keep]
├── Portfolio heat: max 6% total risk          [EXISTS - keep]
├── Regime gate: no new positions if           [SUB-PLAN C]
│   meta-labeler confidence < threshold
└── Telegram alerts with backtest context      [EXISTS - wire in]
```

---

## Sub-Plan Breakdown

This work spans three independent implementation sub-plans. Each can be built and deployed independently.

### Sub-Plan A: Multi-Asset Data Pipeline
**File:** `docs/superpowers/plans/2026-05-20-multi-asset-data-pipeline.md`

**Scope:**
- New DB tables: `GoldPrice`, `ForexRate`, `CryptoPrice` (with `interval` column: 1m, 1h, 1d)
- New fetchers: `GoldFetcher` (yfinance), `ForexFetcher` (yfinance), `CryptoFetcher` (Binance REST)
- Binance websocket service (`nyx-aurum-crypto-stream.service`) for live 1m BTC/ETH data
- Wire into `UnifiedDataPipeline.run_end_of_day()`
- Retention policy enforced by a daily cleanup job (1m data > 60 days → delete)
- **Estimated data volume**: ~2M rows/year for 1m crypto (5 pairs × 1440 bars/day × 365)

**Key assets to fetch:**
```python
GOLD   = ["GC=F"]                              # Gold futures (daily + 1h via yfinance)
FOREX  = ["USDIDR=X", "EURUSD=X", "JPYIDR=X", # yfinance (daily + 1h)
          "GBPIDR=X", "CNHIDR=X"]
CRYPTO = ["BTCUSDT", "ETHUSDT", "BNBUSDT",    # Binance (daily + 1m + live stream)
          "SOLUSDT", "XRPUSDT"]
```

### Sub-Plan B: Feature Engineering Overhaul
**File:** `docs/superpowers/plans/2026-05-20-feature-engineering-overhaul.md`

**Scope:**
- Modify `src/domains/market_data/application/feature_engineering.py`
- Fill in `_add_cross_asset_features()` with real computed features from Sub-Plan A data
- Add `_add_regime_features()` — market regime detection (volatility regime, trend regime)
- Add `_add_multiframe_features()` — 5d, 10d, 20d, 60d returns and rolling volatilities
- Add `TripleBarrierLabeler` class — proper event-driven labeling
- Update `FeatureStore` export to include cross-asset features

**New features (21 new features beyond current):**
```
Cross-asset (requires Sub-Plan A data):
  usdidr_1d_return, usdidr_5d_return, usdidr_vol_20d
  gold_1d_return, gold_5d_return, gold_vs_usdidr_ratio
  btc_1d_return, btc_vol_30d, btc_regime (bull/bear/neutral)
  stock_btc_corr_20d, stock_gold_corr_20d

Multi-timeframe returns:
  return_5d, return_10d, return_20d, return_60d
  vol_5d, vol_20d, vol_60d
  momentum_zscore_20d (price vs 20d SMA in vol units)

Regime:
  market_regime (0=low_vol, 1=normal, 2=high_vol)
  trend_strength (ADX-derived)
```

### Sub-Plan C: Model Pipeline Overhaul & Backtesting
**File:** `docs/superpowers/plans/2026-05-20-model-pipeline-overhaul.md`

**Scope:**
- `TripleBarrierLabeler` integration (from Sub-Plan B)
- `WalkForwardValidator` — rolling train/test with embargo
- Replace current sklearn ensemble with `LightGBMSignalModel`
- `MetaLabeler` — secondary LightGBM predicting signal reliability
- `BacktestEngine` using vectorbt — transaction costs, slippage, lot sizes
- SHAP-based feature importance reporting
- Updated `SignalGenerator` to use new model pipeline
- Performance dashboard output (Sharpe, Calmar, max drawdown, win rate)

**New dependencies:**
```
lightgbm>=4.0
shap>=0.44
vectorbt>=0.26
pytorch-forecasting>=1.0   # for TFT (optional, GPU recommended)
```

---

## Part 4: Expected Outcomes & Metrics

### Baseline (current system)
The current ensemble has no backtesting so we cannot quote real numbers. Based on the architecture (naive labeling + no walk-forward), expect:
- Significant look-ahead bias in training metrics
- Real OOS performance likely close to random for the current labeling approach

### Target (after all 3 sub-plans)
Realistic targets for a well-built IDX swing trading system with proper validation:

| Metric | Realistic target | World-class |
|---|---|---|
| Annualized Sharpe | 0.8–1.5 | > 2.0 |
| Win rate | 52–58% | > 60% |
| Max drawdown | < 15% | < 8% |
| Avg hold period | 3–7 days | varies |
| Annual alpha vs IHSG | +5–12% | > 15% |

> These are after-cost, out-of-sample targets. Anything above 1.5 Sharpe in live trading should be treated with skepticism until proven over 1+ year.

---

## Part 5: Build Order

Build in this order — each sub-plan depends on the previous:

```
Sub-Plan A (data)  →  Sub-Plan B (features)  →  Sub-Plan C (models)
     ↓                      ↓                         ↓
  3–4 days              2–3 days                  5–7 days
```

**Do NOT start Sub-Plan B until Sub-Plan A has at least 30 days of gold/forex/crypto history.** The cross-asset correlation features need a lookback window to be meaningful. A good sequence:
1. Deploy Sub-Plan A data pipeline now (timer fires daily)
2. After 30 days, run Sub-Plan B feature overhaul
3. After 90 days of data, run Sub-Plan C model overhaul (need sufficient training data)
4. After 180 days, evaluate live signal quality vs backtest predictions

---

## Part 6: What to Build First

The user asked "can we build the best prediction model." Honest answer:

**What separates research-grade from production-grade quant systems:**
1. ✅ Walk-forward validation (no data leakage)
2. ✅ Triple-barrier labeling (tradeable outcomes)
3. ✅ Transaction cost modeling in backtest
4. ✅ Meta-labeler to filter low-quality signals
5. ✅ Cross-asset features (the edge vs. pure price models)
6. ⚠️ Tick data / order flow (NOT available for IDX retail)
7. ⚠️ Alternative data (satellite, credit card, app downloads) — out of scope

With items 1–5 in place and 180+ days of live data, this system would be competitive with most retail and semi-professional quant systems for IDX swing trading. Items 6–7 are what separates prop-shop HFT from retail — they're not accessible here, and they're not needed for the target trading style.

**Start with Sub-Plan A.** The other two plans depend on real multi-asset data existing in the database.
