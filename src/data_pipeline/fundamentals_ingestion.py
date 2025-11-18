"""
Fundamental Data Ingestion Service
Retrieves IDX company fundamentals from public sources (Alpha Vantage, OJK filings)
Stores both raw filings metadata and normalized financial metrics.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Iterable, List, Optional, Tuple

import requests
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from ..api.database_extensions import (
    DataRefreshLog,
    FundamentalReport,
    StockFundamentals,
    StockMaster,
)

logger = logging.getLogger(__name__)

ALPHA_VANTAGE_BASE_URL = "https://www.alphavantage.co/query"
ALPHA_FUNCTIONS = ("OVERVIEW", "BALANCE_SHEET", "INCOME_STATEMENT", "CASH_FLOW")


@dataclass
class FundamentalsIngestionResult:
    stock_code: str
    success: bool
    reports_saved: int
    metrics_saved: int
    error_message: Optional[str] = None


class FundamentalsIngestionService:
    """
    Collects and normalizes fundamental data suitable for LLM agents and ML pipelines.
    Primary provider is Alpha Vantage due to generous open-source limits.
    Stub hooks allow future integration with OJK / IDX filings and PDFs.
    """

    def __init__(
        self,
        db_session: Session,
        *,
        alpha_vantage_api_key: Optional[str] = None,
        throttle_seconds: float = 12.0,
    ) -> None:
        self.db_session = db_session
        self.alpha_vantage_api_key = alpha_vantage_api_key or os.getenv("ALPHA_VANTAGE_API_KEY")
        if not self.alpha_vantage_api_key:
            raise ValueError("Alpha Vantage API key is required for fundamentals ingestion.")
        self.throttle_seconds = throttle_seconds

    def ingest_fundamentals(
        self,
        stock_codes: Optional[List[str]] = None,
        include_quarterly: bool = True,
        include_annual: bool = True,
    ) -> Tuple[List[FundamentalsIngestionResult], str]:
        stocks = self._resolve_symbols(stock_codes)
        if not stocks:
            raise ValueError("No active stocks available for fundamentals ingestion.")

        job_id, job_log = self._start_job(stocks, include_quarterly, include_annual)

        results: List[FundamentalsIngestionResult] = []
        total_reports = 0
        total_metrics = 0
        total_failed = 0

        try:
            for stock in stocks:
                try:
                    reports, metrics = self._ingest_single_stock(
                        stock_code=stock.stock_code,
                        yahoo_symbol=stock.yahoo_symbol,
                        include_quarterly=include_quarterly,
                        include_annual=include_annual,
                    )
                    results.append(
                        FundamentalsIngestionResult(
                            stock_code=stock.stock_code,
                            success=True,
                            reports_saved=reports,
                            metrics_saved=metrics,
                        )
                    )
                    total_reports += reports
                    total_metrics += metrics
                except Exception as exc:
                    logger.warning("Fundamentals ingestion failed for %s: %s", stock.stock_code, exc)
                    results.append(
                        FundamentalsIngestionResult(
                            stock_code=stock.stock_code,
                            success=False,
                            reports_saved=0,
                            metrics_saved=0,
                            error_message=str(exc),
                        )
                    )
                    total_failed += 1

                time.sleep(self.throttle_seconds)  # Respect Alpha Vantage free tier

            job_log.completed_at = datetime.utcnow()
            job_log.status = "completed" if total_failed == 0 else "partial"
            job_log.records_inserted = total_reports + total_metrics
            job_log.records_processed = total_reports + total_metrics
            job_log.records_failed = total_failed
            job_log.duration_seconds = (job_log.completed_at - job_log.started_at).total_seconds()

            self.db_session.commit()
            return results, job_id
        except Exception as exc:
            logger.exception("Fundamentals ingestion job %s failed: %s", job_id, exc)
            job_log.status = "failed"
            job_log.completed_at = datetime.utcnow()
            job_log.error_message = str(exc)
            self.db_session.commit()
            raise

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _resolve_symbols(self, stock_codes: Optional[List[str]]) -> List[StockMaster]:
        query = self.db_session.query(StockMaster).filter(StockMaster.is_active.is_(True))
        if stock_codes:
            query = query.filter(StockMaster.stock_code.in_(stock_codes))
        return query.all()

    def _start_job(
        self,
        stocks: Iterable[StockMaster],
        include_quarterly: bool,
        include_annual: bool,
    ) -> Tuple[str, DataRefreshLog]:
        job = DataRefreshLog(
            job_name="fundamentals_ingest",
            job_type="fundamentals",
            started_at=datetime.utcnow(),
            status="running",
            stock_codes=[s.stock_code for s in stocks],
            meta_data={
                "include_quarterly": include_quarterly,
                "include_annual": include_annual,
                "provider": "alpha_vantage",
            },
        )
        self.db_session.add(job)
        self.db_session.commit()
        return str(job.id), job

    def _ingest_single_stock(
        self,
        *,
        stock_code: str,
        yahoo_symbol: str,
        include_quarterly: bool,
        include_annual: bool,
    ) -> Tuple[int, int]:
        raw_payloads: Dict[str, Dict] = {}
        for function in ALPHA_FUNCTIONS:
            payload = self._fetch_alpha_vantage(function, yahoo_symbol)
            raw_payloads[function] = payload
            self._persist_raw_report(stock_code, yahoo_symbol, function, payload)

        metrics_saved = self._persist_parsed_metrics(
            stock_code=stock_code,
            payloads=raw_payloads,
            include_quarterly=include_quarterly,
            include_annual=include_annual,
        )

        reports_saved = len(ALPHA_FUNCTIONS)
        return reports_saved, metrics_saved

    def _fetch_alpha_vantage(self, function: str, symbol: str) -> Dict:
        params = {"function": function, "symbol": symbol, "apikey": self.alpha_vantage_api_key}
        response = requests.get(ALPHA_VANTAGE_BASE_URL, params=params, timeout=30)
        if not response.ok:
            raise ValueError(f"Alpha Vantage request failed ({response.status_code}): {response.text}")
        data = response.json()
        if "Note" in data:
            raise ValueError(f"Alpha Vantage throttled the request: {data['Note']}")
        return data

    def _persist_raw_report(self, stock_code: str, symbol: str, function: str, payload: Dict) -> None:
        serialized = json.dumps(payload, sort_keys=True).encode("utf-8")
        content_hash = hashlib.sha256(serialized).hexdigest()
        stmt = pg_insert(FundamentalReport).values(
            stock_code=stock_code,
            report_date=datetime.utcnow().date(),
            report_type=function.lower(),
            period_start=None,
            period_end=None,
            document_type="json",
            source="alpha_vantage",
            source_url=f"{ALPHA_VANTAGE_BASE_URL}?function={function}&symbol={symbol}",
            storage_path=None,
            content_hash=content_hash,
            is_parsed=True,
            meta_data={"payload_size": len(serialized)},
        )
        stmt = stmt.on_conflict_do_nothing(index_elements=["content_hash"])
        self.db_session.execute(stmt)
        self.db_session.flush()

    def _persist_parsed_metrics(
        self,
        *,
        stock_code: str,
        payloads: Dict[str, Dict],
        include_quarterly: bool,
        include_annual: bool,
    ) -> int:
        overview = payloads.get("OVERVIEW", {})
        income_statement = payloads.get("INCOME_STATEMENT", {})
        balance_sheet = payloads.get("BALANCE_SHEET", {})
        cash_flow = payloads.get("CASH_FLOW", {})

        records: List[Dict] = []

        if include_annual:
            records.extend(
                self._build_fundamental_records(
                    stock_code=stock_code,
                    report_type="annual",
                    overview=overview,
                    income_reports=income_statement.get("annualReports", []),
                    balance_reports=balance_sheet.get("annualReports", []),
                    cashflow_reports=cash_flow.get("annualReports", []),
                )
            )
        if include_quarterly:
            records.extend(
                self._build_fundamental_records(
                    stock_code=stock_code,
                    report_type="quarterly",
                    overview=overview,
                    income_reports=income_statement.get("quarterlyReports", []),
                    balance_reports=balance_sheet.get("quarterlyReports", []),
                    cashflow_reports=cash_flow.get("quarterlyReports", []),
                )
            )

        if not records:
            return 0

        stmt = pg_insert(StockFundamentals).values(records)
        update_cols = {
            "market_cap": stmt.excluded.market_cap,
            "pe_ratio": stmt.excluded.pe_ratio,
            "pb_ratio": stmt.excluded.pb_ratio,
            "ps_ratio": stmt.excluded.ps_ratio,
            "dividend_yield": stmt.excluded.dividend_yield,
            "revenue": stmt.excluded.revenue,
            "net_income": stmt.excluded.net_income,
            "ebitda": stmt.excluded.ebitda,
            "gross_profit": stmt.excluded.gross_profit,
            "operating_income": stmt.excluded.operating_income,
            "gross_margin": stmt.excluded.gross_margin,
            "operating_margin": stmt.excluded.operating_margin,
            "profit_margin": stmt.excluded.profit_margin,
            "total_assets": stmt.excluded.total_assets,
            "total_liabilities": stmt.excluded.total_liabilities,
            "total_equity": stmt.excluded.total_equity,
            "cash_and_equivalents": stmt.excluded.cash_and_equivalents,
            "total_debt": stmt.excluded.total_debt,
            "current_ratio": stmt.excluded.current_ratio,
            "debt_to_equity": stmt.excluded.debt_to_equity,
            "return_on_equity": stmt.excluded.return_on_equity,
            "return_on_assets": stmt.excluded.return_on_assets,
            "earnings_per_share": stmt.excluded.earnings_per_share,
            "book_value_per_share": stmt.excluded.book_value_per_share,
            "meta_data": stmt.excluded.meta_data,
            "data_source": stmt.excluded.data_source,
            "updated_at": datetime.utcnow(),
        }
        stmt = stmt.on_conflict_do_update(
            index_elements=["stock_code", "report_date", "report_type"],
            set_=update_cols,
        )
        self.db_session.execute(stmt)
        self.db_session.flush()
        return len(records)

    def _build_fundamental_records(
        self,
        *,
        stock_code: str,
        report_type: str,
        overview: Dict,
        income_reports: List[Dict],
        balance_reports: List[Dict],
        cashflow_reports: List[Dict],
    ) -> List[Dict]:
        records: List[Dict] = []

        # Index reports by fiscal period for consistent joins
        income_index = {r.get("fiscalDateEnding"): r for r in income_reports}
        balance_index = {r.get("fiscalDateEnding"): r for r in balance_reports}
        cash_index = {r.get("fiscalDateEnding"): r for r in cashflow_reports}

        all_periods = set(income_index.keys()) | set(balance_index.keys()) | set(cash_index.keys())

        for period in sorted(all_periods, reverse=True):
            if not period:
                continue
            report_date = datetime.strptime(period, "%Y-%m-%d").date()
            income = income_index.get(period, {})
            balance = balance_index.get(period, {})
            cash_flow = cash_index.get(period, {})

            market_cap = self._safe_float(overview.get("MarketCapitalization"))
            shares_outstanding = self._safe_float(overview.get("SharesOutstanding"))

            revenue = self._safe_float(income.get("totalRevenue"))
            net_income = self._safe_float(income.get("netIncome"))
            ebitda = self._safe_float(income.get("ebitda"))
            gross_profit = self._safe_float(income.get("grossProfit"))
            operating_income = self._safe_float(income.get("operatingIncome"))
            total_assets = self._safe_float(balance.get("totalAssets"))
            total_liabilities = self._safe_float(balance.get("totalLiabilities"))
            total_equity = self._safe_float(balance.get("totalShareholderEquity"))
            cash_and_equivalents = self._safe_float(balance.get("cashAndCashEquivalentsAtCarryingValue"))
            total_debt = self._safe_float(balance.get("shortLongTermDebtTotal"))

            record = dict(
                stock_code=stock_code,
                report_date=report_date,
                report_type=report_type,
                market_cap=market_cap,
                pe_ratio=self._safe_float(overview.get("PERatio")),
                pb_ratio=self._safe_float(overview.get("PriceToBookRatio")),
                ps_ratio=self._derive_ps_ratio(market_cap, revenue),
                dividend_yield=self._safe_float(overview.get("DividendYield")),
                revenue=revenue,
                net_income=net_income,
                ebitda=ebitda,
                gross_profit=gross_profit,
                operating_income=operating_income,
                gross_margin=self._compute_ratio(gross_profit, revenue),
                operating_margin=self._compute_ratio(operating_income, revenue),
                profit_margin=self._compute_ratio(net_income, revenue),
                total_assets=total_assets,
                total_liabilities=total_liabilities,
                total_equity=total_equity,
                cash_and_equivalents=cash_and_equivalents,
                total_debt=total_debt,
                current_ratio=self._compute_ratio(
                    self._safe_float(balance.get("totalCurrentAssets")),
                    self._safe_float(balance.get("totalCurrentLiabilities")),
                ),
                debt_to_equity=self._compute_ratio(total_debt, total_equity),
                return_on_equity=self._compute_ratio(net_income, total_equity),
                return_on_assets=self._compute_ratio(net_income, total_assets),
                earnings_per_share=self._safe_float(income.get("eps")),
                book_value_per_share=self._compute_ratio(total_equity, shares_outstanding),
                data_source="alpha_vantage",
                meta_data={
                    "period": period,
                    "report_type": report_type,
                    "source_payloads": {
                        "income": bool(income),
                        "balance": bool(balance),
                        "cashflow": bool(cash_flow),
                    },
                },
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )

            records.append(record)
        return records

    @staticmethod
    def _safe_float(value: Optional[str]) -> Optional[float]:
        try:
            if value in (None, "", "None"):
                return None
            return float(value)
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _compute_ratio(numerator: Optional[float], denominator: Optional[float]) -> Optional[float]:
        if numerator is None or denominator in (None, 0):
            return None
        try:
            return numerator / denominator
        except ZeroDivisionError:
            return None

    @staticmethod
    def _derive_ps_ratio(market_cap: Optional[float], revenue: Optional[float]) -> Optional[float]:
        if market_cap is None or revenue in (None, 0):
            return None
        return market_cap / revenue


__all__ = ["FundamentalsIngestionService", "FundamentalsIngestionResult"]
