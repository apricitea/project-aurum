"""Auction Market Theory calculations for intraday IDX sessions."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from ....api.database_extensions import AuctionMarketProfile, IntradayStockPrice


@dataclass
class AuctionProfileResult:
    stock_code: str
    session_date: date
    point_of_control: float
    value_area_high: float
    value_area_low: float
    initial_balance_high: float
    initial_balance_low: float
    profile_type: str
    total_volume: float
    vwap: float
    single_prints: List[float]
    metrics: Dict[str, float]


class AuctionMarketTheoryCalculator:
    """Computes AMT metrics from intraday OHLCV bars."""

    def __init__(self, session: Session, *, tick_size: float = 5.0) -> None:
        self.session = session
        self.tick_size = tick_size

    def compute_for_session(self, stock_code: str, session_date: date) -> Optional[AuctionProfileResult]:
        df = self._load_intraday_session(stock_code, session_date)
        if df.empty:
            return None

        volume_profile = self._compute_volume_profile(df)
        poc = volume_profile.idxmax()
        vah, val = self._compute_value_area(volume_profile, poc)
        ib_high, ib_low = self._compute_initial_balance(df)

        profile_type = self._classify_profile(df, poc, vah, val)
        single_prints = self._detect_single_prints(volume_profile)

        metrics = {
            "total_volume": float(df["volume"].sum()),
            "session_range": float(df["high"].max() - df["low"].min()),
            "session_high": float(df["high"].max()),
            "session_low": float(df["low"].min()),
            "session_close": float(df["close"].iloc[-1]),
            "session_open": float(df["open"].iloc[0]),
        }

        vwap = float((df["close"] * df["volume"]).sum() / max(1, df["volume"].sum()))

        return AuctionProfileResult(
            stock_code=stock_code,
            session_date=session_date,
            point_of_control=float(poc),
            value_area_high=float(vah),
            value_area_low=float(val),
            initial_balance_high=float(ib_high),
            initial_balance_low=float(ib_low),
            profile_type=profile_type,
            total_volume=metrics["total_volume"],
            vwap=vwap,
            single_prints=[float(x) for x in single_prints],
            metrics=metrics,
        )

    def persist_profile(self, profile: AuctionProfileResult) -> None:
        stmt = pg_insert(AuctionMarketProfile).values(
            stock_code=profile.stock_code,
            session_date=profile.session_date,
            point_of_control=profile.point_of_control,
            value_area_high=profile.value_area_high,
            value_area_low=profile.value_area_low,
            initial_balance_high=profile.initial_balance_high,
            initial_balance_low=profile.initial_balance_low,
            profile_type=profile.profile_type,
            total_volume=profile.total_volume,
            vwap=profile.vwap,
            single_prints=profile.single_prints,
            metrics=profile.metrics,
            open_price=profile.metrics.get("session_open"),
            close_price=profile.metrics.get("session_close"),
            session_range=profile.metrics.get("session_range"),
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=[AuctionMarketProfile.stock_code, AuctionMarketProfile.session_date],
            set_={
                "point_of_control": stmt.excluded.point_of_control,
                "value_area_high": stmt.excluded.value_area_high,
                "value_area_low": stmt.excluded.value_area_low,
                "initial_balance_high": stmt.excluded.initial_balance_high,
                "initial_balance_low": stmt.excluded.initial_balance_low,
                "profile_type": stmt.excluded.profile_type,
                "total_volume": stmt.excluded.total_volume,
                "vwap": stmt.excluded.vwap,
                "single_prints": stmt.excluded.single_prints,
                "metrics": stmt.excluded.metrics,
                "updated_at": datetime.utcnow(),
            },
        )
        self.session.execute(stmt)
        self.session.flush()

    # ------------------------------------------------------------------ #
    # Internals
    # ------------------------------------------------------------------ #

    def _load_intraday_session(self, stock_code: str, session_date: date) -> pd.DataFrame:
        start_dt = datetime.combine(session_date, time(9, 0)) - timedelta(minutes=5)
        end_dt = datetime.combine(session_date, time(15, 59)) + timedelta(minutes=5)
        rows = (
            self.session.query(IntradayStockPrice)
            .filter(
                IntradayStockPrice.stock_code == stock_code,
                IntradayStockPrice.timestamp >= start_dt,
                IntradayStockPrice.timestamp <= end_dt,
            )
            .order_by(IntradayStockPrice.timestamp.asc())
            .all()
        )
        data = [
            {
                "timestamp": row.timestamp,
                "open": row.open_price,
                "high": row.high_price,
                "low": row.low_price,
                "close": row.close_price,
                "volume": row.volume,
            }
            for row in rows
        ]
        return pd.DataFrame(data)

    def _compute_volume_profile(self, df: pd.DataFrame) -> pd.Series:
        df = df.copy()
        df["price_level"] = (df["close"] / self.tick_size).round() * self.tick_size
        profile = df.groupby("price_level")["volume"].sum().sort_index()
        return profile

    def _compute_value_area(self, profile: pd.Series, poc: float, percentage: float = 0.7) -> (float, float):
        total_volume = profile.sum()
        if total_volume == 0:
            return poc, poc
        sorted_levels = profile.sort_values(ascending=False)
        cumulative = 0.0
        value_area = set()
        for price, vol in sorted_levels.items():
            value_area.add(price)
            cumulative += vol
            if cumulative / total_volume >= percentage:
                break
        vah = max(value_area)
        val = min(value_area)
        return vah, val

    def _compute_initial_balance(self, df: pd.DataFrame, duration_minutes: int = 60) -> (float, float):
        if df.empty:
            return math.nan, math.nan
        start_time = df["timestamp"].iloc[0]
        cutoff = start_time + timedelta(minutes=duration_minutes)
        ib = df[df["timestamp"] <= cutoff]
        if ib.empty:
            return math.nan, math.nan
        return ib["high"].max(), ib["low"].min()

    def _classify_profile(self, df: pd.DataFrame, poc: float, vah: float, val: float) -> str:
        if df.empty:
            return "unknown"
        open_price = df["open"].iloc[0]
        close_price = df["close"].iloc[-1]
        range_high = df["high"].max()
        range_low = df["low"].min()
        range_total = range_high - range_low
        if range_total == 0:
            return "balanced"

        if close_price > vah and open_price > poc:
            return "trend_up"
        if close_price < val and open_price < poc:
            return "trend_down"
        if vah - val < 0.5 * range_total:
            return "double_distribution"
        if abs(close_price - open_price) < 0.2 * range_total:
            return "neutral"
        return "normal"

    def _detect_single_prints(self, profile: pd.Series) -> List[float]:
        threshold = profile.mean() * 0.3
        return [price for price, vol in profile.items() if vol < threshold]
