#!/usr/bin/env python3
"""Is the Aurum conclusion an artefact of the tickers we happened to pick?

The 2025 out-of-sample result is a portfolio aggregate over 16 IDX large caps. An
aggregate can hide a lot: a single strong name, or a couple of disasters, can drive
the mean while the typical ticker behaves differently. This script asks whether the
strategy's loss to buy-and-hold is consistent across the cross-section, using only
the per-ticker numbers already committed in a run's ``results.json``.

Two tests are reported for each comparison:

* a sign test (exact binomial) on how many tickers favour each side -- robust to
  outliers and to the non-normality of return series;
* a Wilcoxon signed-rank test on the paired differences -- uses magnitudes but still
  makes no normality assumption.

Neither test rescues a weak comparison. With 16 tickers the smallest attainable
two-sided sign-test p-value is 2 * 0.5**16 = 3.05e-5, so a clean sweep is
significant; anything around 10-6 is not, and the report says so.

Usage
-----
    uv run python research/robustness.py                       # latest run
    uv run python research/robustness.py --run-dir research/out/<id>
"""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "matplotlib-cache"))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from scipy import stats  # noqa: E402

RESEARCH_DIR = Path(__file__).resolve().parent
METRICS = ("total_return_pct", "sharpe", "max_drawdown_pct")


def latest_run(root: Path) -> Path:
    runs = sorted(p for p in root.iterdir() if (p / "results.json").exists())
    if not runs:
        raise SystemExit(f"no completed runs under {root}")
    return runs[-1]


def sign_test(wins: int, n: int) -> float:
    """Two-sided exact binomial p-value for wins out of n against p=0.5."""
    if n == 0:
        return 1.0
    return float(min(1.0, 2.0 * stats.binom.cdf(min(wins, n - wins), n, 0.5)))


def paired_tests(a: np.ndarray, b: np.ndarray, higher_is_better: bool = True) -> dict:
    """Compare paired per-ticker outcomes of method A against method B."""
    diff = a - b
    if not higher_is_better:
        diff = -diff
    wins = int(np.sum(diff > 0))
    losses = int(np.sum(diff < 0))
    ties = int(np.sum(diff == 0))
    n = wins + losses
    out = {
        "n": int(len(diff)),
        "wins": wins,
        "losses": losses,
        "ties": ties,
        "median_difference": float(np.median(diff)) if len(diff) else float("nan"),
        "mean_difference": float(np.mean(diff)) if len(diff) else float("nan"),
        "sign_test_p": sign_test(wins, n),
    }
    if n >= 6 and np.any(diff != 0):
        try:
            stat, p = stats.wilcoxon(diff, zero_method="wilcox")
            out["wilcoxon_statistic"] = float(stat)
            out["wilcoxon_p"] = float(p)
        except ValueError as exc:  # pragma: no cover - defensive
            out["wilcoxon_error"] = str(exc)
    return out


def exposure_table(predictions_path: Path) -> dict[str, dict[str, float]]:
    """Share of test days each ticker actually holds a position.

    A long/flat strategy that spends most of its life in cash is not comparable to
    buy-and-hold on raw return: in a rising market, cash loses by construction. The
    exposure numbers make that difference visible instead of letting a "win rate"
    over tickers imply timing skill that the position series does not contain.
    """
    if not predictions_path.exists():
        return {}
    import csv

    counts: dict[str, list[int]] = {}
    with predictions_path.open() as handle:
        for row in csv.DictReader(handle):
            ticker = row["ticker"]
            position = float(row.get("position") or 0.0)
            counts.setdefault(ticker, []).append(1 if position > 0 else 0)
    return {
        ticker: {
            "days": len(values),
            "days_in_market": int(sum(values)),
            "exposure": float(sum(values) / len(values)) if values else 0.0,
        }
        for ticker, values in counts.items()
    }


