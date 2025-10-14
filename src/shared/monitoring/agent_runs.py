"""Utilities for recording AI agent runs for observability and governance."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger(__name__)


@dataclass
class AgentRunRecord:
    stock_code: str
    trade_date: str
    conviction: float
    duration_seconds: float
    timestamp: str
    metadata: Dict[str, Any]


class AgentRunRecorder:
    """Append-only JSONL recorder for agent executions."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def record(self, record: AgentRunRecord) -> None:
        try:
            with self.path.open("a", encoding="utf-8") as fp:
                fp.write(json.dumps(asdict(record)) + "\n")
        except Exception as exc:
            logger.error("Failed to persist agent run record: %s", exc)

    @classmethod
    def from_settings(cls, settings) -> "AgentRunRecorder":
        return cls(Path(settings.LLM_RUN_LOG_PATH))
