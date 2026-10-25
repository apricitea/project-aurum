# Cross-sectional robustness of the Aurum result

Generated 2026-10-25 14:02 UTC by
`research/robustness.py` from the per-ticker block of a committed run. No re-fitting
and no new data: this asks only whether the conclusion holds across the 16 tickers,
rather than being carried by a few of them.

## Strategy against buy-and-hold, ticker by ticker

| Metric | Tickers where the strategy wins | Median difference | Sign-test p | Wilcoxon p |
|---|---|---|---|---|
| total return | 8/16 | +1.390 | 1 | 0.8603 |
| Sharpe | 5/16 | -0.220 | 0.2101 | 0.1167 |
| max drawdown | 1/16 | -21.760 | 0.0005188 | 6.104e-05 |

A win means the strategy's per-ticker value is strictly better than buy-and-hold's on
that ticker; ties are excluded from the sign test.

## Is the strategy's Sharpe distinguishable from zero?

| Measure | Value |
|---|---|
| Median per-ticker Sharpe | -0.320 |
| Share of tickers with Sharpe > 0 | 18.8% |
| Wilcoxon p (Sharpe = 0) | 0.2393 |

## The per-ticker "win rate" is exposure, not skill

The strategy holds a position on a median **3.0%** of test days, and 4 of 16 names are never traded at all. A long/flat model that is in cash almost all the time is not comparable to buy-and-hold on raw return: in a market that rose, cash loses by construction. Both facts have to be read together.

| Measure | Value |
|---|---|
| Median time in market | 3.0% of test days |
| Range | 0.0% to 51.1% |
| Tickers that never open a position | 4 of 16 |
| Win rate among tickers that do trade | 42% of 12 |
| Mean exposure where the strategy wins | 6.9% |
| Mean exposure where it loses | 11.1% |
| Spearman(exposure, return difference) | -0.42 |

Names with no position at all: ADRO, BBNI, BBRI, INDF.

The correlation is negative: the less the strategy traded a name, the better it looked against buy-and-hold on that name. That is arithmetic, not skill -- a flat position returns exactly 0%, so every falling stock flatters a strategy that sat in cash. Per-ticker raw-return win rates therefore say nothing about timing ability, in either direction.


## Walk-forward accuracy against the majority-class baseline

| Measure | Value |
|---|---|
| Tickers where the model beats the majority baseline | 0/16 |
| Median difference in fold accuracy | -0.169 |
| Sign-test p | 3.052e-05 |
| Wilcoxon p | 3.052e-05 |

## How to read this

The accuracy comparison is unambiguous: the model is below the majority-class baseline on 16 of 16 tickers (sign-test p = 3.052e-05). Classification skill is not present in this cross-section, and that is independent of the trading overlay. The per-ticker return comparison against buy-and-hold is **not** significant (8/16 wins, sign-test p = 1). With 16 tickers a 10-6 split is indistinguishable from chance, so this analysis supports "the model has no demonstrable edge", not "the model has a demonstrable anti-edge". Reporting a directional loss as if it were established would be the same error as the withdrawn 195% claim, in reverse. The honest reading of both together is that the signal is not usable as a trading rule on this universe, and that a long/flat overlay that is in cash most of the time is consistent with a near-zero portfolio return even when the index rose.

## Reproduce

```bash
uv run python research/robustness.py --run-dir research/out/<run-id>
```
