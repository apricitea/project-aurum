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
# BinanceFetcher (uses yfinance for BTC-USD 1m — Binance blocked on homelab)
# ------------------------------------------------------------------ #

def _btc_ohlcv_df(rows: int = 10) -> pd.DataFrame:
    idx = pd.date_range("2026-01-01", periods=rows, freq="min", tz="UTC")
    return pd.DataFrame(
        {
            "Open": [50000.0] * rows,
            "High": [50100.0] * rows,
            "Low": [49900.0] * rows,
            "Close": [50050.0] * rows,
            "Volume": [1.5] * rows,
        },
        index=idx,
    )


class TestBinanceFetcher:
    def test_fetch_saves_records(self, db_session):
        with patch("src.data_pipeline.multi_asset_fetcher.yf.Ticker") as mock_ticker:
            mock_ticker.return_value.history.return_value = _btc_ohlcv_df(10)
            fetcher = BinanceFetcher(db_session)
            results, job_id = fetcher.fetch(lookback_minutes=60)

        assert results[0].success
        assert results[0].records_fetched == 10

    def test_fetch_handles_empty_response(self, db_session):
        with patch("src.data_pipeline.multi_asset_fetcher.yf.Ticker") as mock_ticker:
            mock_ticker.return_value.history.return_value = pd.DataFrame()
            fetcher = BinanceFetcher(db_session)
            results, _ = fetcher.fetch(lookback_minutes=60)

        assert results[0].success is False

    def test_fetch_caps_lookback_at_7_days(self, db_session):
        """Lookback > 7 days is silently capped to 7d (yfinance 1m limit)."""
        with patch("src.data_pipeline.multi_asset_fetcher.yf.Ticker") as mock_ticker:
            mock_ticker.return_value.history.return_value = _btc_ohlcv_df(5)
            BinanceFetcher(db_session).fetch(lookback_minutes=60 * 24 * 60)  # 60 days

        # Should have been called with period="7d", not "60d"
        call_kwargs = mock_ticker.return_value.history.call_args
        assert call_kwargs.kwargs.get("period", "") == "7d"


# ------------------------------------------------------------------ #
# Retention Cleaner
# ------------------------------------------------------------------ #

class TestMultiAssetRetentionCleaner:
    def test_deletes_old_1m_rows(self, db_session):
        cleaner = MultiAssetRetentionCleaner(db_session)
        deleted = cleaner.purge_old_1m_data(retain_days=60)

        assert isinstance(deleted, int)
        db_session.commit.assert_called()
