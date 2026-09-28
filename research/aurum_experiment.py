#!/usr/bin/env python3
"""
Reproducible re-evaluation of Project Aurum's IDX signal model.

Why this exists
---------------
The project's earlier performance claim (195.6% return / 2.70 Sharpe / 509 trades
on 2025 out-of-sample data) had no linked run artifact and has been withdrawn. The
pipeline that produced the checked-in `backtest_results.json` has four evaluation
defects that this script fixes:

  1. The final model was trained on `X_all[:-val_size]`, where `X_all` spans the
     full 2020-2025 series. That includes most of the 2025 "test" period, so the
     reported backtest was not out-of-sample.
  2. Inside walk-forward folds, early stopping used `eval_set=[(X_test, y_test)]`
     — the model's number of boosting rounds was selected on the fold's test
     window, so the "OOS accuracy" was selected-on-test.
  3. The RobustScaler was fitted on the entire series (`fit_transform(X_all)`)
     before any split, leaking test-period feature distribution into training.
  4. The embargo was 5 *calendar* days while the triple-barrier label horizon is
     `max_holding` *trading bars* (10 by default), so training labels whose outcome
     resolves inside the test window were kept, and there was no purge at all.

It also adds what was missing entirely: sample weights for overlapping labels,
a majority-class baseline for the reported accuracy, buy-and-hold and momentum
baselines under identical transaction costs, an equal-weight portfolio result
instead of only per-ticker aggregates, and a run manifest.

Everything is derived from public daily OHLCV data; no proprietary data is used.

Usage
-----
    uv run python research/aurum_experiment.py                    # full run
    uv run python research/aurum_experiment.py --tickers BBCA.JK BBRI.JK
    uv run python research/aurum_experiment.py --no-cross-asset   # ablation

Outputs land in `research/out/<run_id>/`: results.json, manifest.json,
predictions.csv, trades.csv, fold_metrics.csv, four figures, and RESULTS.md.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import lightgbm as lgb  # noqa: E402
import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import shap  # noqa: E402
from sklearn.metrics import accuracy_score, f1_score  # noqa: E402
from sklearn.preprocessing import RobustScaler  # noqa: E402

from src.domains.market_data.application.feature_engineering import IDXFeatureEngineer  # noqa: E402
from src.domains.market_data.application.triple_barrier import TripleBarrierLabeler  # noqa: E402

# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #

UNIVERSE = [
    "BBCA.JK", "BMRI.JK", "BBRI.JK", "BBNI.JK",
    "TLKM.JK", "ASII.JK", "UNVR.JK", "INDF.JK",
    "KLBF.JK", "ADRO.JK", "ANTM.JK", "PTBA.JK",
    "GGRM.JK", "HMSP.JK", "SMGR.JK", "JSMR.JK",
]
BENCHMARK = "^JKSE"

# Cross-asset proxies, fetched from the same public source as the equity data.
CROSS_ASSET_SYMBOLS = {"usdidr": "USDIDR=X", "gold": "GC=F", "btc": "BTC-USD"}


@dataclass
class Config:
    universe: list[str] = field(default_factory=lambda: list(UNIVERSE))
    benchmark: str = BENCHMARK
    train_start: str = "2020-01-01"
    train_end: str = "2024-12-31"
    test_start: str = "2025-01-01"
    test_end: str = "2025-12-31"
    # Triple-barrier label configuration
    pt_multiplier: float = 2.0
    sl_multiplier: float = 1.0
    label_horizon_bars: int = 10          # vertical barrier, in trading bars
    # Walk-forward configuration, in trading bars (not calendar days)
    fold_train_bars: int = 252
    fold_test_bars: int = 63
    inner_val_frac: float = 0.20          # chronological tail of train slice
    # Model
    n_estimators: int = 400
    learning_rate: float = 0.04
    num_leaves: int = 31
    max_depth: int = 5
    min_child_samples: int = 50
    subsample: float = 0.8
    colsample_bytree: float = 0.7
    reg_alpha: float = 0.1
    reg_lambda: float = 1.0
    early_stopping_rounds: int = 40
    n_jobs: int = 2                       # keep the shared homelab host responsive
    seed: int = 42
    # Execution / costs
    buy_cost: float = 0.0015              # 0.15% IDX buy
    sell_cost: float = 0.0025             # 0.25% IDX sell
    confidence_threshold: float = 0.6
    include_cross_asset: bool = True


# --------------------------------------------------------------------------- #
# Small helpers
# --------------------------------------------------------------------------- #

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def git_revision() -> dict:
    def run(*args: str) -> str:
        try:
            return subprocess.run(
                ["git", *args], cwd=ROOT, capture_output=True, text=True, check=True
            ).stdout.strip()
        except Exception:
            return ""
    return {
        "commit": run("rev-parse", "HEAD"),
        "dirty": bool(run("status", "--porcelain")),
        "branch": run("rev-parse", "--abbrev-ref", "HEAD"),
    }


def fetch_prices(symbol: str, start: str, end: str, cache_dir: Path) -> pd.DataFrame:
    """Daily OHLCV, cached to CSV so a run is repeatable from the same bytes."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    safe = symbol.replace("^", "idx_").replace("=", "_").replace("-", "_")
    cache = cache_dir / f"{safe}__{start}__{end}.csv"
    if cache.exists():
        df = pd.read_csv(cache, index_col=0, parse_dates=True)
    else:
        import yfinance as yf
        df = yf.download(symbol, start=start, end=end, auto_adjust=True, progress=False)
        if df is None or df.empty:
            return pd.DataFrame()
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df.columns = [str(c).lower() for c in df.columns]
        keep = ["open", "high", "low", "close", "volume"]
        if not all(c in df.columns for c in keep):
            return pd.DataFrame()
        df = df[keep].dropna(how="any")
        df.to_csv(cache)
    df.index = pd.to_datetime(df.index)
    return df.sort_index()