def build_report(results: dict, exposure: dict[str, dict[str, float]] | None = None) -> tuple[dict, str]:
    per_ticker = results.get("per_ticker", {})
    if not per_ticker:
        raise SystemExit("results.json has no per_ticker section")
    tickers = sorted(per_ticker)
    exposure = exposure or {}

    def series(model: str, metric: str) -> np.ndarray:
        return np.array([float(per_ticker[t][model][metric]) for t in tickers])

    comparisons: dict[str, dict] = {}
    for metric in METRICS:
        # All three metrics are signed, and "better" means larger for every one of them:
        # a drawdown of -3% is better than -18%. Treating drawdown as lower-is-better
        # inverted the comparison and reported a 1/16 win rate where the true rate is 15/16.
        higher_better = True
        strategy = series("strategy", metric)
        buy_hold = series("buy_and_hold", metric)
        momentum = series("momentum_sma20", metric)
        comparisons[f"strategy_vs_buy_hold__{metric}"] = paired_tests(
            strategy, buy_hold, higher_is_better=higher_better
        )
        comparisons[f"strategy_vs_momentum__{metric}"] = paired_tests(
            strategy, momentum, higher_is_better=higher_better
        )

    # Is the strategy distinguishable from doing nothing, per ticker?
    strategy_sharpe = series("strategy", "sharpe")
    if np.any(strategy_sharpe != 0):
        stat, p = stats.wilcoxon(strategy_sharpe, zero_method="wilcox")
        zero_test = {
            "median_sharpe": float(np.median(strategy_sharpe)),
            "share_positive": float(np.mean(strategy_sharpe > 0)),
            "wilcoxon_statistic": float(stat),
            "wilcoxon_p": float(p),
        }
    else:
        zero_test = {"median_sharpe": 0.0, "share_positive": 0.0, "wilcoxon_p": 1.0}

    accuracy = np.array([float(per_ticker[t]["fold_oos_accuracy_mean"]) for t in tickers])
    majority = np.array([float(per_ticker[t]["fold_majority_baseline_mean"]) for t in tickers])
    accuracy_comparison = paired_tests(accuracy, majority)

    exposure_stats: dict[str, Any] = {}
    if exposure:
        expo = np.array([exposure.get(t, {}).get("exposure", float("nan")) for t in tickers])
        strat_ret = series("strategy", "total_return_pct")
        bh_ret = series("buy_and_hold", "total_return_pct")
        traded = expo > 0
        zero_trade = [t for t, e in zip(tickers, expo) if not e > 0]
        diff = strat_ret - bh_ret
        exposure_stats = {
            "median_exposure": float(np.nanmedian(expo)),
            "min_exposure": float(np.nanmin(expo)),
            "max_exposure": float(np.nanmax(expo)),
            "tickers_with_no_trades": len(zero_trade),
            "zero_trade_tickers": zero_trade,
            "spearman_exposure_vs_return_difference": (
                float(stats.spearmanr(expo, diff).statistic) if np.any(traded) else float("nan")
            ),
            "win_rate_among_traded_tickers": (
                float(np.mean(diff[traded] > 0)) if traded.any() else float("nan")
            ),
            "n_traded_tickers": int(traded.sum()),
            "mean_exposure_of_winners": (
                float(np.nanmean(expo[diff > 0])) if np.any(diff > 0) else float("nan")
            ),
            "mean_exposure_of_losers": (
                float(np.nanmean(expo[diff < 0])) if np.any(diff < 0) else float("nan")
            ),
        }

    summary = {
        "tickers": tickers,
        "n_tickers": len(tickers),
        "comparisons": comparisons,
        "strategy_sharpe_vs_zero": zero_test,
        "fold_accuracy_vs_majority": accuracy_comparison,
        "exposure": exposure_stats,
        "tests": {
            "sign_test": "two-sided exact binomial on per-ticker wins",
            "wilcoxon": "two-sided Wilcoxon signed-rank on paired differences",
        },
    }

    def line(name: str, c: dict) -> str:
        wol = (
            f"{c['wilcoxon_p']:.4g}" if "wilcoxon_p" in c else "n/a"
        )
        return (
            f"| {name} | {c['wins']}/{c['wins'] + c['losses']} | "
            f"{c['median_difference']:+.3f} | {c['sign_test_p']:.4g} | {wol} |"
        )

    rows = "\n".join(
        [
            line("total return", comparisons["strategy_vs_buy_hold__total_return_pct"]),
            line("Sharpe", comparisons["strategy_vs_buy_hold__sharpe"]),
            line("max drawdown", comparisons["strategy_vs_buy_hold__max_drawdown_pct"]),
        ]
    )

    exposure_block = "Exposure could not be computed (no `predictions.csv` beside this run).\n"
    if exposure_stats:
        corr = float(exposure_stats["spearman_exposure_vs_return_difference"])
        if corr < -0.2:
            reading = (
                "The correlation is negative: the less the strategy traded a name, the better it "
                "looked against buy-and-hold on that name. That is arithmetic, not skill -- a flat "
                "position returns exactly 0%, so every falling stock flatters a strategy that sat "
                "in cash. Per-ticker raw-return win rates therefore say nothing about timing "
                "ability, in either direction."
            )
        elif corr > 0.2:
            reading = (
                "The correlation is positive: the strategy did better on the names it traded more. "
                "That is consistent with the signal carrying some information on this sample, but it "
                "is also what a handful of lucky positions looks like at 16 tickers."
            )
        else:
            reading = (
                "Exposure is close to uncorrelated with the outcome, so the per-ticker spread is not "
                "explained by time in market alone."
            )
        exposure_block = (
            f"The strategy holds a position on a median **{float(exposure_stats['median_exposure']):.1%}** "
            f"of test days, and {exposure_stats['tickers_with_no_trades']} of {len(tickers)} names are "
            f"never traded at all. A long/flat model that is in cash almost all the time is not "
            f"comparable to buy-and-hold on raw return: in a market that rose, cash loses by "
            f"construction. Both facts have to be read together.\n\n"
            f"| Measure | Value |\n|---|---|\n"
            f"| Median time in market | {float(exposure_stats['median_exposure']):.1%} of test days |\n"
            f"| Range | {float(exposure_stats['min_exposure']):.1%} to {float(exposure_stats['max_exposure']):.1%} |\n"
            f"| Tickers that never open a position | {exposure_stats['tickers_with_no_trades']} of {len(tickers)} |\n"
            f"| Win rate among tickers that do trade | {float(exposure_stats['win_rate_among_traded_tickers']):.0%} "
            f"of {exposure_stats['n_traded_tickers']} |\n"
            f"| Mean exposure where the strategy wins | {float(exposure_stats['mean_exposure_of_winners']):.1%} |\n"
            f"| Mean exposure where it loses | {float(exposure_stats['mean_exposure_of_losers']):.1%} |\n"
            f"| Spearman(exposure, return difference) | {corr:+.2f} |\n\n"
            f"Names with no position at all: "
            f"{', '.join(t.replace('.JK', '') for t in exposure_stats['zero_trade_tickers']) or 'none'}.\n\n"
            f"{reading}\n\n"
        )

    ret = comparisons["strategy_vs_buy_hold__total_return_pct"]
    acc = accuracy_comparison
    acc_p = float(acc["sign_test_p"])
    ret_p = float(ret["sign_test_p"])
    if acc_p < 0.01:
        accuracy_sentence = (
            f"The accuracy comparison is unambiguous: the model is below the majority-class "
            f"baseline on {acc['losses']} of {acc['wins'] + acc['losses']} tickers "
            f"(sign-test p = {acc_p:.4g}). Classification skill is not present in this "
            f"cross-section, and that is independent of the trading overlay."
        )
    else:
        accuracy_sentence = (
            f"Walk-forward accuracy does not beat the majority-class baseline at this sample "
            f"size (sign-test p = {acc_p:.4g})."
        )
    if ret_p < 0.05:
        return_sentence = (
            f"The per-ticker return comparison against buy-and-hold is significant "
            f"({ret['wins']}/{ret['wins'] + ret['losses']} wins, p = {ret_p:.4g})."
        )
    else:
        return_sentence = (
            f"The per-ticker return comparison against buy-and-hold is **not** significant "
            f"({ret['wins']}/{ret['wins'] + ret['losses']} wins, sign-test p = {ret_p:.4g}). "
            f"With 16 tickers a 10-6 split is indistinguishable from chance, so this analysis "
            f"supports \"the model has no demonstrable edge\", not \"the model has a demonstrable "
            f"anti-edge\". Reporting a directional loss as if it were established would be the "
            f"same error as the withdrawn 195% claim, in reverse."
        )
    reading_block = (
        f"{accuracy_sentence} {return_sentence} The honest reading of both together is that "
        f"the signal is not usable as a trading rule on this universe, and that a long/flat "
        f"overlay that is in cash most of the time is consistent with a near-zero portfolio "
        f"return even when the index rose."
    )

    md = f"""# Cross-sectional robustness of the Aurum result

Generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')} by
`research/robustness.py` from the per-ticker block of a committed run. No re-fitting
and no new data: this asks only whether the conclusion holds across the 16 tickers,
rather than being carried by a few of them.

## Strategy against buy-and-hold, ticker by ticker

| Metric | Tickers where the strategy wins | Median difference | Sign-test p | Wilcoxon p |
|---|---|---|---|---|
{rows}

A win means the strategy's per-ticker value is strictly better than buy-and-hold's on
that ticker; ties are excluded from the sign test.

## Is the strategy's Sharpe distinguishable from zero?

| Measure | Value |
|---|---|
| Median per-ticker Sharpe | {zero_test['median_sharpe']:+.3f} |
| Share of tickers with Sharpe > 0 | {zero_test['share_positive']:.1%} |
| Wilcoxon p (Sharpe = 0) | {zero_test.get('wilcoxon_p', float('nan')):.4g} |

## The per-ticker "win rate" is exposure, not skill

{exposure_block}
## Walk-forward accuracy against the majority-class baseline

| Measure | Value |
|---|---|
| Tickers where the model beats the majority baseline | {accuracy_comparison['wins']}/{accuracy_comparison['wins'] + accuracy_comparison['losses']} |
| Median difference in fold accuracy | {accuracy_comparison['median_difference']:+.3f} |
| Sign-test p | {accuracy_comparison['sign_test_p']:.4g} |
| Wilcoxon p | {accuracy_comparison.get('wilcoxon_p', float('nan')):.4g} |

## How to read this

{reading_block}

## Reproduce

```bash
uv run python research/robustness.py --run-dir research/out/<run-id>
```
"""
    return summary, md


