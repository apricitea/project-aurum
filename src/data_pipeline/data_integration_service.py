"""
Data Integration Service
Bridges the gap between daily price data pipeline and signal generation/analytics
Transforms raw daily prices into features ready for ML models and dashboard
"""

import pandas as pd
import numpy as np
from datetime import date, datetime, timedelta
from typing import List, Dict, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, or_
import logging

from ..api.database_extensions import (
    DailyStockPrice,
    StockFundamentals,
    MarketNewsArticle,
    AuctionMarketProfile,
    StockMaster,
    DataRefreshLog,
)
from ..api.database import MarketData

logger = logging.getLogger(__name__)


class DataIntegrationService:
    """
    Integrates data from multiple sources for signal generation and analytics
    Provides clean, feature-engineered data ready for ML models
    """

    def __init__(self, db_session: Session):
        self.session = db_session

    def get_latest_prices_dataframe(
        self,
        stock_codes: Optional[List[str]] = None,
        days: int = 252
    ) -> pd.DataFrame:
        """
        Get latest prices in DataFrame format ready for feature engineering

        Args:
            stock_codes: List of stock codes (None for all active stocks)
            days: Number of trading days to retrieve

        Returns:
            DataFrame with columns: date, stock_code, open, high, low, close, volume, etc.
        """
        try:
            # Get active stocks
            if stock_codes is None:
                stocks = self.session.query(StockMaster).filter(
                    StockMaster.is_active == True
                ).all()
                stock_codes = [s.stock_code for s in stocks]

            # Calculate date range
            end_date = date.today()
            start_date = end_date - timedelta(days=int(days * 1.5))  # Buffer for weekends

            # Query price data
            prices = self.session.query(DailyStockPrice).filter(
                and_(
                    DailyStockPrice.stock_code.in_(stock_codes),
                    DailyStockPrice.date >= start_date,
                    DailyStockPrice.date <= end_date,
                    DailyStockPrice.is_trading_day == True
                )
            ).order_by(
                DailyStockPrice.stock_code,
                DailyStockPrice.date
            ).all()

            # Convert to DataFrame
            data = []
            for price in prices:
                data.append({
                    'date': price.date,
                    'stock_code': price.stock_code,
                    'open': price.open_price,
                    'high': price.high_price,
                    'low': price.low_price,
                    'close': price.close_price,
                    'volume': price.volume,
                    'adjusted_close': price.adjusted_close or price.close_price,
                    'vwap': price.vwap,
                    'turnover_value': price.turnover_value,
                    'price_change': price.price_change,
                    'price_change_percent': price.price_change_percent
                })

            df = pd.DataFrame(data)

            # Ensure we have the right number of days per stock
            if not df.empty:
                df = df.groupby('stock_code').tail(days)

            logger.info(f"Retrieved {len(df)} price records for {len(stock_codes)} stocks")
            return df

        except Exception as e:
            logger.error(f"Failed to get latest prices: {str(e)}")
            return pd.DataFrame()

    def get_stock_metadata_dataframe(
        self,
        stock_codes: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """
        Get stock metadata (sector, industry, etc.) as DataFrame

        Returns:
            DataFrame with stock metadata
        """
        try:
            query = self.session.query(StockMaster)

            if stock_codes:
                query = query.filter(StockMaster.stock_code.in_(stock_codes))

            query = query.filter(StockMaster.is_active == True)

            stocks = query.all()

            data = []
            for stock in stocks:
                data.append({
                    'stock_code': stock.stock_code,
                    'company_name': stock.company_name,
                    'sector': stock.sector,
                    'industry': stock.industry,
                    'market_cap_category': stock.market_cap_category,
                    'is_lq45': stock.is_lq45,
                    'yahoo_symbol': stock.yahoo_symbol
                })

            return pd.DataFrame(data)

        except Exception as e:
            logger.error(f"Failed to get stock metadata: {str(e)}")
            return pd.DataFrame()

    def get_fundamental_dataframe(
        self,
        stock_codes: Optional[List[str]] = None,
        years: int = 5
    ) -> pd.DataFrame:
        """
        Retrieve structured fundamental metrics for specified stocks.
        """
        try:
            query = self.session.query(StockFundamentals)

            if stock_codes:
                query = query.filter(StockFundamentals.stock_code.in_(stock_codes))

            cutoff_date = date.today() - timedelta(days=365 * years)
            query = query.filter(StockFundamentals.report_date >= cutoff_date)

            records = query.order_by(
                StockFundamentals.stock_code,
                StockFundamentals.report_date.desc()
            ).all()

            data = []
            for record in records:
                data.append({
                    'stock_code': record.stock_code,
                    'report_date': record.report_date,
                    'report_type': record.report_type,
                    'market_cap': record.market_cap,
                    'pe_ratio': record.pe_ratio,
                    'pb_ratio': record.pb_ratio,
                    'ps_ratio': record.ps_ratio,
                    'dividend_yield': record.dividend_yield,
                    'revenue': record.revenue,
                    'net_income': record.net_income,
                    'ebitda': record.ebitda,
                    'gross_profit': record.gross_profit,
                    'operating_income': record.operating_income,
                    'gross_margin': record.gross_margin,
                    'operating_margin': record.operating_margin,
                    'profit_margin': record.profit_margin,
                    'total_assets': record.total_assets,
                    'total_liabilities': record.total_liabilities,
                    'total_equity': record.total_equity,
                    'cash_and_equivalents': record.cash_and_equivalents,
                    'total_debt': record.total_debt,
                    'current_ratio': record.current_ratio,
                    'debt_to_equity': record.debt_to_equity,
                    'return_on_equity': record.return_on_equity,
                    'return_on_assets': record.return_on_assets,
                    'earnings_per_share': record.earnings_per_share,
                    'book_value_per_share': record.book_value_per_share,
                    'data_source': record.data_source
                })

            return pd.DataFrame(data)

        except Exception as e:
            logger.error(f"Failed to get fundamental data: {str(e)}")
            return pd.DataFrame()

    def get_recent_news_dataframe(
        self,
        stock_codes: Optional[List[str]] = None,
        days: int = 14
    ) -> pd.DataFrame:
        """
        Retrieve recent news articles for downstream sentiment and LLM usage.
        """
        try:
            query = self.session.query(MarketNewsArticle)

            if stock_codes:
                filters = [
                    MarketNewsArticle.stock_codes.contains([code])
                    for code in stock_codes
                ]
                query = query.filter(or_(*filters))

            cutoff = datetime.utcnow() - timedelta(days=days)
            query = query.filter(MarketNewsArticle.published_at >= cutoff)

            articles = query.order_by(MarketNewsArticle.published_at.desc()).all()

            data = []
            for article in articles:
                data.append({
                    'stock_codes': article.stock_codes,
                    'title': article.title,
                    'summary': article.summary,
                    'content': article.content,
                    'source': article.source,
                    'source_url': article.source_url,
                    'published_at': article.published_at,
                    'sentiment_score': article.sentiment_score,
                    'sentiment_label': article.sentiment_label,
                    'language': article.language,
                    'topics': article.topics
                })

            return pd.DataFrame(data)

        except Exception as e:
            logger.error(f"Failed to get news data: {str(e)}")
            return pd.DataFrame()

    def get_amt_dataframe(
        self,
        stock_codes: Optional[List[str]] = None,
        days: int = 30
    ) -> pd.DataFrame:
        """Retrieve recently computed Auction Market Theory profiles."""
        try:
            query = self.session.query(AuctionMarketProfile)

            if stock_codes:
                query = query.filter(AuctionMarketProfile.stock_code.in_(stock_codes))

            cutoff = date.today() - timedelta(days=days)
            query = query.filter(AuctionMarketProfile.session_date >= cutoff)

            profiles = query.order_by(
                AuctionMarketProfile.stock_code,
                AuctionMarketProfile.session_date.desc()
            ).all()

            data = []
            for profile in profiles:
                data.append({
                    'stock_code': profile.stock_code,
                    'session_date': profile.session_date,
                    'point_of_control': profile.point_of_control,
                    'value_area_high': profile.value_area_high,
                    'value_area_low': profile.value_area_low,
                    'initial_balance_high': profile.initial_balance_high,
                    'initial_balance_low': profile.initial_balance_low,
                    'profile_type': profile.profile_type,
                    'total_volume': profile.total_volume,
                    'vwap': profile.vwap,
                    'session_range': profile.session_range,
                    'close_price': profile.close_price,
                    'open_price': profile.open_price,
                    'single_prints': profile.single_prints,
                    'metrics': profile.metrics
                })

            return pd.DataFrame(data)

        except Exception as e:
            logger.error(f"Failed to get AMT data: {str(e)}")
            return pd.DataFrame()

    def prepare_feature_data_for_ml(
        self,
        stock_codes: Optional[List[str]] = None,
        lookback_days: int = 252,
        include_fundamentals: bool = True,
        include_news: bool = False
    ) -> Dict[str, pd.DataFrame]:
        """
        Prepare complete dataset for ML feature engineering

        Returns:
            Dictionary with 'price_data', 'fundamental_data', 'metadata', and optional 'news_data'
        """
        try:
            price_data = self.get_latest_prices_dataframe(
                stock_codes=stock_codes,
                days=lookback_days
            )

            metadata = self.get_stock_metadata_dataframe(stock_codes=stock_codes)

            if not price_data.empty and not metadata.empty:
                price_data = price_data.merge(
                    metadata[['stock_code', 'sector', 'industry']],
                    on='stock_code',
                    how='left'
                )

            fundamental_data = self.get_fundamental_dataframe(stock_codes=stock_codes) \
                if include_fundamentals else pd.DataFrame()

            news_data = self.get_recent_news_dataframe(stock_codes=stock_codes) \
                if include_news else pd.DataFrame()

            amt_data = self.get_amt_dataframe(stock_codes=stock_codes)

            return {
                'price_data': price_data,
                'fundamental_data': fundamental_data,
                'metadata': metadata,
                'news_data': news_data,
                'amt_data': amt_data
            }

        except Exception as e:
            logger.error(f"Failed to prepare feature data: {str(e)}")
            return {
                'price_data': pd.DataFrame(),
                'fundamental_data': pd.DataFrame(),
                'metadata': pd.DataFrame(),
                'news_data': pd.DataFrame(),
                'amt_data': pd.DataFrame()
            }

    def get_latest_prices_for_stocks(
        self,
        stock_codes: List[str]
    ) -> Dict[str, float]:
        """
        Get latest closing prices for specified stocks

        Returns:
            Dictionary mapping stock_code to latest close price
        """
        try:
            latest_prices = {}

            for stock_code in stock_codes:
                price = self.session.query(DailyStockPrice).filter(
                    DailyStockPrice.stock_code == stock_code
                ).order_by(
                    DailyStockPrice.date.desc()
                ).first()

                if price:
                    latest_prices[stock_code] = price.close_price

            return latest_prices

        except Exception as e:
            logger.error(f"Failed to get latest prices: {str(e)}")
            return {}

    def get_market_snapshot(self) -> Dict:
        """
        Get current market snapshot for dashboard

        Returns:
            Dictionary with market statistics
        """
        try:
            today = date.today()

            # Get today's price data
            todays_prices = self.session.query(DailyStockPrice).filter(
                DailyStockPrice.date == today
            ).all()

            if not todays_prices:
                # If no data for today, get latest available date
                latest_date = self.session.query(
                    func.max(DailyStockPrice.date)
                ).scalar()

                if latest_date:
                    todays_prices = self.session.query(DailyStockPrice).filter(
                        DailyStockPrice.date == latest_date
                    ).all()
                    today = latest_date

            # Calculate market statistics
            total_stocks = len(todays_prices)
            gainers = len([p for p in todays_prices if p.price_change_percent > 0])
            losers = len([p for p in todays_prices if p.price_change_percent < 0])
            unchanged = total_stocks - gainers - losers

            total_volume = sum([p.volume for p in todays_prices if p.volume])
            total_value = sum([p.turnover_value for p in todays_prices if p.turnover_value])

            # Top gainers and losers
            sorted_by_change = sorted(
                todays_prices,
                key=lambda x: x.price_change_percent or 0,
                reverse=True
            )

            top_gainers = [
                {
                    'stock_code': p.stock_code,
                    'price': p.close_price,
                    'change': p.price_change,
                    'change_percent': p.price_change_percent
                }
                for p in sorted_by_change[:5]
            ]

            top_losers = [
                {
                    'stock_code': p.stock_code,
                    'price': p.close_price,
                    'change': p.price_change,
                    'change_percent': p.price_change_percent
                }
                for p in sorted_by_change[-5:]
            ]

            # Most active by volume
            sorted_by_volume = sorted(
                todays_prices,
                key=lambda x: x.volume or 0,
                reverse=True
            )

            most_active = [
                {
                    'stock_code': p.stock_code,
                    'price': p.close_price,
                    'volume': p.volume,
                    'turnover_value': p.turnover_value
                }
                for p in sorted_by_volume[:5]
            ]

            return {
                'date': today.isoformat(),
                'total_stocks': total_stocks,
                'advancers': gainers,
                'decliners': losers,
                'unchanged': unchanged,
                'total_volume': total_volume,
                'total_value': total_value,
                'top_gainers': top_gainers,
                'top_losers': top_losers,
                'most_active': most_active
            }

        except Exception as e:
            logger.error(f"Failed to get market snapshot: {str(e)}")
            return {}

    def get_stock_historical_performance(
        self,
        stock_code: str,
        days: int = 30
    ) -> Dict:
        """
        Get historical performance metrics for a stock

        Returns:
            Dictionary with performance statistics
        """
        try:
            end_date = date.today()
            start_date = end_date - timedelta(days=days)

            prices = self.session.query(DailyStockPrice).filter(
                and_(
                    DailyStockPrice.stock_code == stock_code,
                    DailyStockPrice.date >= start_date,
                    DailyStockPrice.date <= end_date
                )
            ).order_by(DailyStockPrice.date).all()

            if not prices:
                return {}

            # Calculate metrics
            closes = [p.close_price for p in prices]
            volumes = [p.volume for p in prices if p.volume]

            total_return = ((closes[-1] - closes[0]) / closes[0]) * 100
            volatility = np.std([p.price_change_percent for p in prices if p.price_change_percent])

            high_price = max([p.high_price for p in prices])
            low_price = min([p.low_price for p in prices])

            avg_volume = np.mean(volumes) if volumes else 0

            return {
                'stock_code': stock_code,
                'period_days': days,
                'start_price': closes[0],
                'end_price': closes[-1],
                'total_return': total_return,
                'high_price': high_price,
                'low_price': low_price,
                'volatility': volatility,
                'avg_volume': avg_volume
            }

        except Exception as e:
            logger.error(f"Failed to get historical performance: {str(e)}")
            return {}

    def get_sector_performance(self, days: int = 30) -> List[Dict]:
        """
        Get sector-wise performance

        Returns:
            List of sector performance dictionaries
        """
        try:
            end_date = date.today()
            start_date = end_date - timedelta(days=days)

            # Get stock metadata for sector mapping
            stocks = self.session.query(StockMaster).filter(
                StockMaster.is_active == True
            ).all()

            stock_sector_map = {s.stock_code: s.sector for s in stocks}

            # Get prices for period
            prices = self.session.query(DailyStockPrice).filter(
                and_(
                    DailyStockPrice.date >= start_date,
                    DailyStockPrice.date <= end_date
                )
            ).all()

            # Group by sector and calculate performance
            sector_data = {}

            for price in prices:
                sector = stock_sector_map.get(price.stock_code, 'Unknown')

                if sector not in sector_data:
                    sector_data[sector] = {
                        'prices': [],
                        'changes': []
                    }

                sector_data[sector]['prices'].append(price.close_price)
                if price.price_change_percent:
                    sector_data[sector]['changes'].append(price.price_change_percent)

            # Calculate sector metrics
            sector_performance = []

            for sector, data in sector_data.items():
                if data['changes']:
                    avg_change = np.mean(data['changes'])
                    volatility = np.std(data['changes'])

                    sector_performance.append({
                        'sector': sector,
                        'avg_change_percent': avg_change,
                        'volatility': volatility,
                        'stock_count': len(set([s for s, sec in stock_sector_map.items() if sec == sector]))
                    })

            # Sort by performance
            sector_performance.sort(key=lambda x: x['avg_change_percent'], reverse=True)

            return sector_performance

        except Exception as e:
            logger.error(f"Failed to get sector performance: {str(e)}")
            return []

    def get_data_quality_summary(self) -> Dict:
        """
        Get summary of data quality for recent refreshes

        Returns:
            Dictionary with quality metrics
        """
        try:
            # Get recent refresh logs
            recent_logs = self.session.query(DataRefreshLog).filter(
                DataRefreshLog.job_type == 'daily_prices'
            ).order_by(
                DataRefreshLog.started_at.desc()
            ).limit(10).all()

            if not recent_logs:
                return {'message': 'No recent data refreshes found'}

            successful = len([log for log in recent_logs if log.status == 'completed'])
            failed = len([log for log in recent_logs if log.status == 'failed'])

            quality_scores = [log.data_quality_score for log in recent_logs if log.data_quality_score]
            avg_quality = np.mean(quality_scores) if quality_scores else 0

            total_records = sum([log.records_processed for log in recent_logs if log.records_processed])

            latest_refresh = recent_logs[0] if recent_logs else None

            return {
                'total_recent_jobs': len(recent_logs),
                'successful_jobs': successful,
                'failed_jobs': failed,
                'avg_data_quality': avg_quality,
                'total_records_processed': total_records,
                'latest_refresh': {
                    'date': latest_refresh.target_date.isoformat() if latest_refresh and latest_refresh.target_date else None,
                    'status': latest_refresh.status if latest_refresh else None,
                    'records': latest_refresh.records_processed if latest_refresh else 0,
                    'quality_score': latest_refresh.data_quality_score if latest_refresh else 0
                } if latest_refresh else None
            }

        except Exception as e:
            logger.error(f"Failed to get data quality summary: {str(e)}")
            return {}
