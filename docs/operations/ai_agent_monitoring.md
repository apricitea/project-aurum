# AI Agent Monitoring & Governance

## Observability Hooks
- Every research run is logged via `AgentRunRecorder` (`src/shared/monitoring/agent_runs.py`) to
  `logs/ai_research_runs.jsonl`, capturing conviction, runtime, and metadata.
- Structured logging (`ResearchOrchestrator`) emits completion telemetry for ingestion by ELK/Loki stacks.
- Unified pipeline logs AMT profile generation outcomes, aligning data freshness with research reports.

## Recommended Dashboards
- **Run Timeline**: visualize daily agent runs, conviction trends, and duration outliers.
- **Coverage**: track how many IDX tickers receive research per week and ensure one-off requests succeed.
- **Cost Control**: correlate agent run counts with LLM usage metrics (tokens/cost) from provider dashboards.
- **Quality Signals**: monitor conviction drift vs. realized performance (requires post-trade tagging).

## Governance Checklist
1. **Approval Workflow** – capture human acknowledgements before executing LLM-driven trades.
2. **Prompt Versioning** – store prompts and config snapshots alongside each run for auditability.
3. **PII & Compliance** – ensure news or filings scraped remain within IDX terms of use; redact sensitive data.
4. **Fallback Strategy** – define behavior when LLM provider unavailable (e.g., pause automation, notify ops).
5. **Model Evaluation** – schedule periodic replay datasets to benchmark agent recommendations vs. baseline.

## Next Actions
- Integrate run recorder with existing observability stack (Prometheus or OpenTelemetry exporters).
- Implement automated alerts when conviction exceeds configured thresholds or outputs fail validation rules.
- Expand governance doc with risk taxonomy for AMT-informed entries once production usage ramps.
