"""Tests for CrossAssetLoader."""
from __future__ import annotations

from datetime import date, datetime
from unittest.mock import MagicMock

import pandas as pd
import pytest

from src.domains.market_data.application.cross_asset_loader import CrossAssetLoader


@pytest.fixture
def db_session():
    return MagicMock()


def _mock_gold_rows(n=5):
    return [
        MagicMock(timestamp=datetime(2026, 1, i + 1), close_price=1800.0 + i * 2)
        for i in range(n)
    ]


def _mock_forex_rows(n=5):
    return [
        MagicMock(timestamp=datetime(2026, 1, i + 1), rate=16000.0 + i * 50)
        for i in range(n)
    ]


def _mock_crypto_rows(n=10):
    """1m BTC rows spread across 2 days."""
    rows = []
    for i in range(n):
        day = 1 + (i // 5)
        rows.append(MagicMock(
            timestamp=datetime(2026, 1, day, i % 5, 0),
            close_price=50000.0 + i * 10,
        ))
    return rows


class TestCrossAssetLoader:
    def test_load_returns_dataframe(self, db_session):
        db_session.query.return_value.filter.return_value.order_by.return_value.all.side_effect = [
            _mock_gold_rows(5),
            _mock_forex_rows(5),
            _mock_crypto_rows(10),
        ]
        loader = CrossAssetLoader(db_session)
        df = loader.load(
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 5),
        )
        assert isinstance(df, pd.DataFrame)
        assert not df.empty

    def test_load_has_expected_columns(self, db_session):
        db_session.query.return_value.filter.return_value.order_by.return_value.all.side_effect = [
            _mock_gold_rows(5),
            _mock_forex_rows(5),
            _mock_crypto_rows(10),
        ]
        loader = CrossAssetLoader(db_session)
        df = loader.load(start_date=date(2026, 1, 1), end_date=date(2026, 1, 5))

        expected = [
            "gold_close", "gold_1d_return", "gold_5d_return",
            "usdidr_rate", "usdidr_1d_return", "usdidr_5d_return", "usdidr_vol_20d",
            "btc_close", "btc_1d_return", "btc_vol_30d", "btc_regime",
        ]
        for col in expected:
            assert col in df.columns, f"Missing column: {col}"

    def test_load_empty_db_returns_empty_dataframe(self, db_session):
        db_session.query.return_value.filter.return_value.order_by.return_value.all.side_effect = [
            [], [], [],
        ]
        loader = CrossAssetLoader(db_session)
        df = loader.load(start_date=date(2026, 1, 1), end_date=date(2026, 1, 5))
        assert isinstance(df, pd.DataFrame)
        assert df.empty

    def test_btc_aggregated_to_daily(self, db_session):
        """Multiple 1m rows on same day → single daily row (last close)."""
        db_session.query.return_value.filter.return_value.order_by.return_value.all.side_effect = [
            _mock_gold_rows(2),
            _mock_forex_rows(2),
            _mock_crypto_rows(10),  # 10 1m rows across 2 days
        ]
        loader = CrossAssetLoader(db_session)
        df = loader.load(start_date=date(2026, 1, 1), end_date=date(2026, 1, 2))
        # Should have at most 2 rows (1 per day), not 10
        assert len(df) <= 2
