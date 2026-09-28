# Aurum re-evaluation — reproducible experiment

This directory holds a from-scratch, reproducible re-evaluation of the Project Aurum
signal model. It exists because the project's earlier performance claim (195.6% return /
2.70 Sharpe / 509 trades on 2025 out-of-sample data) had no linked run artifact and was
withdrawn. Rather than reconcile that number, this script rebuilds the evaluation
correctly and reports whatever it finds.

**Result: the signal model does not beat buy-and-hold, and its walk-forward accuracy is
below the majority-class baseline in every configuration tested.** Details below.

## What was wrong with the original evaluation

Reading `scripts/run_pipeline.py`, `lightgbm_model.py`, and `walk_forward.py` against
López de Prado's *Advances in Financial Machine Learning*, four defects invalidate the
original "out-of-sample" numbers:

| # | Defect | Where | Effect |
|---|---|---|---|
| 1 | The final model was trained on `X_all[:-val_size]`, where `X_all` spans 2020–2025, including most of the 2025 "test" period | `run_pipeline.py` + `LightGBMSignalModel.train` | The reported backtest was **in-sample** |
| 2 | Inside walk-forward folds, early stopping used `eval_set=[(X_test, y_test)]` — the fold's own test window | `lightgbm_model.py:143` | The number of boosting rounds was **selected on the test fold**, so the "OOS accuracy" was not out-of-sample |
| 3 | `RobustScaler.fit_transform(X_all)` was fitted on the whole series before any split | `lightgbm_model.py:123` | Test-period feature distribution leaked into training |
| 4 | The embargo was 5 **calendar** days while the triple-barrier label horizon is `max_holding` **trading bars** (10), and there was no purge at all | `walk_forward.py` + `run_pipeline.py` | Training rows whose labels resolve inside the test window were kept |

Two further issues affected interpretation rather than validity: consecutive
triple-barrier labels share most of their price path but were fit with equal weight
(double-counting the same observations), and the reported "OOS accuracy" of ~0.27–0.33
was never compared against the majority-class baseline (~0.53).

## What this experiment does instead

- **Purge + embargo.** The final model trains on rows whose label window resolves inside
  the training period; the test window begins at least `label_horizon_bars` (10) trading
  bars after the last training label resolves.
- **No test-set selection.** Early stopping uses a chronological inner-validation tail of
  each training slice. The test window is never passed to `eval_set`.
- **Fold-local scaling.** `RobustScaler` is fitted on the inner-train slice of each fit
  and applied to the validation and test slices.
- **Sample weights.** Weights are the average uniqueness of each label
  (`average_uniqueness`), so overlapping observations count once.
- **Baselines under identical costs.** Buy-and-hold and an SMA-20 momentum rule are run
  through the same long/flat backtest with the same IDX costs (0.15% buy / 0.25% sell)
  and the same next-bar execution.
- **A real aggregate.** Results are reported as an equal-weight portfolio across the 16
  tickers, not as a mean of per-ticker metrics (which the paper correctly notes does not
  establish portfolio performance).
- **A run manifest.** `manifest.json` records the commit, dirty flag, package versions,
  per-file SHA-256 of every cached price series, exact split dates, config, seeds, and
  costs.

Full details, including the known limitations of this experiment itself, are in each
run's `RESULTS.md` and `manifest.json`.

## Headline results (2025 test window, 16 IDX large caps)

| Configuration | Strategy return | Sharpe | Max DD | Trades | Win rate |
|---|---|---|---|---|---|
| Signal model + meta-labeler filter + cross-asset features | **+0.12%** | 0.05 | −3.28% | 108 | 50.9% |
| Signal model, no meta-labeler filter | **+7.62%** | 0.88 | −7.68% | 135 | 48.9% |
| Signal model, technical features only | **+4.73%** | 1.38 | −1.67% | 70 | 51.4% |
| **Buy & hold, equal weight** | **+14.17%** | 0.74 | −18.54% | — | — |
| Momentum SMA-20, equal weight | +0.66% | 0.12 | −11.53% | — | — |
| **IHSG (^JKSE) over the same window** | **+20.71%** | 1.12 | −17.76% | — | — |

Walk-forward accuracy inside the training period (2020–2024, purged and embargoed):

| Configuration | Mean OOS accuracy | Majority-class baseline |
|---|---|---|
| With cross-asset features | 0.3409 | 0.5317 |
| Technical features only | 0.3611 | 0.5317 |

Accuracy is on 3-class labels (+1 / 0 / −1), so chance is ~0.33. The model never reaches
the majority-class baseline, which is the honest reference point for a 3-class problem
with an imbalanced label distribution.

## What this establishes

1. **The 195.6% / 2.70 Sharpe claim is not reproducible under a corrected evaluation.**
   No configuration comes close, and the model's fold-level accuracy is below the
   naively-predict-the-majority baseline.
2. **The strategy does not beat buy-and-hold.** It loses on total return in every
   configuration, and loses badly to the index. Where the Sharpe looks respectable, that
   is a consequence of very low market exposure producing a small drawdown, not alpha.
3. **The paper's meta-labeler claim is contradicted.** The draft asserted that the
   meta-labeler "increases trade count but reduces Sharpe" and improves Sharpe by
   ~0.4 points. Here the filter cut return from +7.62% to +0.12% while reducing drawdown
   from −7.68% to −3.28%: it lowers risk by lowering exposure, at the cost of most of the
   return. Any claim about it needs to be restated in those terms.
4. **Cross-asset features do not help** in this setup; the technical-only configuration
   scored better on fold accuracy (0.3611 vs 0.3409) and on portfolio return. Notably,
   the originally committed run could not have used them at all: the cross-asset columns
   are `NaN` unless `cross_asset_df` is supplied with specific pre-computed column names,
   and `run_pipeline.py` never supplies it. The "80+ features including cross-asset
   signals" description did not match what ran.

## Running it

```bash
uv run python research/aurum_experiment.py                  # main configuration
uv run python research/aurum_experiment.py --no-meta        # ablation: no confidence filter
uv run python research/aurum_experiment.py --no-cross-asset # ablation: technical features only
uv run python research/aurum_experiment.py --tickers BBCA.JK BBRI.JK
```

Each run writes `research/out/<run_id>/{results.json,manifest.json,RESULTS.md,fold_metrics.csv,trades.csv,predictions.csv,fig_*.png}`.
Price data is cached to `data/raw/research_cache/` (gitignored) and hashed into the
manifest, so a rerun is reproducible from the same bytes. Model jobs use `n_jobs=2` to
stay friendly to the shared host.

## Committed runs

- `out/20260928T102521Z-f552679/` — main configuration (meta-labeler filter, cross-asset features)
- `out/20260928T102532Z-f552679/` — no meta-labeler filter
- `out/20260928T102543Z-f552679/` — technical features only

## Honest status of this experiment

This is a negative result, and negative results are only useful if their own limitations
are stated. It is one test year, one universe of today's large caps, long/flat only, a
single vendor (yfinance) for IDX prices, barrier hits evaluated on closes rather than
intrabar paths, and one labelling scheme (2:1 ATR barriers, 10-bar vertical). It does not
show that IDX equities are unpredictable — it shows that this pipeline, evaluated
without leakage, does not predict them well enough to beat holding the index.