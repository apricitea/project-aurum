"""
main_pipeline.py — Entry point for the Project Aurum data pipeline.

Exposes the real UnifiedDataPipeline for both direct execution and notebook
imports. The actual implementation lives in src/data_pipeline/unified_pipeline.py.

Usage:
    # Run end-of-day pipeline (prices, intraday, fundamentals, news, feature store):
    python main_pipeline.py

    # Or import in notebooks:
    from main_pipeline import UnifiedDataPipeline, PipelineRunConfig
    pipeline = UnifiedDataPipeline()
    pipeline.run_end_of_day()
"""

from src.data_pipeline.unified_pipeline import UnifiedDataPipeline, PipelineRunConfig

# Legacy compat aliases for notebooks that imported DataCollector / TradingPipeline
DataCollector = UnifiedDataPipeline
TradingPipeline = UnifiedDataPipeline

__all__ = ["UnifiedDataPipeline", "PipelineRunConfig", "DataCollector", "TradingPipeline"]


if __name__ == "__main__":
    import logging
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stdout,
    )

    pipeline = UnifiedDataPipeline()
    pipeline.run_end_of_day()
