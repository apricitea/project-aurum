"""
One-shot historical backfill for multi-asset data.

  Gold (GC=F): 2 years daily
  Forex (USDIDR=X): 2 years daily
  BTC 1m: 60 days (retention limit — no point going further)

Run once after deploying the new tables:
    uv run python scripts/backfill_multi_asset.py
"""
import sys
import logging
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.api.config import settings
from src.data_pipeline.multi_asset_fetcher import GoldFetcher, ForexFetcher, BinanceFetcher

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def main() -> int:
    db_url = (
        f"postgresql://{settings.DB_USER}:{settings.DB_PASSWORD}"
        f"@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"
    )
    engine = create_engine(db_url, pool_pre_ping=True)
    Session = sessionmaker(bind=engine)

    two_years_ago = datetime.utcnow() - timedelta(days=730)

    errors = 0

    # Gold — 2 years daily
    logger.info("Backfilling gold (2yr daily)...")
    with Session() as session:
        results, job_id = GoldFetcher(session).fetch(start_date=two_years_ago)
        session.commit()
    r = results[0]
    if r.success:
        logger.info("Gold OK: %s records (job=%s)", r.records_fetched, job_id)
    else:
        logger.error("Gold FAILED: %s", r.error_message)
        errors += 1

    # Forex USD/IDR — 2 years daily
    logger.info("Backfilling USDIDR=X (2yr daily)...")
    with Session() as session:
        results, job_id = ForexFetcher(session, symbol="USDIDR=X").fetch(start_date=two_years_ago)
        session.commit()
    r = results[0]
    if r.success:
        logger.info("Forex OK: %s records (job=%s)", r.records_fetched, job_id)
    else:
        logger.error("Forex FAILED: %s", r.error_message)
        errors += 1

    # BTC 1m — 7 days max (yfinance hard limit for 1m interval)
    # Daily pipeline will accumulate data up to the 60-day retention window
    logger.info("Backfilling BTC-USD 1m (7 days, yfinance)...")
    with Session() as session:
        results, job_id = BinanceFetcher(session).fetch(lookback_minutes=7 * 24 * 60)
        session.commit()
    r = results[0]
    if r.success:
        logger.info("BTC 1m OK: %s records (job=%s)", r.records_fetched, job_id)
    else:
        logger.error("BTC 1m FAILED: %s", r.error_message)
        errors += 1

    return errors


if __name__ == "__main__":
    sys.exit(main())
