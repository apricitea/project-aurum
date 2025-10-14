"""
Daily Price Data Scheduler
Automated scheduler for daily stock price data refresh
Runs daily at market close to fetch latest prices
"""

import schedule
import time
import logging
from datetime import datetime, time as dt_time
from typing import Optional
import pytz

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .daily_price_fetcher import DailyPriceFetcher
from ..api.config import settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DailyPriceScheduler:
    """
    Scheduler for automated daily price data refresh
    Runs at specified time each trading day
    """

    def __init__(
        self,
        db_url: Optional[str] = None,
        run_time: str = "17:30",  # Default: 5:30 PM Jakarta time (after market close)
        timezone: str = "Asia/Jakarta"
    ):
        """
        Initialize scheduler

        Args:
            db_url: Database connection URL. If None, uses settings
            run_time: Time to run daily refresh (HH:MM format, 24-hour)
            timezone: Timezone for scheduling
        """
        self.db_url = db_url or self._build_db_url()
        self.run_time = run_time
        self.timezone = pytz.timezone(timezone)

        # Create database engine and session factory
        self.engine = create_engine(self.db_url)
        self.SessionFactory = sessionmaker(bind=self.engine)

        self.is_running = False

    def _build_db_url(self) -> str:
        """Build database URL from settings"""
        # Try PostgreSQL first, fall back to SQLite
        try:
            return (
                f"postgresql://{settings.DB_USER}:{settings.DB_PASSWORD}"
                f"@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"
            )
        except:
            return "sqlite:///data/trading_system.db"

    def daily_refresh_job(self):
        """
        Main job function for daily price refresh
        Fetches latest prices for all active stocks
        """
        logger.info("="*80)
        logger.info("Starting daily price refresh job...")
        logger.info(f"Timestamp: {datetime.now(self.timezone)}")
        logger.info("="*80)

        try:
            # Create database session
            session = self.SessionFactory()

            # Create fetcher instance
            fetcher = DailyPriceFetcher(session)

            # Fetch today's prices for all active stocks
            # By default, fetches last 7 days to catch any missed days
            results, job_id = fetcher.fetch_daily_prices(
                stock_codes=None,  # All active stocks
                backfill_days=7
            )

            # Log summary
            successful = len([r for r in results if r.success])
            failed = len([r for r in results if not r.success])
            total_records = sum([r.records_fetched for r in results if r.success])

            logger.info("-"*80)
            logger.info(f"Daily refresh completed!")
            logger.info(f"Job ID: {job_id}")
            logger.info(f"Stocks processed: {len(results)}")
            logger.info(f"Successful: {successful}")
            logger.info(f"Failed: {failed}")
            logger.info(f"Total records: {total_records}")
            logger.info("="*80)

            # Log failed stocks
            if failed > 0:
                failed_stocks = [r.stock_code for r in results if not r.success]
                logger.warning(f"Failed stocks: {', '.join(failed_stocks)}")

            session.close()

            return True

        except Exception as e:
            logger.error(f"Daily refresh job failed: {str(e)}", exc_info=True)
            return False

    def manual_refresh(self, stock_codes: Optional[list] = None):
        """
        Manually trigger a data refresh

        Args:
            stock_codes: Optional list of stock codes to refresh. If None, refresh all
        """
        logger.info("Manual refresh triggered...")

        try:
            session = self.SessionFactory()
            fetcher = DailyPriceFetcher(session)

            results, job_id = fetcher.fetch_daily_prices(
                stock_codes=stock_codes,
                backfill_days=7
            )

            logger.info(f"Manual refresh completed. Job ID: {job_id}")

            session.close()
            return results, job_id

        except Exception as e:
            logger.error(f"Manual refresh failed: {str(e)}", exc_info=True)
            raise

    def backfill_historical(self, years: int = 2, stock_codes: Optional[list] = None):
        """
        Backfill historical data

        Args:
            years: Number of years to backfill
            stock_codes: Optional list of stock codes. If None, backfill all
        """
        logger.info(f"Starting historical backfill for {years} years...")

        try:
            session = self.SessionFactory()
            fetcher = DailyPriceFetcher(session)

            results, job_id = fetcher.backfill_historical_data(
                stock_codes=stock_codes,
                years=years
            )

            logger.info(f"Historical backfill completed. Job ID: {job_id}")

            session.close()
            return results, job_id

        except Exception as e:
            logger.error(f"Historical backfill failed: {str(e)}", exc_info=True)
            raise

    def start(self):
        """Start the scheduler"""
        logger.info("="*80)
        logger.info("Starting Daily Price Scheduler")
        logger.info(f"Scheduled run time: {self.run_time} {self.timezone}")
        logger.info("="*80)

        # Schedule the job
        schedule.every().day.at(self.run_time).do(self.daily_refresh_job)

        # Also run on weekdays only (Mon-Fri) - Indonesian market trading days
        # This is a backup in case the general schedule runs on weekends
        for day in ['monday', 'tuesday', 'wednesday', 'thursday', 'friday']:
            getattr(schedule.every(), day).at(self.run_time).do(self.daily_refresh_job)

        self.is_running = True

        logger.info("Scheduler started. Press Ctrl+C to stop.")
        logger.info(f"Next run: {schedule.next_run()}")
        logger.info("-"*80)

        try:
            while self.is_running:
                schedule.run_pending()
                time.sleep(60)  # Check every minute

        except KeyboardInterrupt:
            logger.info("\nScheduler stopped by user")
            self.stop()

    def stop(self):
        """Stop the scheduler"""
        self.is_running = False
        schedule.clear()
        logger.info("Scheduler stopped")

    def run_once(self):
        """Run the job once immediately (for testing)"""
        logger.info("Running job once (test mode)...")
        return self.daily_refresh_job()

    def get_schedule_info(self) -> dict:
        """Get information about scheduled jobs"""
        jobs = schedule.get_jobs()
        return {
            'is_running': self.is_running,
            'run_time': self.run_time,
            'timezone': str(self.timezone),
            'next_run': str(schedule.next_run()) if jobs else None,
            'scheduled_jobs': len(jobs)
        }


def main():
    """
    Main entry point for running the scheduler
    Can be run directly or as a service/daemon
    """
    import argparse

    parser = argparse.ArgumentParser(description='Daily Stock Price Data Scheduler')
    parser.add_argument(
        '--time',
        default='17:30',
        help='Time to run daily (HH:MM, 24-hour format). Default: 17:30'
    )
    parser.add_argument(
        '--timezone',
        default='Asia/Jakarta',
        help='Timezone for scheduling. Default: Asia/Jakarta'
    )
    parser.add_argument(
        '--run-once',
        action='store_true',
        help='Run the job once and exit (for testing)'
    )
    parser.add_argument(
        '--backfill',
        type=int,
        metavar='YEARS',
        help='Backfill historical data for specified years and exit'
    )
    parser.add_argument(
        '--stocks',
        nargs='+',
        help='Specific stock codes to process (space-separated)'
    )

    args = parser.parse_args()

    # Create scheduler
    scheduler = DailyPriceScheduler(
        run_time=args.time,
        timezone=args.timezone
    )

    if args.backfill:
        # Backfill mode
        logger.info(f"Running in backfill mode: {args.backfill} years")
        scheduler.backfill_historical(years=args.backfill, stock_codes=args.stocks)

    elif args.run_once:
        # Test mode - run once
        logger.info("Running in test mode: single execution")
        scheduler.run_once()

    else:
        # Normal mode - continuous scheduling
        scheduler.start()


if __name__ == "__main__":
    main()
