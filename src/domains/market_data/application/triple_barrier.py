"""
Triple Barrier Labeler (López de Prado, Advances in Financial Machine Learning, 2018).

For each bar t:
  - Upper barrier: close[t] + pt_multiplier × atr[t]
  - Lower barrier: close[t] - sl_multiplier × atr[t]
  - Vertical barrier: t + max_holding bars

Label:
  +1  if upper barrier hit first (profit target)
  -1  if lower barrier hit first (stop loss)
   0  if time barrier hit first (hold-through)
  NaN if atr[t] is NaN or zero, or t is the final bar

Usage:
    labeler = TripleBarrierLabeler(pt_sl=(2.0, 1.0), max_holding=20)
    labels = labeler.label(price_series, atr_series)

Replaces: pd.qcut(forward_returns, q=4, labels=['Sell','Hold','Buy','Strong_Buy'])
in model_ensemble.py — produces labels that reflect actual tradeable outcomes
with realistic profit/loss boundaries.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


class TripleBarrierLabeler:
    """
    ATR-based triple-barrier labeler for daily price series.

    Parameters
    ----------
    pt_sl : (float, float)
        (profit_take_multiplier, stop_loss_multiplier).
        Barriers: close ± multiplier × ATR.
        Asymmetric default (2.0 PT, 1.0 SL) → 2:1 reward/risk ratio.
    max_holding : int
        Maximum days to hold (vertical barrier). Typical: 20 trading days.
    """

    def __init__(
        self,
        pt_sl: tuple[float, float] = (2.0, 1.0),
        max_holding: int = 20,
    ) -> None:
        self.pt_multiplier, self.sl_multiplier = pt_sl
        self.max_holding = max_holding

    def label(self, prices: pd.Series, atr: pd.Series) -> pd.Series:
        """
        Compute triple-barrier labels for each bar.

        Parameters
        ----------
        prices : pd.Series
            Daily close prices, date-indexed.
        atr : pd.Series
            Average True Range aligned to the same index as prices.

        Returns
        -------
        pd.Series of float: +1.0, -1.0, 0.0, or NaN.
        """
        prices = prices.reindex(atr.index)
        n = len(prices)
        labels = pd.Series(np.nan, index=prices.index, dtype=float)

        price_arr = prices.to_numpy(dtype=float)
        atr_arr = atr.to_numpy(dtype=float)

        for i in range(n - 1):
            entry = price_arr[i]
            atr_i = atr_arr[i]

            if np.isnan(entry) or np.isnan(atr_i) or atr_i == 0:
                continue

            pt = entry + self.pt_multiplier * atr_i
            sl = entry - self.sl_multiplier * atr_i

            end = min(i + self.max_holding, n - 1)
            window = price_arr[i + 1 : end + 1]

            if len(window) == 0:
                continue

            pt_hits = np.where(window >= pt)[0]
            sl_hits = np.where(window <= sl)[0]

            pt_first = pt_hits[0] if len(pt_hits) else None
            sl_first = sl_hits[0] if len(sl_hits) else None

            if pt_first is None and sl_first is None:
                labels.iloc[i] = 0.0   # time exit
            elif pt_first is None:
                labels.iloc[i] = -1.0
            elif sl_first is None:
                labels.iloc[i] = 1.0
            else:
                labels.iloc[i] = 1.0 if pt_first <= sl_first else -1.0

        return labels


__all__ = ["TripleBarrierLabeler"]
