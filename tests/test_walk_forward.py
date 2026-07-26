"""Tests for WalkForwardValidator."""
import pandas as pd
import pytest
from src.domains.trading.infrastructure.ml_models.walk_forward import WalkForwardValidator


@pytest.fixture
def three_year_index():
    return pd.date_range("2020-01-01", "2022-12-31", freq="B")


def test_returns_folds_for_sufficient_data(three_year_index):
    wfv = WalkForwardValidator(train_days=252, test_days=63, embargo_days=5)
    assert len(wfv.get_folds(three_year_index)) > 0


def test_returns_empty_for_short_data():
    short = pd.date_range("2020-01-01", periods=100, freq="B")
    wfv = WalkForwardValidator(train_days=252, test_days=63, embargo_days=5)
    assert wfv.get_folds(short) == []


def test_fold_train_end_before_test_start(three_year_index):
    wfv = WalkForwardValidator(train_days=252, test_days=63, embargo_days=5)
    for fold in wfv.get_folds(three_year_index):
        assert fold.train_end < fold.test_start


def test_embargo_gap_respected(three_year_index):
    embargo = 5
    wfv = WalkForwardValidator(train_days=252, test_days=63, embargo_days=embargo)
    for fold in wfv.get_folds(three_year_index):
        assert (fold.test_start - fold.train_end).days >= embargo


def test_folds_sequential_ids(three_year_index):
    wfv = WalkForwardValidator(train_days=252, test_days=63, embargo_days=5)
    for i, fold in enumerate(wfv.get_folds(three_year_index)):
        assert fold.fold_id == i


def test_test_windows_non_overlapping(three_year_index):
    wfv = WalkForwardValidator(train_days=252, test_days=63, embargo_days=5)
    folds = wfv.get_folds(three_year_index)
    for i in range(1, len(folds)):
        assert folds[i].test_start > folds[i - 1].test_end
