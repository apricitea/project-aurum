#!/usr/bin/env python
"""
CLI entry point for running the LLM research orchestrator.
"""

from __future__ import annotations

import argparse
from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.api.config import settings
from src.domains.ai_research import ResearchConfig, ResearchOrchestrator


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run LLM research agents for a given stock.")
    parser.add_argument("--stock", required=True, help="IDX stock code (e.g., BBCA)")
    parser.add_argument(
        "--date",
        default=datetime.utcnow().date().isoformat(),
        help="Trade date in YYYY-MM-DD (default: today)",
    )
    parser.add_argument("--notes", default="", help="Additional analyst notes to seed the agents")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    engine = create_engine(settings.get_database_url())
    SessionFactory = sessionmaker(bind=engine)

    orchestrator = ResearchOrchestrator(SessionFactory)
    report = orchestrator.run(
        ResearchConfig(
            stock_code=args.stock.upper(),
            trade_date=datetime.strptime(args.date, "%Y-%m-%d").date(),
            notes=args.notes,
        )
    )

    print("\n=== Research Report ===")
    print(f"Stock: {report.stock_code}")
    print(f"Trade Date: {report.trade_date}")
    print(f"Conviction: {report.conviction:.2f}")
    print("\n-- Analyst Notes --")
    for role, note in report.analyst_notes.items():
        print(f"[{role}] {note}\n")
    print("-- Debate Summary --")
    print(report.debate_summary)
    print("\n-- Risk Assessment --")
    print(report.risk_assessment)
    print("\n-- Final Recommendation --")
    print(report.final_recommendation)


if __name__ == "__main__":
    main()
