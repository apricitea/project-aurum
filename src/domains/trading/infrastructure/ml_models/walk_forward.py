"""
Walk-Forward Validator with embargo for time-series model evaluation.

Methodology: López de Prado "Advances in Financial Machine Learning" Ch. 7.
  - Rolling training window (fixed size)
  - Non-overlapping test windows
  - Embargo gap between train end and test start to prevent leakage
    from autocorrelated observations
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List

import pandas as pd


@dataclass
class WalkForwardFold:
    fold_id: int
    train_start: pd.Timestamp
    train_end: pd.Timestamp
    test_start: pd.Timestamp
    test_end: pd.Timestamp


class WalkForwardValidator:
    """
    Generates rolling train/test folds with an embargo gap.

    Parameters
    ----------
    train_days : int
        Number of calendar days in each training window (default 252 ≈ 1 year).
    test_days : int
        Number of calendar days in each test window (default 63 ≈ 1 quarter).
    embargo_days : int
        Minimum calendar-day gap between train_end and test_start (default 5).
    """

    def __init__(
        self,
        train_days: int = 252,
        test_days: int = 63,
        embargo_days: int = 5,
    ) -> None:
        self.train_days = train_days
        self.test_days = test_days
        self.embargo_days = embargo_days

    def get_folds(self, index: pd.DatetimeIndex) -> List[WalkForwardFold]:
        """
        Generate walk-forward folds for the given date index.

        Returns an empty list if the index is too short for even one fold.
        """
        index = index.sort_values()
        total_days = (index[-1] - index[0]).days
        min_required = self.train_days + self.embargo_days + self.test_days
        if total_days < min_required:
            return []

        folds: List[WalkForwardFold] = []
        fold_id = 0
        train_start = index[0]

        while True:
            train_end_target = train_start + pd.Timedelta(days=self.train_days)
            # Find the last index date on or before the target
            train_mask = index <= train_end_target
            if not train_mask.any():
                break
            train_end = index[train_mask][-1]

            test_start_target = train_end + pd.Timedelta(days=self.embargo_days + 1)
            test_mask = index >= test_start_target
            if not test_mask.any():
                break
            test_start = index[test_mask][0]

            test_end_target = test_start + pd.Timedelta(days=self.test_days)
            test_slice_mask = (index >= test_start) & (index <= test_end_target)
            if not test_slice_mask.any():
                break
            test_end = index[test_slice_mask][-1]

            folds.append(
                WalkForwardFold(
                    fold_id=fold_id,
                    train_start=train_start,
                    train_end=train_end,
                    test_start=test_start,
                    test_end=test_end,
                )
            )
            fold_id += 1
            # Advance train window to start at next test_end
            next_start_mask = index > test_end
            if not next_start_mask.any():
                break
            train_start = index[next_start_mask][0]

        return folds
