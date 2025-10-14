"""Application service for Auction Market Theory analytics."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import List, Optional

from sqlalchemy.orm import Session

from ....api.database_extensions import AuctionMarketProfile
from ..infrastructure.auction_market_theory import (
    AuctionMarketTheoryCalculator,
    AuctionProfileResult,
)


@dataclass
class AMTComputationResult:
    stock_code: str
    session_date: date
    success: bool
    error: Optional[str] = None


class AuctionMarketTheoryService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def compute_range(
        self,
        stock_code: str,
        start: date,
        end: date,
    ) -> List[AMTComputationResult]:
        calc = AuctionMarketTheoryCalculator(self.session)
        current = start
        results: List[AMTComputationResult] = []
        while current <= end:
            try:
                profile = calc.compute_for_session(stock_code, current)
                if profile:
                    calc.persist_profile(profile)
                    results.append(AMTComputationResult(stock_code, current, True))
                else:
                    results.append(AMTComputationResult(stock_code, current, False, "no_intraday_data"))
            except Exception as exc:
                results.append(AMTComputationResult(stock_code, current, False, str(exc)))
            current += timedelta(days=1)
        self.session.commit()
        return results

    def get_profile(self, stock_code: str, session_date: date) -> Optional[AuctionMarketProfile]:
        return (
            self.session.query(AuctionMarketProfile)
            .filter(
                AuctionMarketProfile.stock_code == stock_code,
                AuctionMarketProfile.session_date == session_date,
            )
            .first()
        )

    def latest_profiles(self, stock_code: str, limit: int = 10) -> List[AuctionMarketProfile]:
        return (
            self.session.query(AuctionMarketProfile)
            .filter(AuctionMarketProfile.stock_code == stock_code)
            .order_by(AuctionMarketProfile.session_date.desc())
            .limit(limit)
            .all()
        )
