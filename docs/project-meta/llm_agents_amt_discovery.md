# Project Aurum – LLM Agents & Auction Market Theory Expansion

## 1. Executive Summary
- **Objective**: integrate multi-agent LLM research workflows and Auction Market Theory (AMT) analytics into Project Aurum to enhance IDX-focused decision making.
- **Drivers**: richer qualitative context, transparent strategy debates, improved structural market insights, and actionable visualizations for discretionary or systematic traders.
- **Constraints**: personal-scale operations, reliance on publicly accessible data feeds, controlled API spend, and compliance with IDX data usage guidelines.
- **Success Criteria**: measurable uplift in signal quality and user engagement while maintaining sub-minute operational latency and predictable operating costs.

## 2. Requirements Alignment
| Category | Requirement | Source | Notes |
| --- | --- | --- | --- |
| Use Cases | Research agents synthesize fundamentals, news, sentiment, technicals for IDX equities | User brief | Extend dashboard with LLM-generated reports & confidence metrics |
| Use Cases | AMT metrics (profiles, value area, anomalies) augment signal and visualization layers | User brief | Intraday or pseudo-intraday data needed |
| Data | Only use public, scrapable, or LLM-acquirable datasets | User brief | Avoid paid market data licenses |
| Architecture | Integrate within existing FastAPI + React stack | Project docs | Services presented via existing API gateway |
| Ops | Scalable for personal use | User brief | Target local or single-cloud deployment, modest cost ceiling |
| Quality | Follow state-of-the-art yet pragmatic methods | Instruction | Prioritize robustness, reproducibility, observability |

## 3. Stakeholder & Risk Checklist
- Confirm tolerance for estimated monthly LLM spend (default forecast in §6).
- Confirm acceptance of AlphaVantage / Yahoo Finance / scraping terms of service for IDX symbols.
- Verify any compliance requirements for distributing LLM outputs (e.g., disclaimers, auditability).
- Establish fallback expectations if intraday IDX data accessibility degrades.

## 4. Codebase Audit Highlights
- `src/domains/trading/application/services/signal_generator.py` – deterministic ML/risk pipeline; prime integration point for AMT-enhanced features and agent outputs.
- `src/data_pipeline` – mature daily ETL with yfinance, Postgres support; needs extension for intraday bars and qualitative datasets.
- `TradingAgents/tradingagents` – LangGraph-based agent orchestration (analyst → researcher → trader → risk → PM). Modular design enabling reuse with custom tool bindings.
- `apps/web_dashboard` – modular React dashboard; ready to accept new API endpoints for AMT panels and research briefings.
- Observed gaps: no dedicated feature store, no LLM service layer, no AMT computation modules, limited observability for new workloads.

## 5. Data Source Feasibility Matrix
| Dataset | Candidate Source | Access Mode | Coverage | Cost | Risks / Mitigations |
| --- | --- | --- | --- | --- | --- |
| Daily & intraday OHLCV | Yahoo Finance (public API via yfinance) | REST-like unofficial endpoints | Daily ✅ / 5m intraday ✅ | Free | Rate limiting, symbol mapping – mitigate with caching, staggered schedules |
| Daily & intraday OHLCV | IDX website (JSON, CSV, HTML) | Web scraping | Comprehensive | Free | HTML structure drift – build parser abstraction & monitoring |
| Fundamentals (financials) | IDX filings, OJK (annual/quarterly PDFs/HTML) | Scraping + PDF parsing | Core constituents | Free | Parsing complexity – schedule nightly ingestion, store raw artifacts |
| Fundamentals | AlphaVantage fundamentals API | Official API (free tier 5 req/min) | Global coverage, incl. IDX | Free (tier) | Throttling – queue requests, cache responses |
| News & Sentiment | Google News RSS, TradingEconomics headlines | HTTP feeds | Global + local finance | Free | Sentiment quality – ensemble with transformer sentiment model |
| Sentiment | Twitter/X scraping via snscrape | CLI scraping | Mixed coverage | Free | TOS grey area – optional, toggle in config |
| Macro | Bank Indonesia, IMF datasets | CSV/JSON download | Good | Free | Update frequency – cron-based ingestion |
| Auction Market microstructure data | If intraday limited, build synthetic via aggregated tick data proxies | Derived | Dependent | Free | Accuracy vs actual tick – validate on replay periods |

## 6. Preliminary Cost & Resource Model
| Component | Volume Assumption | Unit Cost | Monthly Estimate | Notes |
| --- | --- | --- | --- | --- |
| LLM research runs | 200 agent sessions / month, avg 250K tokens | $15 / 1M tokens (e.g., GPT-4o-mini mix) | ~$750 | Tune prompts & caching; consider local models for low stakes tasks |
| LLM inference fallback (local) | RTX 4090 equivalent | Electricity + depreciation | ~$120 | Optionally replace 30% of calls |
| Cloud storage (object + DB) | 200 GB | $0.023/GB | ~$5 | Assume AWS S3 or similar |
| Compute (ETL + services) | 2 vCPU 8 GB VM | $25 | Lightsail/Droplet baseline |
| Monitoring & logs | 30 GB logs | $0.50/GB | ~$15 | Use Loki or self-hosted ELK to reduce |
| Contingency | 10% buffer | — | ~$90 | Covers burst workload |
| **Total** | — | — | **≈ $1,000 / month** | Adjust based on actual run cadence |

> Action: Validate acceptable cost ceiling; if lower, tighten agent frequency, adopt open models, or schedule on-demand research.

## 7. Open Questions
1. Do we require Bahasa Indonesia prompts/output for agents? Impacts model choice and cost.
2. How critical is intraday latency (<5 min) vs end-of-day for AMT? Determines infrastructure complexity.
3. Preferred deployment target (local workstation vs cloud VM) for always-on services?
4. Are there compliance or audit logs requirements for LLM-generated recommendations?

## 8. Recommended Next Steps (Phase 0 Closure)
- Secure stakeholder sign-off on requirements, cost envelope, and data-source policy.
- Decide on default LLM provider mix (OpenAI vs alternatives) and permissible fallbacks.
- Schedule IDX site scraping POC and AlphaVantage coverage test (Phase 1 kickoff inputs).
- Prepare contribution guidelines for agent prompts/configs to align with existing documentation standards.

