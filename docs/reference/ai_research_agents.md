# AI Research Agents Overview

## Purpose
Project Aurum now embeds a LangGraph-based multi-agent workflow inspired by Tauric Research's *TradingAgents* framework. The system produces narrative-rich trading intelligence that complements existing ML signals.

## Architecture
- **Context Builder** (`src/domains/ai_research/tools.py`) aggregates price history, intraday bars, fundamentals, and news directly from Aurum's databases.
- **Agent Graph** (`src/domains/ai_research/graph.py`) coordinates fundamental, technical, news, debate, risk, and trader roles using configurable LLM backends.
- **Service Layer** (`src/domains/ai_research/service.py`) exposes a `ResearchOrchestrator` that downstream components (API, CLI, dashboard) can invoke.
- **CLI** (`scripts/run_ai_research.py`) allows manual execution for validation or ad-hoc research.

## Execution Flow
1. Build market context for the requested IDX ticker.
2. Analysts (fundamental, technical, news) generate role-specific insights.
3. Debate coordinator synthesizes consensus.
4. Risk manager evaluates sizing and constraints.
5. Trader agent issues final recommendation with conviction score.

## Configuration
LLM parameters are sourced from `settings` (`src/api/config.py`). Supported providers include OpenAI, Anthropic, and Google (optional dependencies).

## Next Steps
- Add caching and evaluation harness for repeatability.
- Expose REST/WebSocket endpoints (Phase 4).
- Extend debate stage with bear/bull personas and memory persistence.
