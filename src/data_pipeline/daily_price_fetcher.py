"""
Daily Stock Price Fetcher
Fetches daily OHLCV data from Yahoo Finance for Indonesian stocks
Implements best practices for data quality, error handling, and idempotency
"""

import yfinance as yf
import pandas as pd
import logging
from datetime import datetime, timedelta, date
from typing import List, Dict, Optional, Tuple
import time
from dataclasses import dataclass
import uuid

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from ..api.database_extensions import (
    StockMaster, DailyStockPrice, DataRefreshLog, DataQualityMetric
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class FetchResult:
    """Result of a data fetch operation"""
    stock_code: str
    success: bool
    records_fetched: int
    error_message: Optional[str] = None
    data_quality_score: Optional[float] = None


class DailyPriceFetcher:
    """
    Fetches daily stock prices from Yahoo Finance
    Implements data quality checks and error handling
    """

    def __init__(self, db_session: Session):
        self.db_session = db_session
        self.api_call_count = 0
        self.api_delay = 0.5  # Delay between API calls (seconds)

    def fetch_daily_prices(
        self,
        stock_codes: Optional[List[str]] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        backfill_days: int = 7
    ) -> Tuple[List[FetchResult], str]:
        """
        Fetch daily prices for specified stocks

        Args:
            stock_codes: List of stock codes to fetch. If None, fetch all active stocks
            start_date: Start date for historical data. If None, fetch last backfill_days
            end_date: End date for historical data. Defaults to today
            backfill_days: Number of days to backfill if start_date not specified

        Returns:
            Tuple of (list of FetchResult, job_id)
        """
        # Create job log entry
        job_id = str(uuid.uuid4())
        job_log = DataRefreshLog(
            id=uuid.UUID(job_id),
            job_name="daily_price_fetch",
            job_type="daily_prices",
            started_at=datetime.utcnow(),
            status="running",
            target_date=end_date or date.today(),
            stock_codes=stock_codes
        )
        self.db_session.add(job_log)
        self.db_session.commit()

        try:
            # Get list of stocks to fetch
            if stock_codes is None:
                stocks = self._get_active_stocks()
            else:
                stocks = self._get_stocks_by_codes(stock_codes)

            if not stocks:
                raise ValueError("No stocks found to fetch")

            # Set date range
            if end_date is None:
                end_date = date.today()
            if start_date is None:
                start_date = end_date - timedelta(days=backfill_days)

            logger.info(f"Fetching prices for {len(stocks)} stocks from {start_date} to {end_date}")

            # Fetch data for each stock
            results = []
            total_records = 0
            total_inserted = 0
            total_updated = 0
            total_failed = 0

            for stock in stocks:
                result = self._fetch_stock_data(
                    stock_code=stock.stock_code,
                    yahoo_symbol=stock.yahoo_symbol,
                    start_date=start_date,
                    end_date=end_date
                )
                results.append(result)

                if result.success:
                    total_records += result.records_fetched
                    total_inserted += result.records_fetched
                else:
                    total_failed += 1

                # Rate limiting
                time.sleep(self.api_delay)

            # Update job log
            job_log.completed_at = datetime.utcnow()
            job_log.duration_seconds = (job_log.completed_at - job_log.started_at).total_seconds()
            job_log.status = "completed" if total_failed == 0 else "partial"
            job_log.records_processed = total_records
            job_log.records_inserted = total_inserted
            job_log.records_updated = total_updated
            job_log.records_failed = total_failed
            job_log.api_calls_made = self.api_call_count

            # Calculate overall data quality score
            quality_scores = [r.data_quality_score for r in results if r.data_quality_score is not None]
            if quality_scores:
                job_log.data_quality_score = sum(quality_scores) / len(quality_scores)

            self.db_session.commit()

            logger.info(
                f"Job {job_id} completed: {total_inserted} inserted, "
                f"{total_updated} updated, {total_failed} failed"
            )

            return results, job_id

        except Exception as e:
            logger.error(f"Job {job_id} failed: {str(e)}")
            job_log.status = "failed"
            job_log.completed_at = datetime.utcnow()
            job_log.error_message = str(e)
            self.db_session.commit()
            raise

    def _get_active_stocks(self) -> List[StockMaster]:
        """Get all active stocks from stock_master table"""
        return self.db_session.query(StockMaster).filter(
            StockMaster.is_active == True
        ).all()

    def _get_stocks_by_codes(self, stock_codes: List[str]) -> List[StockMaster]:
        """Get stocks by stock codes"""
        return self.db_session.query(StockMaster).filter(
            and_(
                StockMaster.stock_code.in_(stock_codes),
                StockMaster.is_active == True
            )
        ).all()

    def _fetch_stock_data(
        self,
        stock_code: str,
        yahoo_symbol: str,
        start_date: date,
        end_date: date
    ) -> FetchResult:
        """
        Fetch data for a single stock from Yahoo Finance

        Args:
            stock_code: IDX stock code (e.g., BBCA)
            yahoo_symbol: Yahoo Finance symbol (e.g., BBCA.JK)
            start_date: Start date
            end_date: End date

        Returns:
            FetchResult
        """
        try:
            logger.info(f"Fetching {stock_code} ({yahoo_symbol})...")

            # Fetch data from Yahoo Finance
            ticker = yf.Ticker(yahoo_symbol)
            self.api_call_count += 1

            # Get historical data
            df = ticker.history(
                start=start_date,
                end=end_date + timedelta(days=1),  # yfinance end is exclusive
                interval="1d",
                auto_adjust=False,
                actions=True
            )

            if df.empty:
                logger.warning(f"No data returned for {stock_code}")
                return FetchResult(
                    stock_code=stock_code,
                    success=False,
                    records_fetched=0,
                    error_message="No data returned from API"
                )

            # Validate and clean data
            df = self._validate_and_clean_data(df, stock_code)

            # Calculate derived metrics
            df = self._calculate_derived_metrics(df)

            # Save to database (upsert)
            records_saved = self._save_price_data(stock_code, df)

            # Calculate data quality score
            quality_score = self._calculate_quality_score(df)

            # Update stock_master last_price_update
            self._update_stock_last_fetch(stock_code, quality_score)

            logger.info(f"✓ {stock_code}: {records_saved} records saved, quality: {quality_score:.1f}%")

            return FetchResult(
                stock_code=stock_code,
                success=True,
                records_fetched=records_saved,
                data_quality_score=quality_score
            )

        except Exception as e:
            logger.error(f"✗ {stock_code}: {str(e)}")
            return FetchResult(
                stock_code=stock_code,
                success=False,
                records_fetched=0,
                error_message=str(e)
            )

    def _validate_and_clean_data(self, df: pd.DataFrame, stock_code: str) -> pd.DataFrame:
        """
        Validate and clean price data
        - Remove rows with missing critical data
        - Check for price anomalies
        - Flag suspicious data
        """
        # Reset index to get date as column
        df = df.reset_index()
        df.rename(columns={'Date': 'date'}, inplace=True)

        # Remove rows with missing OHLC data
        required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
        df = df.dropna(subset=required_cols)

        # Data validation checks
        validation_errors = []

        # 1. Check for negative prices
        price_cols = ['Open', 'High', 'Low', 'Close']
        for col in price_cols:
            if (df[col] <= 0).any():
                validation_errors.append(f"Negative or zero prices in {col}")
                df = df[df[col] > 0]

        # 2. Check for illogical OHLC relationships
        invalid_ohlc = (
            (df['High'] < df['Low']) |
            (df['High'] < df['Open']) |
            (df['High'] < df['Close']) |
            (df['Low'] > df['Open']) |
            (df['Low'] > df['Close'])
        )
        if invalid_ohlc.any():
            validation_errors.append("Invalid OHLC relationships detected")
            df = df[~invalid_ohlc]

        # 3. Check for extreme price movements (>50% in one day - potential data error)
        if len(df) > 1:
            df['price_change_pct'] = df['Close'].pct_change() * 100
            extreme_moves = abs(df['price_change_pct']) > 50
            if extreme_moves.any():
                validation_errors.append(f"Extreme price movements detected: {extreme_moves.sum()} days")
                # Flag but don't remove - could be legitimate (stock splits, etc.)

        # 4. Check for zero volume
        if (df['Volume'] == 0).any():
            validation_errors.append(f"Zero volume on {(df['Volume'] == 0).sum()} days")

        if validation_errors:
            logger.warning(f"{stock_code} validation warnings: {', '.join(validation_errors)}")

        return df

    def _calculate_derived_metrics(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate derived metrics like VWAP, price changes, etc."""

        # VWAP (Volume-Weighted Average Price)
        df['vwap'] = ((df['High'] + df['Low'] + df['Close']) / 3 * df['Volume']).cumsum() / df['Volume'].cumsum()

        # Turnover value
        df['turnover_value'] = df['Close'] * df['Volume']

        # Price changes
        df['price_change'] = df['Close'] - df['Close'].shift(1)
        df['price_change_percent'] = df['Close'].pct_change() * 100

        # Fill NaN for first row
        df.loc[df.index[0], 'price_change'] = 0
        df.loc[df.index[0], 'price_change_percent'] = 0

        return df

    def _save_price_data(self, stock_code: str, df: pd.DataFrame) -> int:
        """
        Save price data to database with upsert logic
        Idempotent: can be run multiple times without creating duplicates
        """
        records_saved = 0

        for _, row in df.iterrows():
            try:
                # Check if record exists
                existing = self.db_session.query(DailyStockPrice).filter(
                    and_(
                        DailyStockPrice.stock_code == stock_code,
                        DailyStockPrice.date == row['date'].date()
                    )
                ).first()

                price_data = {
                    'stock_code': stock_code,
                    'date': row['date'].date(),
                    'open_price': float(row['Open']),
                    'high_price': float(row['High']),
                    'low_price': float(row['Low']),
                    'close_price': float(row['Close']),
                    'volume': float(row['Volume']),
                    'adjusted_close': float(row.get('Adj Close', row['Close'])),
                    'vwap': float(row.get('vwap', 0)) if pd.notna(row.get('vwap')) else None,
                    'turnover_value': float(row.get('turnover_value', 0)) if pd.notna(row.get('turnover_value')) else None,
                    'price_change': float(row.get('price_change', 0)) if pd.notna(row.get('price_change')) else None,
                    'price_change_percent': float(row.get('price_change_percent', 0)) if pd.notna(row.get('price_change_percent')) else None,
                    'is_trading_day': True,
                    'data_source': 'yfinance',
                    'data_quality': 'verified',
                }

                # Check for corporate actions (dividends, stock splits)
                has_dividend = row.get('Dividends', 0) > 0
                has_split = row.get('Stock Splits', 0) != 0
                if has_dividend or has_split:
                    price_data['is_corporate_action'] = True
                    price_data['meta_data'] = {
                        'dividend': float(row.get('Dividends', 0)),
                        'stock_split': float(row.get('Stock Splits', 0))
                    }

                if existing:
                    # Update existing record
                    for key, value in price_data.items():
                        setattr(existing, key, value)
                    existing.updated_at = datetime.utcnow()
                else:
                    # Insert new record
                    new_record = DailyStockPrice(**price_data)
                    self.db_session.add(new_record)

                records_saved += 1

            except Exception as e:
                logger.error(f"Error saving {stock_code} data for {row['date']}: {str(e)}")
                continue

        # Commit all records for this stock
        self.db_session.commit()

        return records_saved

    def _calculate_quality_score(self, df: pd.DataFrame) -> float:
        """
        Calculate data quality score (0-100)
        Based on completeness, consistency, and reasonableness
        """
        score = 100.0

        # Deduct for missing data
        completeness = df.notna().sum().sum() / (len(df) * len(df.columns))
        score *= completeness

        # Deduct for zero volume days
        zero_volume_pct = (df['Volume'] == 0).sum() / len(df)
        score *= (1 - zero_volume_pct * 0.5)  # 50% penalty for zero volume

        # Deduct for suspicious price patterns
        if len(df) > 1:
            # Check for too many consecutive identical prices
            consecutive_same = (df['Close'] == df['Close'].shift(1)).sum()
            if consecutive_same > len(df) * 0.3:  # More than 30% same prices
                score *= 0.8

        return max(0.0, min(100.0, score))

    def _update_stock_last_fetch(self, stock_code: str, quality_score: float):
        """Update stock_master with last fetch time and quality score"""
        stock = self.db_session.query(StockMaster).filter(
            StockMaster.stock_code == stock_code
        ).first()

        if stock:
            stock.last_price_update = datetime.utcnow()
            stock.data_quality_score = quality_score
            stock.updated_at = datetime.utcnow()
            self.db_session.commit()

    def backfill_historical_data(
        self,
        stock_codes: Optional[List[str]] = None,
        years: int = 2
    ) -> Tuple[List[FetchResult], str]:
        """
        Backfill historical data for multiple years
        Useful for initial data load or recovery

        Args:
            stock_codes: List of stock codes. If None, backfill all active stocks
            years: Number of years of historical data to fetch

        Returns:
            Tuple of (list of FetchResult, job_id)
        """
        end_date = date.today()
        start_date = end_date - timedelta(days=years * 365)

        logger.info(f"Backfilling {years} years of data from {start_date} to {end_date}")

        return self.fetch_daily_prices(
            stock_codes=stock_codes,
            start_date=start_date,
            end_date=end_date
        )

    def get_data_quality_report(self, days: int = 30) -> Dict:
        """
        Generate data quality report for recent data

        Args:
            days: Number of days to analyze

        Returns:
            Dictionary with quality metrics
        """
        start_date = date.today() - timedelta(days=days)

        # Query data quality metrics
        metrics = self.db_session.query(DataQualityMetric).filter(
            DataQualityMetric.metric_date >= start_date
        ).all()

        # Query recent job logs
        recent_jobs = self.db_session.query(DataRefreshLog).filter(
            and_(
                DataRefreshLog.started_at >= datetime.utcnow() - timedelta(days=days),
                DataRefreshLog.job_type == 'daily_prices'
            )
        ).order_by(DataRefreshLog.started_at.desc()).limit(10).all()

        return {
            'period_days': days,
            'total_jobs': len(recent_jobs),
            'successful_jobs': len([j for j in recent_jobs if j.status == 'completed']),
            'failed_jobs': len([j for j in recent_jobs if j.status == 'failed']),
            'avg_quality_score': sum([j.data_quality_score for j in recent_jobs if j.data_quality_score]) / len(recent_jobs) if recent_jobs else 0,
            'total_records_processed': sum([j.records_processed for j in recent_jobs if j.records_processed]),
            'recent_jobs': [
                {
                    'job_id': str(j.id),
                    'started_at': j.started_at.isoformat(),
                    'status': j.status,
                    'records_processed': j.records_processed,
                    'quality_score': j.data_quality_score
                }
                for j in recent_jobs
            ]
        }
