"""
Data access helpers for the AI research agent stack.
Transforms database records into concise textual context for LLM prompts.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional

import pandas as pd
from sqlalchemy.orm import Session

from ..api.database_extensions import (
    DailyStockPrice,
    IntradayStockPrice,
    MarketNewsArticle,
    StockFundamentals,
    StockMaster,
)


@dataclass
class MarketContext:
    stock_code: str
    company_name: str
    metadata: Dict
    price_summary: str
    intraday_summary: str
    fundamentals_summary: str
    news_summary: str


class MarketContextBuilder:
    """
    Builds curated market context packets for downstream LLM agents.
    """

    def __init__(self, session: Session):
        self.session = session

    def build(
        self,
        stock_code: str,
        *,
        lookback_days: int = 120,
        reports: int = 4,
        news_days: int = 10,
    ) -> MarketContext:
        stock = (
            self.session.query(StockMaster)
            .filter(StockMaster.stock_code == stock_code, StockMaster.is_active.is_(True))
            .first()
        )
        if not stock:
            raise ValueError(f"Unknown or inactive stock: {stock_code}")

        price_df = self._load_price_history(stock_code, lookback_days)
        intraday_df = self._load_intraday_history(stock_code)
        fundamentals_df = self._load_fundamentals(stock_code, reports)
        news_df = self._load_recent_news(stock_code, news_days)

        return MarketContext(
            stock_code=stock_code,
            company_name=stock.company_name,
            metadata={
                "sector": stock.sector,
                "industry": stock.industry,
                "market_cap_category": stock.market_cap_category,
                "is_lq45": stock.is_lq45,
            },
            price_summary=self._summarize_price_history(price_df),
            intraday_summary=self._summarize_intraday(intraday_df),
            fundamentals_summary=self._summarize_fundamentals(fundamentals_df),
            news_summary=self._summarize_news(news_df),
        )

    # ------------------------------------------------------------------ #
    # Loaders
    # ------------------------------------------------------------------ #

    def _load_price_history(self, stock_code: str, lookback_days: int) -> pd.DataFrame:
        start_date = date.today() - timedelta(days=int(lookback_days * 1.5))
        rows = (
            self.session.query(DailyStockPrice)
            .filter(
                DailyStockPrice.stock_code == stock_code,
                DailyStockPrice.date >= start_date,
            )
            .order_by(DailyStockPrice.date.asc())
            .all()
        )
        data = [
            {
                "date": row.date,
                "close": row.close_price,
                "volume": row.volume,
                "high": row.high_price,
                "low": row.low_price,
                "open": row.open_price,
            }
            for row in rows
        ]
        return pd.DataFrame(data)

    def _load_intraday_history(self, stock_code: str) -> pd.DataFrame:
        cutoff = datetime.utcnow() - timedelta(days=2)
        rows = (
            self.session.query(IntradayStockPrice)
            .filter(
                IntradayStockPrice.stock_code == stock_code,
                IntradayStockPrice.timestamp >= cutoff,
            )
            .order_by(IntradayStockPrice.timestamp.asc())
            .all()
        )
        data = [
            {
                "timestamp": row.timestamp,
                "close": row.close_price,
                "volume": row.volume,
                "interval": row.interval,
            }
            for row in rows
        ]
        return pd.DataFrame(data)

    def _load_fundamentals(self, stock_code: str, reports: int) -> pd.DataFrame:
        rows = (
            self.session.query(StockFundamentals)
            .filter(StockFundamentals.stock_code == stock_code)
            .order_by(StockFundamentals.report_date.desc())
            .limit(reports)
            .all()
        )
        data = [
            {
                "report_date": row.report_date,
                "report_type": row.report_type,
                "revenue": row.revenue,
                "net_income": row.net_income,
                "ebitda": row.ebitda,
                "gross_margin": row.gross_margin,
                "operating_margin": row.operating_margin,
                "profit_margin": row.profit_margin,
                "return_on_equity": row.return_on_equity,
                "return_on_assets": row.return_on_assets,
                "debt_to_equity": row.debt_to_equity,
                "dividend_yield": row.dividend_yield,
            }
            for row in rows
        ]
        return pd.DataFrame(data)

    def _load_recent_news(self, stock_code: str, days: int) -> pd.DataFrame:
        cutoff = datetime.utcnow() - timedelta(days=days)
        rows = (
            self.session.query(MarketNewsArticle)
            .filter(
                MarketNewsArticle.published_at >= cutoff,
                MarketNewsArticle.stock_codes.contains([stock_code]),
            )
            .order_by(MarketNewsArticle.published_at.desc())
            .limit(20)
            .all()
        )
        data = [
            {
                "published_at": row.published_at,
                "title": row.title,
                "summary": row.summary,
                "sentiment_score": row.sentiment_score,
                "sentiment_label": row.sentiment_label,
                "source": row.source,
            }
            for row in rows
        ]
        return pd.DataFrame(data)

    # ------------------------------------------------------------------ #
    # Summaries
    # ------------------------------------------------------------------ #

    @staticmethod
    def _summarize_price_history(df: pd.DataFrame) -> str:
        if df.empty:
            return "No recent price history available."
        df = df.sort_values("date")
        df["returns"] = df["close"].pct_change()
        last_close = df["close"].iloc[-1]
        weekly_return = df["close"].iloc[-5:].pct_change().iloc[-1] if len(df) >= 5 else None
        monthly_return = df["close"].iloc[-21:].pct_change().iloc[-1] if len(df) >= 21 else None
        volatility = df["returns"].std() * (252 ** 0.5) if df["returns"].std() is not None else None
        avg_volume = df["volume"].tail(21).mean()
        return (
            f"Last close: {last_close:.2f} IDR. "
            f"Weekly return: {MarketContextBuilder._format_pct(weekly_return)}, "
            f"Monthly return: {MarketContextBuilder._format_pct(monthly_return)}. "
            f"Annualized volatility: {MarketContextBuilder._format_pct(volatility)}. "
            f"Average 1M volume: {avg_volume:,.0f}."
        )

    @staticmethod
    def _summarize_intraday(df: pd.DataFrame) -> str:
        if df.empty:
            return "No intraday data captured in the last two days."
        latest = df.iloc[-1]
        interval = latest["interval"]
        intraday_vol = df["volume"].sum()
        price_range = df["close"].max() - df["close"].min()
        return (
            f"Intraday interval {interval}: volume {intraday_vol:,.0f}, "
            f"price range {price_range:.2f} IDR over last {len(df)} bars."
        )

    @staticmethod
    def _summarize_fundamentals(df: pd.DataFrame) -> str:
        if df.empty:
            return "Fundamental reports not yet ingested."
        latest = df.iloc[0]
        growth = None
        if len(df) > 1 and df["revenue"].iloc[1]:
            growth = (latest["revenue"] - df["revenue"].iloc[1]) / abs(df["revenue"].iloc[1])
        parts = [
            f"Latest {latest['report_type']} report on {latest['report_date']}:",
            f"Revenue {MarketContextBuilder._format_number(latest['revenue'])} IDR,"
            f" Net income {MarketContextBuilder._format_number(latest['net_income'])} IDR.",
            f"Margins: gross {MarketContextBuilder._format_pct(latest['gross_margin'])}, "
            f"operating {MarketContextBuilder._format_pct(latest['operating_margin'])}, "
            f"net {MarketContextBuilder._format_pct(latest['profit_margin'])}.",
            f"ROE {MarketContextBuilder._format_pct(latest['return_on_equity'])}, "
            f"ROA {MarketContextBuilder._format_pct(latest['return_on_assets'])}, "
            f"D/E {MarketContextBuilder._format_number(latest['debt_to_equity'])}.",
        ]
        if growth is not None:
            parts.append(f"Year-over-year revenue growth {MarketContextBuilder._format_pct(growth)}.")
        if latest.get("dividend_yield") is not None:
            parts.append(f"Dividend yield {MarketContextBuilder._format_pct(latest['dividend_yield'])}.")
        return " ".join(parts)

    @staticmethod
    def _summarize_news(df: pd.DataFrame) -> str:
        if df.empty:
            return "No relevant news in the last period."
        sentiments = df["sentiment_score"].dropna()
        aggregate_sentiment = sentiments.mean() if not sentiments.empty else 0
        top_headlines = "; ".join(df.head(3)["title"].tolist())
        return (
            f"{len(df)} news items in the last period. "
            f"Average sentiment score {aggregate_sentiment:.2f}. "
            f"Top headlines: {top_headlines}"
        )

    # ------------------------------------------------------------------ #
    # Formatting helpers
    # ------------------------------------------------------------------ #

    @staticmethod
    def _format_pct(value: Optional[float]) -> str:
        if value is None or pd.isna(value):
            return "n/a"
        return f"{value:.2%}"

    @staticmethod
    def _format_number(value: Optional[float]) -> str:
        if value is None or pd.isna(value):
            return "n/a"
        return f"{value:,.0f}"
