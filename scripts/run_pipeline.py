#!/usr/bin/env python3
"""
End-to-end training + backtest pipeline for Project Aurum.

Downloads IDX OHLCV data via yfinance, engineers features, trains
LightGBM + MetaLabeler with walk-forward CV, runs backtest,
saves per-ticker and aggregated results.

Usage:
    uv run scripts/run_pipeline.py
    uv run scripts/run_pipeline.py --tickers BBCA.JK BMRI.JK --start 2020-01-01
    uv run scripts/run_pipeline.py --start 2020-01-01 --end 2025-12-31 --output results.json
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.domains.market_data.application.feature_engineering import IDXFeatureEngineer
from src.domains.trading.infrastructure.ml_models.lightgbm_model import LightGBMSignalModel
from src.domains.trading.infrastructure.ml_models.meta_labeler import MetaLabeler
from src.domains.trading.infrastructure.ml_models.walk_forward import WalkForwardValidator
from src.domains.analytics.application.backtesting_engine import BacktestingEngine

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

DEFAULT_TICKERS = [
    "BBCA.JK", "BMRI.JK", "BBRI.JK", "BBNI.JK",
    "TLKM.JK", "ASII.JK", "UNVR.JK", "INDF.JK",
    "KLBF.JK", "ADRO.JK", "ANTM.JK", "PTBA.JK",
    "GGRM.JK", "HMSP.JK", "SMGR.JK", "JSMR.JK",
]


def download_data(ticker: str, start: str, end: str) -> pd.DataFrame:
    import yfinance as yf
    df = yf.download(ticker, start=start, end=end, auto_adjust=True, progress=False)
    if df.empty:
        return df
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.columns = [c.lower() for c in df.columns]
    required = ["open", "high", "low", "close", "volume"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        logger.warning("%s: missing columns %s", ticker, missing)
        return pd.DataFrame()
    return df[required].dropna()


def run_ticker(
    ticker: str,
    start: str,
    end: str,
    confidence_threshold: float = 0.6,
    min_bars: int = 400,
) -> dict | None:
    logger.info("Processing %s", ticker)

    raw = download_data(ticker, start, end)
    if len(raw) < min_bars:
        logger.warning("%s: only %d bars (need >=%d) — skipping", ticker, len(raw), min_bars)
        return None

    eng = IDXFeatureEngineer()
    data = eng.generate_technical_features(raw)

    # 80/20 train/test split (time-ordered)
    split_idx = int(len(data) * 0.8)
    train_data = data.iloc[:split_idx]
    test_data = data.iloc[split_idx:]
    test_prices = raw.iloc[split_idx:]

    # Train primary LightGBM model
    model = LightGBMSignalModel()
    train_metrics = model.train(train_data, walk_forward=True)
    logger.info(
        "%s | folds=%d oos_acc=%.3f train_acc=%.3f n_features=%d",
        ticker,
        train_metrics.get("n_folds", 0),
        train_metrics.get("oos_accuracy_mean", float("nan")),
        train_metrics.get("training_accuracy", 0.0),
        train_metrics.get("n_features", 0),
    )

    # Train MetaLabeler on OOS predictions from walk-forward folds.
    # Using in-sample predictions would make meta_y all-1 (model overfit on train),
    # rendering the MetaLabeler degenerate. OOS predictions give real signal quality.
    meta = MetaLabeler()
    feat_names = model.feature_names
    wfv = WalkForwardValidator(train_days=252, test_days=63, embargo_days=5)
    folds = wfv.get_folds(train_data.index)
    oos_X_rows, oos_preds, oos_actual = [], [], []
    for fold in folds:
        fmask_tr = (train_data.index >= fold.train_start) & (train_data.index <= fold.train_end)
        fmask_te = (train_data.index >= fold.test_start) & (train_data.index <= fold.test_end)
        if fmask_tr.sum() < 30 or fmask_te.sum() < 5:
            continue
        fold_model = LightGBMSignalModel()
        try:
            fold_model.train(train_data[fmask_tr], walk_forward=False)
            fp, _ = fold_model.predict(train_data[fmask_te])
            fa = fold_model.create_targets(train_data[fmask_te])
            fX, _ = fold_model.prepare_features(train_data[fmask_te])
            oos_X_rows.append(fX)
            oos_preds.append(fp)
            oos_actual.append(fa)
        except Exception as e:
            logger.debug("Fold MetaLabeler training failed: %s", e)

    if oos_X_rows:
        oos_X = np.vstack(oos_X_rows)
        oos_X_df = pd.DataFrame(oos_X, columns=feat_names)
        oos_p = np.concatenate(oos_preds)
        oos_a = np.concatenate(oos_actual)
        # Only train if we have both classes (some wrong predictions)
        valid = ~np.isnan(oos_a)
        meta_y = (oos_p[valid] == oos_a[valid]).astype(int)
        if len(np.unique(meta_y)) >= 2:
            meta.fit(oos_X_df.iloc[valid], oos_p[valid], oos_a[valid])
        else:
            logger.info("%s: MetaLabeler skipped (single class in OOS — model too accurate or too few folds)", ticker)
    else:
        logger.info("%s: MetaLabeler skipped (no OOS folds)", ticker)

    # Generate signals on test data
    test_preds, _ = model.predict(test_data)
    signals = pd.Series(0.0, index=test_data.index)
    signals[test_preds == 1.0] = 1.0
    signals[test_preds == -1.0] = -1.0

    # Apply MetaLabeler confidence filter only if trained
    confidence: pd.Series | None = None
    if meta.is_trained:
        X_test, _ = model.prepare_features(test_data)
        X_test_df = pd.DataFrame(X_test, columns=feat_names)
        bet_sizes = meta.predict_bet_size(X_test_df)
        confidence = pd.Series(bet_sizes, index=test_data.index)

    # Backtest
    engine = BacktestingEngine()
    result = engine.run(test_prices, signals, confidence, confidence_threshold)

    logger.info(
        "%s | Sharpe=%.2f Return=%.1f%% WinRate=%.1f%% MaxDD=%.1f%% Trades=%d",
        ticker,
        result.sharpe_ratio,
        result.total_return_pct,
        result.win_rate_pct,
        result.max_drawdown_pct,
        result.total_trades,
    )

    return {
        "ticker": ticker,
        "bars_total": len(data),
        "bars_train": split_idx,
        "bars_test": len(test_data),
        "train_metrics": {
            k: (float(v) if isinstance(v, (int, float, np.floating)) else v)
            for k, v in train_metrics.items()
        },
        "backtest": {
            "total_return_pct": round(float(result.total_return_pct), 2),
            "sharpe_ratio": round(float(result.sharpe_ratio), 2),
            "win_rate_pct": round(float(result.win_rate_pct), 2),
            "max_drawdown_pct": round(float(result.max_drawdown_pct), 2),
            "total_trades": int(result.total_trades),
            "annualised_return_pct": round(float(result.annualised_return_pct), 2),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tickers", nargs="+", default=DEFAULT_TICKERS)
    parser.add_argument("--start", default="2020-01-01")
    parser.add_argument("--end", default="2025-12-31")
    parser.add_argument("--threshold", type=float, default=0.6)
    parser.add_argument("--output", default="backtest_results.json")
    args = parser.parse_args()

    results = []
    for ticker in args.tickers:
        try:
            r = run_ticker(ticker, args.start, args.end, args.threshold)
            if r:
                results.append(r)
        except Exception as exc:
            logger.error("%s failed: %s", ticker, exc, exc_info=True)

    if not results:
        logger.error("No results produced")
        sys.exit(1)

    sharpes = [r["backtest"]["sharpe_ratio"] for r in results]
    returns = [r["backtest"]["total_return_pct"] for r in results]
    win_rates = [r["backtest"]["win_rate_pct"] for r in results]
    drawdowns = [r["backtest"]["max_drawdown_pct"] for r in results]

    summary = {
        "n_tickers": len(results),
        "avg_sharpe": round(float(np.mean(sharpes)), 2),
        "median_sharpe": round(float(np.median(sharpes)), 2),
        "avg_return_pct": round(float(np.mean(returns)), 2),
        "avg_win_rate_pct": round(float(np.mean(win_rates)), 2),
        "avg_max_drawdown_pct": round(float(np.mean(drawdowns)), 2),
        "best_ticker": results[int(np.argmax(sharpes))]["ticker"],
        "worst_ticker": results[int(np.argmin(sharpes))]["ticker"],
    }

    print("\n===== AGGREGATE BACKTEST RESULTS =====")
    for k, v in summary.items():
        print(f"  {k}: {v}")

    output = {"summary": summary, "per_ticker": results}
    Path(args.output).write_text(json.dumps(output, indent=2, default=str))
    logger.info("Saved to %s", args.output)


if __name__ == "__main__":
    main()
