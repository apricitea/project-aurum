"""
CrossAssetLoader — fetches gold, forex, and BTC prices from DB tables
(populated by Sub-Plan A) and returns a single date-indexed DataFrame
for use by IDXFeatureEngineer._add_cross_asset_features().

All derived columns degrade gracefully to NaN when history is insufficient.
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta

import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from ....api.database_extensions import GoldPrice, ForexRate, CryptoPrice

logger = logging.getLogger(__name__)


class CrossAssetLoader:
    """
    Loads gold / forex / BTC data from the database and returns
    a date-indexed DataFrame ready for feature engineering.

    Columns returned:
        gold_close, gold_1d_return, gold_5d_return
        usdidr_rate, usdidr_1d_return, usdidr_5d_return, usdidr_vol_20d
        btc_close, btc_1d_return, btc_vol_30d, btc_regime
    """

    BTC_SYMBOL = "BTC-USD"
    FOREX_SYMBOL = "USDIDR=X"

    def __init__(self, db_session: Session) -> None:
        self.session = db_session

    def load(
        self,
        start_date: date,
        end_date: date,
        extra_lookback_days: int = 90,
    ) -> pd.DataFrame:
        """
        Return a date-indexed DataFrame of cross-asset features.

        Fetches `extra_lookback_days` before `start_date` so rolling
        windows (up to 30d) are warm at `start_date`.

        Returns an empty DataFrame (no columns) if all three sources
        have no data.
        """
        fetch_from = datetime.combine(
            start_date - timedelta(days=extra_lookback_days), datetime.min.time()
        )
        fetch_to = datetime.combine(end_date, datetime.max.time())

        gold_df = self._load_gold(fetch_from, fetch_to)
        forex_df = self._load_forex(fetch_from, fetch_to)
        btc_df = self._load_btc(fetch_from, fetch_to)

        if gold_df.empty and forex_df.empty and btc_df.empty:
            return pd.DataFrame()

        merged = self._build_features(gold_df, forex_df, btc_df)

        # Trim to requested date range
        merged = merged[
            (merged.index >= pd.Timestamp(start_date))
            & (merged.index <= pd.Timestamp(end_date))
        ]
        return merged

    # ------------------------------------------------------------------ #
    # Private loaders
    # ------------------------------------------------------------------ #

    def _load_gold(self, start: datetime, end: datetime) -> pd.DataFrame:
        rows = (
            self.session.query(GoldPrice)
            .filter(GoldPrice.timestamp >= start, GoldPrice.timestamp <= end)
            .order_by(GoldPrice.timestamp)
            .all()
        )
        if not rows:
            return pd.DataFrame()
        df = pd.DataFrame(
            {"close": [r.close_price for r in rows]},
            index=pd.to_datetime([r.timestamp for r in rows]).normalize(),
        )
        return df[~df.index.duplicated(keep="last")]

    def _load_forex(self, start: datetime, end: datetime) -> pd.DataFrame:
        rows = (
            self.session.query(ForexRate)
            .filter(
                ForexRate.symbol == self.FOREX_SYMBOL,
                ForexRate.timestamp >= start,
                ForexRate.timestamp <= end,
            )
            .order_by(ForexRate.timestamp)
            .all()
        )
        if not rows:
            return pd.DataFrame()
        df = pd.DataFrame(
            {"rate": [r.rate for r in rows]},
            index=pd.to_datetime([r.timestamp for r in rows]).normalize(),
        )
        return df[~df.index.duplicated(keep="last")]

    def _load_btc(self, start: datetime, end: datetime) -> pd.DataFrame:
        """Aggregate 1m rows to daily (last close per calendar day)."""
        rows = (
            self.session.query(CryptoPrice)
            .filter(
                CryptoPrice.symbol == self.BTC_SYMBOL,
                CryptoPrice.timestamp >= start,
                CryptoPrice.timestamp <= end,
            )
            .order_by(CryptoPrice.timestamp)
            .all()
        )
        if not rows:
            return pd.DataFrame()
        df = pd.DataFrame(
            {"close": [r.close_price for r in rows]},
            index=pd.to_datetime([r.timestamp for r in rows]),
        )
        # Aggregate 1m → daily using last close
        daily = df.resample("D").last().dropna()
        return daily

    # ------------------------------------------------------------------ #
    # Feature computation
    # ------------------------------------------------------------------ #

    def _build_features(
        self,
        gold: pd.DataFrame,
        forex: pd.DataFrame,
        btc: pd.DataFrame,
    ) -> pd.DataFrame:
        out = pd.DataFrame(index=self._union_index(gold, forex, btc))

        # Gold
        if not gold.empty:
            g = gold["close"].reindex(out.index, method="ffill")
            out["gold_close"] = g
            out["gold_1d_return"] = g.pct_change(1)
            out["gold_5d_return"] = g.pct_change(5)
        else:
            for col in ["gold_close", "gold_1d_return", "gold_5d_return"]:
                out[col] = np.nan

        # Forex (USD/IDR)
        if not forex.empty:
            f = forex["rate"].reindex(out.index, method="ffill")
            out["usdidr_rate"] = f
            out["usdidr_1d_return"] = f.pct_change(1)
            out["usdidr_5d_return"] = f.pct_change(5)
            out["usdidr_vol_20d"] = f.pct_change().rolling(20).std() * np.sqrt(252)
        else:
            for col in ["usdidr_rate", "usdidr_1d_return", "usdidr_5d_return", "usdidr_vol_20d"]:
                out[col] = np.nan

        # Gold / IDR ratio (gold priced in IDR — inflation signal)
        if "gold_close" in out.columns and "usdidr_rate" in out.columns:
            out["gold_vs_usdidr_ratio"] = out["gold_close"] / out["usdidr_rate"].replace(0, np.nan)
        else:
            out["gold_vs_usdidr_ratio"] = np.nan

        # BTC
        if not btc.empty:
            b = btc["close"].reindex(out.index, method="ffill")
            out["btc_close"] = b
            out["btc_1d_return"] = b.pct_change(1)
            out["btc_vol_30d"] = b.pct_change().rolling(30).std() * np.sqrt(252)
            ma20 = b.rolling(20).mean()
            regime = np.where(b > ma20, 1.0, np.where(b < ma20, -1.0, 0.0))
            out["btc_regime"] = pd.Series(regime, index=out.index).where(ma20.notna(), np.nan)
        else:
            for col in ["btc_close", "btc_1d_return", "btc_vol_30d", "btc_regime"]:
                out[col] = np.nan

        return out

    @staticmethod
    def _union_index(*dfs: pd.DataFrame) -> pd.DatetimeIndex:
        idx = pd.DatetimeIndex([])
        for df in dfs:
            if not df.empty:
                idx = idx.union(df.index)
        return idx.normalize().drop_duplicates().sort_values()


__all__ = ["CrossAssetLoader"]
