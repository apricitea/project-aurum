"""Tests for GoldFetcher, ForexFetcher, BinanceFetcher, MultiAssetRetentionCleaner."""
from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.data_pipeline.multi_asset_fetcher import (
    BinanceFetcher,
    ForexFetcher,
    GoldFetcher,
    MultiAssetRetentionCleaner,
)


# ------------------------------------------------------------------ #
# Fixtures
# ------------------------------------------------------------------ #

@pytest.fixture
def db_session():
    session = MagicMock()
    session.query.return_value.filter.return_value.delete.return_value = 5
    return session


def _make_ohlcv_df(rows: int = 3) -> pd.DataFrame:
    idx = pd.date_range("2026-01-01", periods=rows, freq="D", tz="UTC")
    return pd.DataFrame(
        {
            "Open": [1800.0] * rows,
            "High": [1820.0] * rows,
            "Low": [1790.0] * rows,
            "Close": [1810.0] * rows,
            "Volume": [100.0] * rows,
        },
        index=idx,
    )


# ------------------------------------------------------------------ #
# GoldFetcher
# ------------------------------------------------------------------ #

class TestGoldFetcher:
    def test_fetch_saves_records(self, db_session):
        with patch("src.data_pipeline.multi_asset_fetcher.yf.Ticker") as mock_ticker:
            mock_ticker.return_value.history.return_value = _make_ohlcv_df(3)
            fetcher = GoldFetcher(db_session)
            results, job_id = fetcher.fetch(backfill_days=7)

        assert len(results) == 1
        assert results[0].success
        assert results[0].records_fetched == 3
        assert job_id

    def test_fetch_handles_empty_response(self, db_session):
        with patch("src.data_pipeline.multi_asset_fetcher.yf.Ticker") as mock_ticker:
            mock_ticker.return_value.history.return_value = pd.DataFrame()
            fetcher = GoldFetcher(db_session)
            results, _ = fetcher.fetch(backfill_days=7)

        assert results[0].success is False

    def test_fetch_handles_exception(self, db_session):
        with patch("src.data_pipeline.multi_asset_fetcher.yf.Ticker") as mock_ticker:
            mock_ticker.return_value.history.side_effect = RuntimeError("network error")
            fetcher = GoldFetcher(db_session)
            results, _ = fetcher.fetch(backfill_days=7)

        assert results[0].success is False
        assert "network error" in results[0].error_message


# ------------------------------------------------------------------ #
# ForexFetcher
# ------------------------------------------------------------------ #

class TestForexFetcher:
    def test_fetch_saves_records(self, db_session):
        with patch("src.data_pipeline.multi_asset_fetcher.yf.Ticker") as mock_ticker:
            mock_ticker.return_value.history.return_value = _make_ohlcv_df(5)
            fetcher = ForexFetcher(db_session, symbol="USDIDR=X")
            results, job_id = fetcher.fetch(backfill_days=7)

        assert results[0].success
        assert results[0].records_fetched == 5

    def test_fetch_uses_correct_symbol(self, db_session):
        with patch("src.data_pipeline.multi_asset_fetcher.yf.Ticker") as mock_ticker:
            mock_ticker.return_value.history.return_value = _make_ohlcv_df(1)
            ForexFetcher(db_session, symbol="USDIDR=X").fetch(backfill_days=3)

        mock_ticker.assert_called_once_with("USDIDR=X")


# ------------------------------------------------------------------ #
# BinanceFetcher
# ------------------------------------------------------------------ #

def _binance_klines(n: int = 5) -> list:
    """Minimal Binance kline format: [open_time, o, h, l, c, vol, close_time, quote_vol, ...]"""
    base = int(datetime(2026, 1, 1).timestamp() * 1000)
    return [
        [base + i * 60000, "50000", "50100", "49900", "50050", "1.5",
         base + i * 60000 + 59999, "75075.0", 100, "0.8", "40000", "0"]
        for i in range(n)
    ]


class TestBinanceFetcher:
    def test_fetch_saves_records(self, db_session):
        with patch("src.data_pipeline.multi_asset_fetcher.requests.get") as mock_get:
            mock_get.return_value.ok = True
            mock_get.return_value.json.return_value = _binance_klines(10)
            fetcher = BinanceFetcher(db_session)
            results, job_id = fetcher.fetch(lookback_minutes=60)

        assert results[0].success
        assert results[0].records_fetched == 10

    def test_fetch_handles_api_error(self, db_session):
        with patch("src.data_pipeline.multi_asset_fetcher.requests.get") as mock_get:
            mock_get.return_value.ok = False
            mock_get.return_value.status_code = 429
            fetcher = BinanceFetcher(db_session)
            results, _ = fetcher.fetch(lookback_minutes=60)

        assert results[0].success is False

    def test_fetch_paginates_when_needed(self, db_session):
        """lookback > 1000 bars triggers multiple API calls."""
        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            mock = MagicMock()
            mock.ok = True
            # First call returns full page (triggers pagination), second returns partial
            mock.json.return_value = _binance_klines(1000) if call_count == 1 else _binance_klines(200)
            return mock

        with patch("src.data_pipeline.multi_asset_fetcher.requests.get", side_effect=side_effect):
            fetcher = BinanceFetcher(db_session)
            results, _ = fetcher.fetch(lookback_minutes=1500)

        assert call_count == 2
        assert results[0].records_fetched == 1200


# ------------------------------------------------------------------ #
# Retention Cleaner
# ------------------------------------------------------------------ #

class TestMultiAssetRetentionCleaner:
    def test_deletes_old_1m_rows(self, db_session):
        cleaner = MultiAssetRetentionCleaner(db_session)
        deleted = cleaner.purge_old_1m_data(retain_days=60)

        assert isinstance(deleted, int)
        db_session.commit.assert_called()
