"""
Minimal stubs for legacy imports.

The original notebooks referenced `main_pipeline` for orchestration, but
that module isn't part of the current codebase.  We provide lightweight
stand-ins so the API can start up without ImportErrors.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

import pandas as pd


class DataCollector:
    """Stub collector that returns empty data frames."""

    def collect_daily_data(self) -> Dict[str, Any]:
        return {
            "price_data": pd.DataFrame(),
            "fundamental_data": pd.DataFrame(),
        }


@dataclass
class TradingPipeline:
    """Placeholder trading pipeline."""

    config: Dict[str, Any] | None = None

    def run(self) -> None:
        return None
