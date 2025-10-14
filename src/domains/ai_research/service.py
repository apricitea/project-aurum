"""High-level orchestration for running LLM agent research within Project Aurum."""

from __future__ import annotations

import logging
import re
import time
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime
from typing import Dict, Optional

from sqlalchemy.orm import Session, sessionmaker

from ..api.config import settings
from ...shared.monitoring.agent_runs import AgentRunRecord, AgentRunRecorder
from .agents import LLMClientParams
from .graph import ResearchGraphFactory
from .state import ResearchState
from .tools import MarketContextBuilder


@dataclass
class ResearchConfig:
    stock_code: str
    trade_date: date
    notes: Optional[str] = None


@dataclass
class ResearchReport:
    stock_code: str
    trade_date: date
    analyst_notes: Dict[str, str]
    debate_summary: str
    risk_assessment: str
    final_recommendation: str
    conviction: float
    timestamp: datetime


class ResearchOrchestrator:
    """
    Integrates TradingAgents-inspired multi-agent workflow with Project Aurum data.
    """

    def __init__(
        self,
        session_factory: sessionmaker,
        *,
        llm_params: Optional[LLMClientParams] = None,
        recorder: Optional[AgentRunRecorder] = None,
    ) -> None:
        self.session_factory = session_factory
        self.llm_params = llm_params or LLMClientParams(
            provider=settings.LLM_PROVIDER,
            primary_model=settings.LLM_PRIMARY_MODEL,
            secondary_model=settings.LLM_SECONDARY_MODEL,
            base_url=settings.LLM_BASE_URL,
            temperature=settings.LLM_TEMPERATURE,
            timeout=settings.LLM_TIMEOUT_SECONDS,
        )
        self.graph_factory = ResearchGraphFactory(self.llm_params)
        self.recorder = recorder or AgentRunRecorder.from_settings(settings)
        self.logger = logging.getLogger(__name__)

    def run(self, config: ResearchConfig) -> ResearchReport:
        start = time.perf_counter()
        app = self.graph_factory.create()

        with self._session_scope() as session:
            builder = MarketContextBuilder(session)
            context = builder.build(config.stock_code)

        state: ResearchState = {
            "stock_code": config.stock_code,
            "trade_date": config.trade_date,
            "context": {
                "metadata": context.metadata,
                "price_summary": context.price_summary,
                "intraday_summary": context.intraday_summary,
                "fundamentals_summary": context.fundamentals_summary,
                "news_summary": context.news_summary,
            },
            "analyst_notes": [],
            "artifacts": {"notes": config.notes or ""},
        }

        result = app.invoke(state)

        analyst_notes = {note["role"]: note["analysis"] for note in result.get("analyst_notes", [])}
        recommendation_text = result.get("final_recommendation", "")
        conviction = self._extract_conviction(recommendation_text)
        duration = time.perf_counter() - start

        report = ResearchReport(
            stock_code=config.stock_code,
            trade_date=config.trade_date,
            analyst_notes=analyst_notes,
            debate_summary=result.get("debate_summary", ""),
            risk_assessment=result.get("risk_assessment", ""),
            final_recommendation=recommendation_text,
            conviction=conviction,
            timestamp=datetime.utcnow(),
        )

        self.logger.info(
            "AI research run completed",
            extra={
                "stock_code": report.stock_code,
                "trade_date": str(report.trade_date),
                "conviction": report.conviction,
                "duration_seconds": round(duration, 3),
            },
        )

        if self.recorder:
            record = AgentRunRecord(
                stock_code=report.stock_code,
                trade_date=str(report.trade_date),
                conviction=report.conviction,
                duration_seconds=duration,
                timestamp=report.timestamp.isoformat(),
                metadata={
                    "notes_length": len(report.analyst_notes),
                    "llm_provider": self.llm_params.provider,
                },
            )
            self.recorder.record(record)

        return report

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    @contextmanager
    def _session_scope(self):
        session: Session = self.session_factory()
        try:
            yield session
        finally:
            session.close()

    @staticmethod
    def _extract_conviction(text: str) -> float:
        match = re.search(r"([0-1](?:\.\d+)?)", text)
        if not match:
            return 0.0
        try:
            return float(match.group(1))
        except ValueError:
            return 0.0
