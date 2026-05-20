"""
Runner script for the Aurum daily data pipeline.
Invoked by the nyx-aurum-data systemd service.

Exit codes:
  0 — pipeline completed successfully
  1 — pipeline failed (systemd will log the error)
"""
import logging
import sys
from pathlib import Path

# Ensure project root is on sys.path when run directly
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

# Load project .env — keeps credentials out of the service unit
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from src.data_pipeline.unified_pipeline import UnifiedDataPipeline, PipelineRunConfig

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("aurum-data-pipeline")


def main() -> int:
    logger.info("Aurum data pipeline starting")
    try:
        pipeline = UnifiedDataPipeline()
        pipeline.run_end_of_day(PipelineRunConfig())
        logger.info("Aurum data pipeline completed successfully")
        return 0
    except Exception as exc:
        logger.error("Aurum data pipeline FAILED: %s", exc, exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