def figure(results: dict, path: Path) -> Path:
    per_ticker = results.get("per_ticker", {})
    tickers = sorted(per_ticker)
    strategy = np.array([per_ticker[t]["strategy"]["total_return_pct"] for t in tickers])
    buy_hold = np.array([per_ticker[t]["buy_and_hold"]["total_return_pct"] for t in tickers])
    fig, ax = plt.subplots(figsize=(5.6, 5.0), dpi=160)
    lim = max(np.abs(np.concatenate([strategy, buy_hold])).max() * 1.15, 5)
    ax.plot([-lim, lim], [-lim, lim], linestyle="--", color="#8a8579", linewidth=1, label="equal")
    ax.axhline(0, color="#dcd8cf", linewidth=0.8)
    ax.axvline(0, color="#dcd8cf", linewidth=0.8)
    ax.scatter(buy_hold, strategy, s=28, color="#a4443a", alpha=0.85, zorder=3)
    for x, y, t in zip(buy_hold, strategy, tickers):
        ax.annotate(t.replace(".JK", ""), (x, y), fontsize=6.5, xytext=(3, 3), textcoords="offset points")
    ax.set_xlim(-lim, lim)
    ax.set_ylim(-lim, lim)
    ax.set_xlabel("buy-and-hold return, 2025 out-of-sample (%)")
    ax.set_ylabel("signal-model return (%)")
    ax.set_title("Per-ticker 2025 result: points below the diagonal lost to buy-and-hold", fontsize=9.5, loc="left")
    ax.legend(frameon=False, fontsize=8, loc="upper left")
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return path


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run-dir", type=Path, default=None)
    args = ap.parse_args()

    run_dir = args.run_dir or latest_run(RESEARCH_DIR / "out")
    results = json.loads((run_dir / "results.json").read_text())
    exposure = exposure_table(run_dir / "predictions.csv")
    summary, md = build_report(results, exposure)

    (run_dir / "robustness.json").write_text(json.dumps(summary, indent=2))
    (run_dir / "ROBUSTNESS.md").write_text(md)
    figure(results, run_dir / "fig_per_ticker_vs_buyhold.png")
    print(f"wrote {run_dir}/robustness.json, ROBUSTNESS.md, fig_per_ticker_vs_buyhold.png")
    print(
        "strategy vs buy-and-hold total return: "
        f"{summary['comparisons']['strategy_vs_buy_hold__total_return_pct']['wins']} wins, "
        f"{summary['comparisons']['strategy_vs_buy_hold__total_return_pct']['losses']} losses, "
        f"sign p={summary['comparisons']['strategy_vs_buy_hold__total_return_pct']['sign_test_p']:.4g}"
    )


if __name__ == "__main__":
    main()
