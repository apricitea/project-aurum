"""
LangGraph assembly for the LLM research workflow.
"""

from __future__ import annotations

from langgraph.graph import END, StateGraph
from langgraph.checkpoint import MemorySaver

from .agents import (
    DebateCoordinatorAgent,
    FundamentalAnalystAgent,
    LLMClientParams,
    NewsAnalystAgent,
    RiskManagerAgent,
    TechnicalAnalystAgent,
    TraderAgent,
    build_llm_client,
)
from .state import ResearchState


class ResearchGraphFactory:
    """
    Builds the multi-agent research graph with configurable LLM backends.
    """

    def __init__(
        self,
        params: LLMClientParams,
        *,
        memory: bool = True,
    ) -> None:
        self.params = params
        self.memory = memory

    def create(self) -> StateGraph:
        fast_llm = build_llm_client(self.params, fast=True)
        deep_llm = build_llm_client(self.params, fast=False)

        sg = StateGraph(ResearchState)

        sg.add_node("fundamental", FundamentalAnalystAgent("fundamental", FUNDAMENTAL_PROMPT, deep_llm))
        sg.add_node("technical", TechnicalAnalystAgent("technical", TECHNICAL_PROMPT, fast_llm))
        sg.add_node("news", NewsAnalystAgent("news", NEWS_PROMPT, fast_llm))
        sg.add_node("debate", DebateCoordinatorAgent("debate", DEBATE_PROMPT, fast_llm))
        sg.add_node("risk", RiskManagerAgent("risk", RISK_PROMPT, deep_llm))
        sg.add_node("trader", TraderAgent("trader", TRADER_PROMPT, deep_llm))

        sg.set_entry_point("fundamental")
        sg.add_edge("fundamental", "technical")
        sg.add_edge("technical", "news")
        sg.add_edge("news", "debate")
        sg.add_edge("debate", "risk")
        sg.add_edge("risk", "trader")
        sg.add_edge("trader", END)

        if self.memory:
            return sg.compile(checkpointer=MemorySaver())
        return sg.compile()


FUNDAMENTAL_PROMPT = (
    "You are a fundamental analyst specializing in Indonesian equities. "
    "Deliver a balanced view covering financial strength, growth trends, and valuation."
)

TECHNICAL_PROMPT = (
    "You are a technical analyst. Focus on trend, momentum, support/resistance, and notable indicators."
)

NEWS_PROMPT = (
    "You are a news and sentiment analyst. Highlight catalysts, policy changes, and overall sentiment."
)

DEBATE_PROMPT = (
    "You moderate the debate outcome. Synthesize analyst notes into a coherent storyline with pros/cons."
)

RISK_PROMPT = (
    "You are a risk manager. Evaluate position sizing, volatility, liquidity, and adverse scenarios."
)

TRADER_PROMPT = (
    "You are the head trader. Translate research into a clear action (buy/sell/hold) with conviction and timing."
)
