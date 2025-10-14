"""
Agent role implementations for the LLM trading research workflow.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

try:
    from langchain_anthropic import ChatAnthropic
except ImportError:  # pragma: no cover - optional dependency
    ChatAnthropic = None

try:
    from langchain_google_genai import ChatGoogleGenerativeAI
except ImportError:  # pragma: no cover - optional dependency
    ChatGoogleGenerativeAI = None

from .state import ResearchState


class LLMAgent:
    def __init__(self, name: str, system_prompt: str, llm_client) -> None:
        self.name = name
        self.system_prompt = system_prompt
        self.llm_client = llm_client

    def __call__(self, state: ResearchState) -> Dict:
        raise NotImplementedError

    def _invoke(self, user_prompt: str) -> str:
        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=user_prompt),
        ]
        response = self.llm_client.invoke(messages)
        return response.content if hasattr(response, "content") else str(response)


class FundamentalAnalystAgent(LLMAgent):
    def __call__(self, state: ResearchState) -> Dict:
        context = state["context"]
        prompt = (
            f"Company metadata: {context['metadata']}.\n"
            f"Fundamental summary: {context['fundamentals_summary']}.\n"
            "Please assess intrinsic value drivers, growth outlook, and key risks."
        )
        analysis = self._invoke(prompt)
        return {"analyst_notes": state.get("analyst_notes", []) + [{"role": "fundamental", "analysis": analysis}]}


class TechnicalAnalystAgent(LLMAgent):
    def __call__(self, state: ResearchState) -> Dict:
        context = state["context"]
        prompt = (
            f"Price summary: {context['price_summary']}.\n"
            f"Intraday summary: {context['intraday_summary']}.\n"
            "Identify technical patterns, momentum, and support/resistance levels relevant for a short-term trade."
        )
        analysis = self._invoke(prompt)
        return {"analyst_notes": state.get("analyst_notes", []) + [{"role": "technical", "analysis": analysis}]}


class NewsAnalystAgent(LLMAgent):
    def __call__(self, state: ResearchState) -> Dict:
        context = state["context"]
        prompt = (
            f"News summary: {context['news_summary']}.\n"
            "Evaluate sentiment drivers, catalysts, and any macro factors impacting the stock."
        )
        analysis = self._invoke(prompt)
        return {"analyst_notes": state.get("analyst_notes", []) + [{"role": "news", "analysis": analysis}]}


class DebateCoordinatorAgent(LLMAgent):
    def __call__(self, state: ResearchState) -> Dict:
        notes = state.get("analyst_notes", [])
        prompt = (
            "You are summarizing a debate between analysts. "
            "Highlight points of agreement, disagreement, and actionable insights.\n\n"
            f"Analyst contributions: {notes}"
        )
        summary = self._invoke(prompt)
        return {"debate_summary": summary}


class RiskManagerAgent(LLMAgent):
    def __call__(self, state: ResearchState) -> Dict:
        context = state["context"]
        summary = state.get("debate_summary", "")
        prompt = (
            f"Context: {context['metadata']}.\n"
            f"Price summary: {context['price_summary']}.\n"
            f"Debate summary: {summary}.\n"
            "Assess position sizing, scenario risks, and compliance with mandate constraints."
        )
        assessment = self._invoke(prompt)
        return {"risk_assessment": assessment}


class TraderAgent(LLMAgent):
    def __call__(self, state: ResearchState) -> Dict:
        summary = state.get("debate_summary", "")
        risk_assessment = state.get("risk_assessment", "")
        prompt = (
            f"Debate summary: {summary}.\n"
            f"Risk assessment: {risk_assessment}.\n"
            "Provide a final trading recommendation (buy/sell/hold) with conviction score (0-1) and execution notes."
        )
        decision = self._invoke(prompt)
        return {
            "final_recommendation": decision,
            "confidence": 0.0,  # will be parsed downstream
        }


@dataclass
class LLMClientParams:
    provider: str
    primary_model: str
    secondary_model: Optional[str] = None
    base_url: Optional[str] = None
    temperature: float = 0.4
    timeout: int = 120


def build_llm_client(params: LLMClientParams, *, fast: bool = False):
    model = params.secondary_model if fast and params.secondary_model else params.primary_model
    provider = params.provider.lower()

    if provider == "openai":
        return ChatOpenAI(
            model=model,
            base_url=params.base_url,
            temperature=params.temperature,
            timeout=params.timeout,
        )
    if provider == "anthropic":
        if ChatAnthropic is None:
            raise ImportError("langchain-anthropic is not installed.")
        return ChatAnthropic(
            model=model,
            base_url=params.base_url,
            temperature=params.temperature,
            timeout=params.timeout,
        )
    if provider == "google":
        if ChatGoogleGenerativeAI is None:
            raise ImportError("langchain-google-genai is not installed.")
        return ChatGoogleGenerativeAI(model=model, temperature=params.temperature)
    raise ValueError(f"Unsupported LLM provider: {params.provider}")
