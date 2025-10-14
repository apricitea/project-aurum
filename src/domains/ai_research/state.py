"""
State definitions for LLM research agents.
"""

from __future__ import annotations

from datetime import date
from typing import Dict, List, Optional, TypedDict


class ResearchState(TypedDict, total=False):
    stock_code: str
    trade_date: date
    context: Dict
    analyst_notes: List[Dict[str, str]]
    debate_summary: str
    risk_assessment: str
    final_recommendation: str
    confidence: float
    artifacts: Dict[str, str]
