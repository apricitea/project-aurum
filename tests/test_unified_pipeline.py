import logging
from unittest.mock import Mock, patch

from src.data_pipeline.unified_pipeline import UnifiedDataPipeline


def test_fundamentals_are_skipped_without_alpha_vantage_key(monkeypatch, caplog):
    monkeypatch.delenv("ALPHA_VANTAGE_API_KEY", raising=False)
    pipeline = Mock(spec=UnifiedDataPipeline)

    with patch("src.data_pipeline.unified_pipeline.FundamentalsIngestionService") as service:
        with caplog.at_level(logging.WARNING):
            UnifiedDataPipeline._maybe_run_fundamentals(
                pipeline,
                session=Mock(),
                stock_codes=["BBCA"],
                frequency="daily",
            )

    service.assert_not_called()
    assert "ALPHA_VANTAGE_API_KEY is not configured" in caplog.text
