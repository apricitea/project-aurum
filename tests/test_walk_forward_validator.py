"""Tests for WalkForwardValidator."""
from __future__ import annotations

import pandas as pd
import pytest

from src.domains.trading.infrastructure.ml_models.walk_forward import (
    WalkForwardValidator,
    WalkForwardFold,
)


@pytest.fixture
def daily_index():
    """3-year business-day index — enough for several folds."""
    return pd.date_range("2022-01-03", periods=756, freq="B")


class TestWalkForwardFolds:
    def test_returns_at_least_one_fold(self, daily_index):
        wfv = WalkForwardValidator(train_days=252, test_days=63, embargo_days=5)
        folds = wfv.get_folds(daily_index)
        assert len(folds) >= 1

    def test_fold_is_dataclass(self, daily_index):
        wfv = WalkForwardValidator(train_days=252, test_days=63, embargo_days=5)
        folds = wfv.get_folds(daily_index)
        fold = folds[0]
        assert hasattr(fold, "train_start")
        assert hasattr(fold, "train_end")
        assert hasattr(fold, "test_start")
        assert hasattr(fold, "test_end")
        assert hasattr(fold, "fold_id")

    def test_train_comes_before_test(self, daily_index):
        wfv = WalkForwardValidator(train_days=252, test_days=63, embargo_days=5)
        for fold in wfv.get_folds(daily_index):
            assert fold.train_end < fold.test_start

    def test_embargo_gap_respected(self, daily_index):
        embargo = 5
        wfv = WalkForwardValidator(train_days=252, test_days=63, embargo_days=embargo)
        for fold in wfv.get_folds(daily_index):
            gap_days = (fold.test_start - fold.train_end).days
            assert gap_days >= embargo

    def test_folds_are_non_overlapping_in_test(self, daily_index):
        wfv = WalkForwardValidator(train_days=252, test_days=63, embargo_days=5)
        folds = wfv.get_folds(daily_index)
        for i in range(1, len(folds)):
            assert folds[i].test_start > folds[i - 1].test_end

    def test_train_size_approximately_correct(self, daily_index):
        wfv = WalkForwardValidator(train_days=252, test_days=63, embargo_days=5)
        folds = wfv.get_folds(daily_index)
        fold = folds[0]
        train_slice = daily_index[
            (daily_index >= fold.train_start) & (daily_index <= fold.train_end)
        ]
        # train_days=252 calendar days ≈ 181 business days (252 * 5/7)
        assert 170 <= len(train_slice) <= 200