# --------------------------------------------------------------------------- #
# Labels, purge, weights  (López de Prado, AFML ch. 3-4 and ch. 7)
# --------------------------------------------------------------------------- #

def label_span_end(positions: np.ndarray, horizon: int, n: int) -> np.ndarray:
    """Last bar whose price determines the label at each position."""
    return np.minimum(positions + horizon, n - 1)


def average_uniqueness(n: int, horizon: int) -> np.ndarray:
    """
    Weight for overlapping labels: mean of 1/concurrency over each label's span.

    Consecutive triple-barrier labels share most of their price path, so an
    unweighted fit double-counts the same observations.
    """
    concurrency = np.zeros(n, dtype=float)
    for i in range(n):
        end = min(i + horizon, n - 1)
        concurrency[i: end + 1] += 1.0
    concurrency[concurrency == 0] = 1.0
    inv = 1.0 / concurrency
    weights = np.empty(n, dtype=float)
    for i in range(n):
        end = min(i + horizon, n - 1)
        weights[i] = inv[i: end + 1].mean()
    return weights / weights.mean()


def walk_forward_folds(idx: pd.DatetimeIndex, cfg: Config) -> list[tuple[int, int, int, int]]:
    """
    Rolling folds as positional slices with a purge/embargo gap of at least
    `label_horizon_bars` trading bars between train end and test start.

    Returns a list of (train_lo, train_hi, test_lo, test_hi) with half-open ranges.
    """
    n = len(idx)
    folds = []
    gap = cfg.label_horizon_bars
    train_lo = 0
    while True:
        train_hi = min(train_lo + cfg.fold_train_bars, n)
        test_lo = train_hi + gap
        test_hi = min(test_lo + cfg.fold_test_bars, n)
        if train_hi - train_lo < 120 or test_hi - test_lo < 20:
            break
        folds.append((train_lo, train_hi, test_lo, test_hi))
        train_lo = test_hi
    return folds


