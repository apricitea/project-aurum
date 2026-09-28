# Aurum re-evaluation — 20260928T102521Z-f552679

Run against commit `f552679d28ad` (dirty: True).
Train window 2020-01-01 → 2024-12-31; test window 2025-01-01 → 2025-12-31.

## Headline

- Tickers evaluated: 16
- Mean walk-forward OOS accuracy (inside train period): **0.3409** vs majority-class baseline **0.5317**
- Equal-weight portfolio, 2025 test window: strategy total_return_pct=0.12 | cagr_pct=0.13 | sharpe=0.05 | max_drawdown_pct=-3.28
- Equal-weight portfolio, 2025 test window: buy & hold total_return_pct=14.17 | cagr_pct=15.27 | sharpe=0.74 | max_drawdown_pct=-18.54
- Equal-weight portfolio, 2025 test window: momentum SMA20 total_return_pct=0.66 | cagr_pct=0.71 | sharpe=0.12 | max_drawdown_pct=-11.53
- IHSG over the same window: total_return_pct=20.71
- Total test-period trades across tickers: 108

## Reading this

- Accuracy is on 3-class labels (+1 / 0 / -1), so 33% is chance; the majority-class
  baseline is the number to compare against, not 0.
- Per-ticker Sharpe averages are reported in the manifest but are not portfolio results.
  The equal-weight portfolio line is the honest aggregate.
- Every number here is produced by this script; see manifest.json for data hashes,
  split dates, seeds, and configuration.

## Known limitations

- Long/flat only; the production engine also models short signals.
- A single 2025 test window — one year is not all market regimes.
- Barrier hits are evaluated on close prices, so intrabar paths are not modelled.
- No cross-sectional (multi-asset) model: each ticker is modelled independently.
- Survivorship: the universe is today's large caps, not a point-in-time index membership.
- yfinance is a secondary vendor for IDX data; corporate-action handling is not verified.
