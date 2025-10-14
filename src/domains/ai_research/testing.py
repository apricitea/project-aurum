"""
Testing utilities for AI research agents.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List

from langchain_core.messages import BaseMessage, AIMessage


@dataclass
class MockLLM:
    """
    Lightweight mock for ChatModel interfaces used in unit tests.
    """

    response: str = "Mock response."

    def invoke(self, messages: List[BaseMessage], **_: Any) -> AIMessage:
        return AIMessage(content=self.response)