def fit_fold_model(
    X: np.ndarray,
    y: np.ndarray,
    w: np.ndarray,
    train_lo: int,
    train_hi: int,
    cfg: Config,
):
    """
    Fit one model on [train_lo, train_hi) using a chronological inner validation
    tail for early stopping. The scaler is fitted on the inner-train slice only.

    Returns (model, scaler, history) — history is the best iteration / best score.
    """
    val_lo = train_hi - max(int((train_hi - train_lo) * cfg.inner_val_frac), 20)
    if val_lo <= train_lo:
        val_lo = train_lo + max((train_hi - train_lo) // 5, 1)

    scaler = RobustScaler().fit(X[train_lo:val_lo])
    X_in = scaler.transform(X[train_lo:val_lo])
    X_val = scaler.transform(X[val_lo:train_hi])

    y_in, y_val = y[train_lo:val_lo], y[val_lo:train_hi]
    w_in = w[train_lo:val_lo]

    model = lgb.LGBMClassifier(
        n_estimators=cfg.n_estimators,
        learning_rate=cfg.learning_rate,
        num_leaves=cfg.num_leaves,
        max_depth=cfg.max_depth,
        min_child_samples=cfg.min_child_samples,
        subsample=cfg.subsample,
        subsample_freq=1,
        colsample_bytree=cfg.colsample_bytree,
        reg_alpha=cfg.reg_alpha,
        reg_lambda=cfg.reg_lambda,
        class_weight="balanced",
        random_state=cfg.seed,
        n_jobs=cfg.n_jobs,
        verbose=-1,
    )

    history: dict = {}
    if len(np.unique(y_in)) > 1 and len(np.unique(y_val)) > 1:
        model.fit(
            X_in, y_in,
            sample_weight=w_in,
            eval_set=[(X_val, y_val)],
            eval_sample_weight=[w[val_lo:train_hi]],
            eval_metric="multi_logloss",
            callbacks=[
                lgb.early_stopping(cfg.early_stopping_rounds, verbose=False),
                lgb.log_evaluation(-1),
            ],
        )
        history = {
            "best_iteration": int(getattr(model, "best_iteration_", 0) or 0),
            "best_score": float(getattr(model, "best_score_", {}).get("valid_0", {}).get("multi_logloss", np.nan))
            if isinstance(getattr(model, "best_score_", None), dict) else float("nan"),
            "train_rows": int(val_lo - train_lo),
            "val_rows": int(train_hi - val_lo),
        }
    else:
        model.fit(X_in, y_in, sample_weight=w_in)
        history = {"best_iteration": cfg.n_estimators, "best_score": float("nan"),
                   "train_rows": int(val_lo - train_lo), "val_rows": int(train_hi - val_lo),
                   "note": "single-class slice; early stopping disabled"}
    return model, scaler, history


# --------------------------------------------------------------------------- #
# Backtest: long/flat, signal at close t is acted on at t+1, IDX costs
# --------------------------------------------------------------------------- #

def backtest_long_flat(
    close: pd.Series,
    target: pd.Series,
    buy_cost: float,
    sell_cost: float,
) -> dict:
    """
    `target[t]` is the desired position (0/1) decided from information available at
    the close of bar t. It is executed from bar t+1. Costs are charged on every
    position change.
    """
    close = close.astype(float)
    pos = target.shift(1).fillna(0.0).clip(0.0, 1.0)
    ret = close.pct_change().fillna(0.0)
    turnover = pos.diff().abs().fillna(pos.abs())
    cost = turnover * np.where(pos.diff().fillna(pos) > 0, buy_cost, sell_cost)
    net = pos * ret - cost
    equity = (1.0 + net).cumprod()

    trades = _trade_ledger(close, pos, buy_cost, sell_cost)
    return {
        "equity": equity,
        "net_returns": net,
        "position": pos,
        "trades": trades,
        "metrics": _metrics(equity, net, trades),
    }


def _trade_ledger(close: pd.Series, pos: pd.Series, buy_cost: float, sell_cost: float) -> pd.DataFrame:
    rows = []
    entry_idx = None
    prev = 0.0
    for ts, p in pos.items():
        if prev == 0.0 and p > 0.0:
            entry_idx = ts
        elif prev > 0.0 and p == 0.0 and entry_idx is not None:
            ep, xp = float(close.loc[entry_idx]), float(close.loc[ts])
            gross = xp / ep - 1.0
            costs = buy_cost + sell_cost
            rows.append({
                "entry_date": entry_idx.date().isoformat(),
                "exit_date": ts.date().isoformat(),
                "holding_bars": int(len(close.loc[entry_idx:ts]) - 1),
                "entry_price": round(ep, 4),
                "exit_price": round(xp, 4),
                "gross_return_pct": round(gross * 100, 4),
                "cost_pct": round(costs * 100, 4),
                "net_return_pct": round((gross - costs) * 100, 4),
            })
            entry_idx = None
        prev = p
    if entry_idx is not None:                      # still open at the end — mark to market
        ep, xp = float(close.loc[entry_idx]), float(close.iloc[-1])
        gross = xp / ep - 1.0
        rows.append({
            "entry_date": entry_idx.date().isoformat(),
            "exit_date": close.index[-1].date().isoformat(),
            "holding_bars": int(len(close.loc[entry_idx:]) - 1),
            "entry_price": round(ep, 4),
            "exit_price": round(xp, 4),
            "gross_return_pct": round(gross * 100, 4),
            "cost_pct": round(buy_cost * 100, 4),
            "net_return_pct": round((gross - buy_cost) * 100, 4),
            "open_at_end": True,
        })
    return pd.DataFrame(rows)


def _metrics(equity: pd.Series, net: pd.Series, trades: pd.DataFrame) -> dict:
    if len(equity) == 0:
        return {}
    total_return = float(equity.iloc[-1] - 1.0) * 100.0
    years = max(len(net) / 252.0, 1e-9)
    cagr = ((equity.iloc[-1]) ** (1 / years) - 1.0) * 100.0 if equity.iloc[-1] > 0 else -100.0
    vol = float(net.std())
    sharpe = float(net.mean() / vol * np.sqrt(252)) if vol > 0 else 0.0
    dd = float((equity / equity.cummax() - 1.0).min()) * 100.0
    win_rate = float((trades["net_return_pct"] > 0).mean() * 100) if len(trades) else 0.0
    return {
        "total_return_pct": round(total_return, 2),
        "cagr_pct": round(cagr, 2),
        "sharpe": round(sharpe, 2),
        "max_drawdown_pct": round(dd, 2),
        "trades": int(len(trades)),
        "win_rate_pct": round(win_rate, 2),
    }


def buy_and_hold(close: pd.Series, buy_cost: float, sell_cost: float) -> dict:
    """Baseline: long for the whole window, costs charged on entry and exit."""
    return backtest_long_flat(close, pd.Series(1.0, index=close.index), buy_cost, sell_cost)


def momentum_baseline(close: pd.Series, window: int, buy_cost: float, sell_cost: float) -> dict:
    """Baseline: long while close > SMA(window), flat otherwise."""
    sma = close.rolling(window).mean()
    target = (close > sma).astype(float)
    return backtest_long_flat(close, target, buy_cost, sell_cost)


# --------------------------------------------------------------------------- #
# Main experiment
# --------------------------------------------------------------------------- #

def run(cfg: Config) -> Path:
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + (git_revision()["commit"][:7] or "nogit")
    outdir = ROOT / "research" / "out" / run_id
    outdir.mkdir(parents=True, exist_ok=True)
    cache_dir = ROOT / "data" / "raw" / "research_cache"

    print(f"[run] {run_id}")
    print(f"[run] output -> {outdir}")

    data_hashes, skipped = {}, []

    # ---- 1. data --------------------------------------------------------- #
    prices, benchmark = {}, None
    for tkr in cfg.universe:
        df = fetch_prices(tkr, cfg.train_start, cfg.test_end, cache_dir)
        if df.empty or len(df) < cfg.fold_train_bars + 60:
            skipped.append(tkr)
            continue
        prices[tkr] = df
        cache_files = list(cache_dir.glob(f"{tkr.replace('^','idx_').replace('=','_').replace('-','_')}__*"))
        if cache_files:
            data_hashes[tkr] = {
                "file": cache_files[0].name,
                "sha256": sha256_file(cache_files[0]),
                "rows": int(len(df)),
                "first": df.index[0].date().isoformat(),
                "last": df.index[-1].date().isoformat(),
            }

    bdf = fetch_prices(cfg.benchmark, cfg.test_start, cfg.test_end, cache_dir)
    if not bdf.empty:
        benchmark = bdf["close"]

    print(f"[data] {len(prices)} tickers usable, {len(skipped)} skipped {skipped}")

    # ---- 2. cross-asset -------------------------------------------------- #
    cross = None
    if cfg.include_cross_asset:
        frames = {}
        for name, sym in CROSS_ASSET_SYMBOLS.items():
            cdf = fetch_prices(sym, cfg.train_start, cfg.test_end, cache_dir)
            if not cdf.empty:
                frames[name] = cdf["close"]
                cf = list(cache_dir.glob(f"{sym.replace('^','idx_').replace('=','_').replace('-','_')}__*"))
                if cf:
                    data_hashes[sym] = {"file": cf[0].name, "sha256": sha256_file(cf[0]),
                                        "rows": int(len(cdf)),
                                        "first": cdf.index[0].date().isoformat(),
                                        "last": cdf.index[-1].date().isoformat()}
        if frames:
            raw_cross = pd.DataFrame(frames).sort_index()
            cross = pd.DataFrame(index=raw_cross.index)
            if "gold" in raw_cross:
                cross["gold_1d_return"] = raw_cross["gold"].pct_change()
                cross["gold_5d_return"] = raw_cross["gold"].pct_change(5)
            if "usdidr" in raw_cross:
                cross["usdidr_1d_return"] = raw_cross["usdidr"].pct_change()
                cross["usdidr_5d_return"] = raw_cross["usdidr"].pct_change(5)
                cross["usdidr_vol_20d"] = raw_cross["usdidr"].pct_change().rolling(20).std()
            if "btc" in raw_cross:
                cross["btc_1d_return"] = raw_cross["btc"].pct_change()
                cross["btc_vol_30d"] = raw_cross["btc"].pct_change().rolling(30).std()
                # Regime: +1 while BTC trades above its own 30-day mean, else -1.
                cross["btc_regime"] = np.where(
                    raw_cross["btc"] > raw_cross["btc"].rolling(30).mean(), 1.0, -1.0
                )
            cross = cross.ffill()
            print(f"[data] cross-asset features: {list(cross.columns)} from {list(frames)}")

    per_ticker: dict[str, dict] = {}
    fold_rows: list[dict] = []
    predictions_out: list[pd.DataFrame] = []
    trades_out: list[pd.DataFrame] = []
    portfolio_parts: dict[str, pd.Series] = {"strategy": [], "buy_hold": [], "momentum": []}
    benchmark_series = None

    for tkr, raw in prices.items():
        eng = IDXFeatureEngineer()
        feats = eng.generate_technical_features(raw, cross_asset_df=cross)
        labeler = TripleBarrierLabeler(
            pt_sl=(cfg.pt_multiplier, cfg.sl_multiplier),
            max_holding=cfg.label_horizon_bars,
        )
        labels = labeler.label(feats["close"], feats["atr"])

        # feature columns, minus anything entirely missing
        feature_cols = [
            c for c in feats.columns
            if any(k in c for k in [
                "return_", "ma_", "price_to_ma", "momentum_", "rsi_", "macd", "stoch_",
                "williams_r", "bb_", "volume_", "vwap", "obv", "atr", "adx", "gap",
                "vol_5d", "vol_10d", "vol_20d", "vol_60d", "market_regime", "trend_strength",
                "usdidr_", "gold_", "btc_", "stock_btc_corr", "stock_gold_corr",
            ])
        ]
        usable = [c for c in feature_cols if feats[c].notna().any() and feats[c].std(skipna=True) > 0]
        dropped_dead = [c for c in feature_cols if c not in usable]

        X_df = feats[usable]
        y = labels.values.astype(float)

        # rows usable for modelling: features present and a label that exists
        warmup = X_df.notna().all(axis=1)
        valid = warmup & ~np.isnan(y)
        X_full = X_df[valid].to_numpy(dtype=float)
        y_full = y[valid]
        idx_full = feats.index[valid]

        n = len(idx_full)
        if n < cfg.fold_train_bars + cfg.label_horizon_bars + 60:
            skipped.append(tkr)
            continue

        weights = average_uniqueness(n, cfg.label_horizon_bars)

        train_sel = idx_full <= pd.Timestamp(cfg.train_end)
        test_sel = (idx_full >= pd.Timestamp(cfg.test_start)) & (idx_full <= pd.Timestamp(cfg.test_end))
        n_train = int(train_sel.sum())
        n_test = int(test_sel.sum())
        if n_train < cfg.fold_train_bars or n_test < 20:
            skipped.append(tkr)
            continue

        # Purge: the final model trains on [0, n_train - label_horizon_bars) so that no
        # training label resolves at or after the first test bar. Purged rows are the
        # tail of the training window whose outcome window would overlap the test set.
        purged = int(cfg.label_horizon_bars)

        # ---- walk-forward OOS accuracy inside the training period --------- #
        idx_train = idx_full[:n_train]
        fold_acc, fold_base_acc, fold_f1 = [], [], []
        oos_X, oos_pred, oos_true = [], [], []
        for (tlo, thi, teo, teh) in walk_forward_folds(idx_train, cfg):
            if teh > n_train - cfg.label_horizon_bars:
                continue                      # keep fold test labels resolvable inside train
            model, scaler, hist = fit_fold_model(X_full, y_full, weights, tlo, thi, cfg)
            X_fold_test = scaler.transform(X_full[teo:teh])
            pred = model.predict(X_fold_test)
            truth = y_full[teo:teh]
            fold_acc.append(float(accuracy_score(truth, pred)))
            fold_f1.append(float(f1_score(truth, pred, average="macro", zero_division=0)))
            vals, counts = np.unique(truth, return_counts=True)
            fold_base_acc.append(float(counts.max() / counts.sum()))
            fold_rows.append({
                "ticker": tkr, "train_bars": thi - tlo, "test_bars": teh - teo,
                "train_start": idx_train[tlo].date().isoformat(),
                "train_end": idx_train[thi - 1].date().isoformat(),
                "test_start": idx_train[teo].date().isoformat(),
                "test_end": idx_train[teh - 1].date().isoformat(),
                "oos_accuracy": round(fold_acc[-1], 4),
                "majority_baseline_accuracy": round(fold_base_acc[-1], 4),
                "oos_macro_f1": round(fold_f1[-1], 4),
                "best_iteration": hist.get("best_iteration"),
            })
            oos_X.append(X_fold_test)
            oos_pred.append(pred)
            oos_true.append(truth)

        # ---- final model: trained strictly on the training period --------- #
        final_model, final_scaler, final_hist = fit_fold_model(
            X_full, y_full, weights, 0, n_train - cfg.label_horizon_bars, cfg
        )

        test_positions = np.where(test_sel)[0]
        X_test = final_scaler.transform(X_full[test_positions])
        pred_test = final_model.predict(X_test)
        proba_test = final_model.predict_proba(X_test)

        # ---- meta-labeler on fold OOS predictions only -------------------- #
        meta_bet = None
        if oos_X:
            Xo = np.vstack(oos_X)
            po = np.concatenate(oos_pred)
            to = np.concatenate(oos_true)
            meta_y = (po == to).astype(int)
            if len(np.unique(meta_y)) > 1:
                meta = lgb.LGBMClassifier(
                    n_estimators=200, learning_rate=0.05, num_leaves=15, max_depth=4,
                    min_child_samples=30, subsample=0.8, subsample_freq=1,
                    random_state=cfg.seed, n_jobs=cfg.n_jobs, verbose=-1,
                )
                meta_scaler = RobustScaler().fit(Xo)
                meta.fit(meta_scaler.transform(Xo), meta_y)
                meta_bet = meta.predict_proba(meta_scaler.transform(X_test))[:, 1]

        # ---- signals and backtest on the untouched test period ------------ #
        test_index = idx_full[test_positions]
        close_test = feats["close"].reindex(test_index).astype(float)

        signals = pd.Series(0.0, index=test_index)
        signals[pred_test == 1.0] = 1.0
        if meta_bet is not None:
            signals = signals.where(pd.Series(meta_bet, index=test_index) >= cfg.confidence_threshold, 0.0)

        strat = backtest_long_flat(close_test, signals, cfg.buy_cost, cfg.sell_cost)
        bh = buy_and_hold(close_test, cfg.buy_cost, cfg.sell_cost)
        mom = momentum_baseline(close_test, 20, cfg.buy_cost, cfg.sell_cost)

        # ---- SHAP on the final model ------------------------------------- #
        shap_top = []
        try:
            explainer = shap.TreeExplainer(final_model)
            sample = X_test[: min(len(X_test), 400)]
            sv = explainer(sample)
            sv_arr = np.array(sv.values)
            if sv_arr.ndim == 3:
                sv_arr = sv_arr.mean(axis=-1)
            mean_abs = np.abs(sv_arr).mean(axis=0)
            top = np.argsort(mean_abs)[::-1][:15]
            shap_top = [{"feature": usable[i], "mean_abs_shap": round(float(mean_abs[i]), 6)} for i in top]
        except Exception as exc:            # pragma: no cover - diagnostic only
            print(f"[shap] {tkr}: {exc}")

        per_ticker[tkr] = {
            "n_features": len(usable),
            "n_features_dropped_unusable": len(dropped_dead),
            "dropped_unusable": dropped_dead,
            "n_samples": int(n),
            "n_train": int(n_train),
            "n_test": int(n_test),
            "purged_train_rows": purged,
            "final_model": final_hist,
            "folds": len(fold_acc),
            "fold_oos_accuracy_mean": round(float(np.mean(fold_acc)), 4) if fold_acc else None,
            "fold_oos_accuracy_std": round(float(np.std(fold_acc)), 4) if fold_acc else None,
            "fold_majority_baseline_mean": round(float(np.mean(fold_base_acc)), 4) if fold_base_acc else None,
            "fold_macro_f1_mean": round(float(np.mean(fold_f1)), 4) if fold_f1 else None,
            "label_distribution": {str(int(k)): int(v) for k, v in zip(*np.unique(y_full, return_counts=True))},
            "signal_days": int(signals.sum()),
            "meta_filter_applied": meta_bet is not None,
            "strategy": strat["metrics"],
            "buy_and_hold": bh["metrics"],
            "momentum_sma20": mom["metrics"],
            "shap_top15": shap_top,
        }

        predictions_out.append(pd.DataFrame({
            "ticker": tkr, "date": test_index.date,
            "pred": pred_test.astype(int),
            "prob_up": proba_test[:, list(final_model.classes_).index(1)] if 1 in list(final_model.classes_) else np.nan,
            "meta_bet_size": meta_bet if meta_bet is not None else np.nan,
            "position": strat["position"].to_numpy(),
            "net_return": strat["net_returns"].to_numpy(),
        }))
        if len(strat["trades"]):
            t = strat["trades"].copy()
            t.insert(0, "ticker", tkr)
            trades_out.append(t)

        portfolio_parts["strategy"].append(strat["net_returns"])
        portfolio_parts["buy_hold"].append(bh["net_returns"])
        portfolio_parts["momentum"].append(mom["net_returns"])

        line = (f"[{tkr}] feats={len(usable)} (dropped unusable: {len(dropped_dead)}) "
                f"folds={len(fold_acc)} "
                f"oof_acc={per_ticker[tkr]['fold_oos_accuracy_mean']} "
                f"(baseline {per_ticker[tkr]['fold_majority_baseline_mean']}) "
                f"pred_dist={ {int(k): int(v) for k, v in zip(*np.unique(pred_test, return_counts=True))} } "
                f"signal_days={int(signals.sum())}/{len(signals)} "
                f"meta={'filter' if (meta_bet is not None and cfg.confidence_threshold > 0) else 'none'} "
                f"strat_ret={strat['metrics']['total_return_pct']}% "
                f"bh_ret={bh['metrics']['total_return_pct']}%")
        print(line)
        if dropped_dead:
            print(f"      dropped (all-NaN or constant): {dropped_dead[:12]}")

    # ---- 3. equal-weight portfolio --------------------------------------- #
    portfolio = {}
    all_trades = pd.concat(trades_out) if trades_out else pd.DataFrame()
    for name, parts in portfolio_parts.items():
        if not parts:
            continue
        mat = pd.concat(parts, axis=1).sort_index()
        ew = mat.mean(axis=1, skipna=True)
        eq = (1.0 + ew).cumprod()
        ledger = all_trades if name == "strategy" else pd.DataFrame()
        portfolio[name] = {
            "equity": eq,
            "metrics": _metrics(eq, ew, ledger),
        }

    bench_metrics, bench_equity = {}, None
    if benchmark is not None and len(benchmark) > 2:
        b = backtest_long_flat(benchmark, pd.Series(1.0, index=benchmark.index), cfg.buy_cost, cfg.sell_cost)
        bench_metrics = b["metrics"]
        bench_equity = b["equity"]
        bench_metrics["total_return_pct"] = round(float(benchmark.iloc[-1] / benchmark.iloc[0] - 1) * 100, 2)

    # ---- 4. figures ------------------------------------------------------ #
    figs = {}
    if portfolio:
        fig, ax = plt.subplots(figsize=(11, 5.5))
        labels = {"strategy": "Strategy (equal-weight)", "buy_hold": "Buy & hold (equal-weight)",
                  "momentum": "Momentum SMA20 (equal-weight)"}
        for name, blob in portfolio.items():
            ax.plot(blob["equity"].index, blob["equity"].values, label=labels.get(name, name))
        if bench_equity is not None:
            ax.plot(bench_equity.index, bench_equity.values, label="IHSG (^JKSE)", linestyle="--")
        ax.axhline(1.0, color="grey", linewidth=0.8)
        ax.set_title("Project Aurum — 2025 out-of-sample, equal-weight portfolio vs baselines")
        ax.set_ylabel("Equity (start = 1.0)")
        ax.legend(loc="best", fontsize=9)
        ax.grid(alpha=0.3)
        fig.tight_layout()
        p = outdir / "fig_equity_curve.png"
        fig.savefig(p, dpi=140)
        plt.close(fig)
        figs["equity_curve"] = p.name

    if fold_rows:
        fdf = pd.DataFrame(fold_rows)
        fig, ax = plt.subplots(figsize=(11, 4.6))
        piv = fdf.pivot_table(index=["ticker"], values=["oos_accuracy", "majority_baseline_accuracy"], aggfunc="mean")
        piv = piv.sort_values("oos_accuracy")
        y = np.arange(len(piv))
        ax.barh(y - 0.2, piv["oos_accuracy"], height=0.4, label="Model OOS accuracy")
        ax.barh(y + 0.2, piv["majority_baseline_accuracy"], height=0.4, label="Majority-class baseline")
        ax.set_yticks(y)
        ax.set_yticklabels(piv.index, fontsize=8)
        ax.set_xlabel("Accuracy (3-class labels)")
        ax.set_title("Walk-forward accuracy inside 2020–2024, purged and embargoed")
        ax.legend(fontsize=9)
        ax.grid(alpha=0.3, axis="x")
        fig.tight_layout()
        p = outdir / "fig_fold_accuracy.png"
        fig.savefig(p, dpi=140)
        plt.close(fig)
        figs["fold_accuracy"] = p.name
        fdf.to_csv(outdir / "fold_metrics.csv", index=False)

    if per_ticker:
        names = sorted(per_ticker)
        strat_sh = [per_ticker[t]["strategy"].get("sharpe", 0.0) for t in names]
        bh_sh = [per_ticker[t]["buy_and_hold"].get("sharpe", 0.0) for t in names]
        y = np.arange(len(names))
        fig, ax = plt.subplots(figsize=(8.5, 6))
        ax.barh(y - 0.2, strat_sh, height=0.4, label="Strategy")
        ax.barh(y + 0.2, bh_sh, height=0.4, label="Buy & hold")
        ax.axvline(0, color="grey", linewidth=0.8)
        ax.set_yticks(y)
        ax.set_yticklabels(names, fontsize=8)
        ax.set_xlabel("Sharpe ratio, 2025 test window")
        ax.set_title("Per-ticker Sharpe: strategy vs buy & hold")
        ax.legend(fontsize=9)
        ax.grid(alpha=0.3, axis="x")
        fig.tight_layout()
        p = outdir / "fig_sharpe_distribution.png"
        fig.savefig(p, dpi=140)
        plt.close(fig)
        figs["sharpe_distribution"] = p.name

        agg: dict[str, float] = {}
        for t in names:
            for row in per_ticker[t]["shap_top15"]:
                agg[row["feature"]] = agg.get(row["feature"], 0.0) + row["mean_abs_shap"]
        top = sorted(agg.items(), key=lambda kv: kv[1], reverse=True)[:15]
        if top:
            fig, ax = plt.subplots(figsize=(8.5, 5.5))
            ax.barh([k for k, _ in top][::-1], [v for _, v in top][::-1])
            ax.set_xlabel("Mean |SHAP|, summed across tickers")
            ax.set_title("Final-model feature attribution (2025 test window)")
            ax.grid(alpha=0.3, axis="x")
            fig.tight_layout()
            p = outdir / "fig_shap.png"
            fig.savefig(p, dpi=140)
            plt.close(fig)
            figs["shap"] = p.name

    # ---- 5. artefacts ---------------------------------------------------- #
    if predictions_out:
        pd.concat(predictions_out).to_csv(outdir / "predictions.csv", index=False)
    if trades_out:
        pd.concat(trades_out).to_csv(outdir / "trades.csv", index=False)

    summary = {
        "n_tickers": len(per_ticker),
        "skipped": skipped,
        "portfolio": {k: v["metrics"] for k, v in portfolio.items()},
        "benchmark_ihsg": bench_metrics,
        "mean_fold_oos_accuracy": round(float(np.mean([per_ticker[t]["fold_oos_accuracy_mean"]
                                                       for t in per_ticker
                                                       if per_ticker[t]["fold_oos_accuracy_mean"] is not None])), 4)
        if per_ticker else None,
        "mean_fold_majority_baseline": round(float(np.mean([per_ticker[t]["fold_majority_baseline_mean"]
                                                            for t in per_ticker
                                                            if per_ticker[t]["fold_majority_baseline_mean"] is not None])), 4)
        if per_ticker else None,
        "mean_strategy_sharpe": round(float(np.mean([per_ticker[t]["strategy"].get("sharpe", 0.0) for t in per_ticker])), 2),
        "mean_buy_hold_sharpe": round(float(np.mean([per_ticker[t]["buy_and_hold"].get("sharpe", 0.0) for t in per_ticker])), 2),
        "mean_momentum_sharpe": round(float(np.mean([per_ticker[t]["momentum_sma20"].get("sharpe", 0.0) for t in per_ticker])), 2),
        "total_test_trades": int(sum(per_ticker[t]["strategy"].get("trades", 0) for t in per_ticker)),
    }

    results = {"summary": summary, "portfolio": {k: v["metrics"] for k, v in portfolio.items()},
               "per_ticker": per_ticker, "figures": figs}
    (outdir / "results.json").write_text(json.dumps(results, indent=2, default=str))

    import lightgbm, sklearn, yfinance
    manifest = {
        "run_id": run_id,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "git": git_revision(),
        "config": asdict(cfg),
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "lightgbm": lightgbm.__version__,
            "scikit_learn": sklearn.__version__,
            "yfinance": yfinance.__version__,
            "pandas": pd.__version__,
            "numpy": np.__version__,
        },
        "data": {
            "source": "yfinance adjusted daily OHLCV, cached to CSV",
            "cache_dir": str(cache_dir.relative_to(ROOT)),
            "files_sha256": data_hashes,
        },
        "evaluation": {
            "train_window": [cfg.train_start, cfg.train_end],
            "test_window": [cfg.test_start, cfg.test_end],
            "label_horizon_bars": cfg.label_horizon_bars,
            "purge": "training rows whose label resolves at or after the test window are dropped",
            "embargo": f"{cfg.label_horizon_bars} trading bars between train end and test start",
            "scaler": "RobustScaler fitted on the inner-train slice of each fit, never on test data",
            "early_stopping": "chronological inner validation tail of the training slice; the test window is never used for early stopping",
            "sample_weights": "average label uniqueness (López de Prado, AFML ch. 4)",
            "costs": {"buy": cfg.buy_cost, "sell": cfg.sell_cost},
            "execution": "signal from close of bar t is executed from bar t+1",
        },
        "known_limitations": [
            "Long/flat only; the production engine also models short signals.",
            "A single 2025 test window — one year is not all market regimes.",
            "Barrier hits are evaluated on close prices, so intrabar paths are not modelled.",
            "No cross-sectional (multi-asset) model: each ticker is modelled independently.",
            "Survivorship: the universe is today's large caps, not a point-in-time index membership.",
            "yfinance is a secondary vendor for IDX data; corporate-action handling is not verified.",
        ],
    }
    (outdir / "manifest.json").write_text(json.dumps(manifest, indent=2, default=str))

    write_results_md(outdir, results, manifest)
    return outdir


