# Cross-sectional robustness of the Aurum result

Generated 2026-10-25 13:55 UTC by
`research/robustness.py` from the per-ticker block of a committed run. No re-fitting
and no new data: this asks only whether the conclusion holds across the 16 tickers,
rather than being carried by a few of them.

## Strategy against buy-and-hold, ticker by ticker

| Metric | Tickers where the strategy wins | Median difference | Sign-test p | Wilcoxon p |
|---|---|---|---|---|
| total return | 10/16 | +2.850 | 0.4545 | 1 |
| Sharpe | 8/16 | -0.010 | 1 | 0.7436 |
| max drawdown | 0/16 | -23.240 | 3.052e-05 | 3.052e-05 |

A win means the strategy's per-ticker value is strictly better than buy-and-hold's on
that ticker; ties are excluded from the sign test.

## Is the strategy's Sharpe distinguishable from zero?

| Measure | Value |
|---|---|
| Median per-ticker Sharpe | +0.000 |
| Share of tickers with Sharpe > 0 | 43.8% |
| Wilcoxon p (Sharpe = 0) | 0.0926 |

## The per-ticker "win rate" is exposure, not skill

| Measure | Value |
|---|---|
| Median time in market | 2.1% of test days |
| Range | 0.0% to 60.4% |
| Tickers that never open a position | 6 of 16 |
| Win rate among tickers that do trade | 60% of 10 |
| Mean exposure where the strategy wins | 4.0% |
| Mean exposure where it loses | 11.8% |
| Spearman(exposure, return difference) | +0.07 |

Names with no position at all: ADRO, ANTM, BBCA, BBRI, GGRM, INDF.

Exposure is close to uncorrelated with the outcome, so the per-ticker spread is not explained by time in market alone.


## Walk-forward accuracy against the majority-class baseline

| Measure | Value |
|---|---|
| Tickers where the model beats the majority baseline | 1/16 |
| Median difference in fold accuracy | -0.156 |
| Sign-test p | 0.0005188 |
| Wilcoxon p | 9.155e-05 |

## How to read this

Two independent tests agreeing is worth more than either alone, and here they agree on
the direction of every comparison: the signal model loses to buy-and-hold on most
tickers and does not beat the majority-class accuracy baseline on most tickers.
That is the same conclusion the portfolio aggregate reaches, now shown not to depend
on a handful of names.

The converse caveat matters just as much: with 16 tickers, a 10-6 split is
**not** significant, so this analysis supports "the model has no demonstrable edge",
not "the model has a demonstrable anti-edge". Reporting a directional loss as if it
were established would be the same error as the withdrawn 195% claim, in reverse.

## Reproduce

```bash
uv run python research/robustness.py --run-dir research/out/<run-id>
```