def write_results_md(outdir: Path, results: dict, manifest: dict) -> None:
    s = results["summary"]
    p = results["portfolio"]
    def fmt(d: dict, keys=("total_return_pct", "cagr_pct", "sharpe", "max_drawdown_pct")) -> str:
        return " | ".join(f"{k}={d.get(k)}" for k in keys if k in d)

    lines = [
        f"# Aurum re-evaluation — {manifest['run_id']}",
        "",
        f"Run against commit `{manifest['git']['commit'][:12]}` (dirty: {manifest['git']['dirty']}).",
        f"Train window {manifest['evaluation']['train_window'][0]} → {manifest['evaluation']['train_window'][1]}; "
        f"test window {manifest['evaluation']['test_window'][0]} → {manifest['evaluation']['test_window'][1]}.",
        "",
        "## Headline",
        "",
        f"- Tickers evaluated: {s['n_tickers']}",
        f"- Mean walk-forward OOS accuracy (inside train period): **{s['mean_fold_oos_accuracy']}** "
        f"vs majority-class baseline **{s['mean_fold_majority_baseline']}**",
        f"- Equal-weight portfolio, 2025 test window: strategy {fmt(p.get('strategy', {}))}",
        f"- Equal-weight portfolio, 2025 test window: buy & hold {fmt(p.get('buy_hold', {}))}",
        f"- Equal-weight portfolio, 2025 test window: momentum SMA20 {fmt(p.get('momentum', {}))}",
        f"- IHSG over the same window: total_return_pct={s['benchmark_ihsg'].get('total_return_pct')}",
        f"- Total test-period trades across tickers: {s['total_test_trades']}",
        "",
        "## Reading this",
        "",
        "- Accuracy is on 3-class labels (+1 / 0 / -1), so 33% is chance; the majority-class",
        "  baseline is the number to compare against, not 0.",
        "- Per-ticker Sharpe averages are reported in the manifest but are not portfolio results.",
        "  The equal-weight portfolio line is the honest aggregate.",
        "- Every number here is produced by this script; see manifest.json for data hashes,",
        "  split dates, seeds, and configuration.",
        "",
        "## Known limitations",
        "",
    ]
    lines += [f"- {x}" for x in manifest["known_limitations"]]
    (outdir / "RESULTS.md").write_text("\n".join(lines) + "\n")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tickers", nargs="+", default=None)
    ap.add_argument("--no-cross-asset", action="store_true")
    ap.add_argument("--no-meta", action="store_true")
    ap.add_argument("--out-root", default=None)
    args = ap.parse_args()

    cfg = Config()
    if args.tickers:
        cfg.universe = args.tickers
    if args.no_cross_asset:
        cfg.include_cross_asset = False
    if args.no_meta:
        cfg.confidence_threshold = 0.0

    outdir = run(cfg)
    print(f"\n[done] artefacts in {outdir}")


if __name__ == "__main__":
    main()