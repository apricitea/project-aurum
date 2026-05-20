"""
Signal Service for Indonesian Quantitative Trading System
Integrates with existing ML pipeline and manages signal generation, portfolio tracking
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta, time
import json
import uuid
import pandas as pd
import numpy as np
from pathlib import Path
import pickle
import aioredis

from src.domains.market_data.application.feature_engineering import IDXFeatureEngineer
from src.domains.trading.infrastructure.ml_models.model_ensemble import IDXQuantitativeModel
from src.domains.trading.application.services.signal_generator import SignalGenerator, AlertSystem
from src.data_pipeline.unified_pipeline import UnifiedDataPipeline as DataCollector, UnifiedDataPipeline as TradingPipeline

from .database import DatabaseManager
from .config import settings

logger = logging.getLogger(__name__)


class SignalService:
    """
    Signal service that manages ML model inference, signal generation, and portfolio tracking
    Integrates with the existing quantitative trading pipeline
    """

    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.redis_client = None

        # Initialize existing ML components
        self.data_collector = None
        self.feature_engineer = None
        self.ml_model = None
        self.signal_generator = None
        self.alert_system = None

        # Service state
        self.is_initialized = False
        self.model_loaded = False
        self.last_signal_generation = None
        self.current_positions = {}
        self.portfolio_metrics = {}

        # Generation tasks tracking
        self.active_tasks = {}

    async def initialize(self):
        """Initialize signal service with ML components"""
        try:
            # Connect to Redis for caching
            self.redis_client = await aioredis.from_url(
                f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}",
                encoding="utf-8",
                decode_responses=True
            )

            # Initialize ML pipeline components
            await self._initialize_ml_components()

            # Load latest model
            await self._load_model()

            # Initialize portfolio tracking
            await self._initialize_portfolio_tracking()

            self.is_initialized = True
            logger.info("Signal service initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize signal service: {str(e)}")
            raise

    async def _initialize_ml_components(self):
        """Initialize ML pipeline components"""
        try:
            # Initialize components from existing pipeline
            self.data_collector = DataCollector()
            self.feature_engineer = IDXFeatureEngineer()
            self.signal_generator = SignalGenerator()
            self.alert_system = AlertSystem()

            logger.info("ML components initialized")

        except Exception as e:
            logger.error(f"Failed to initialize ML components: {str(e)}")
            raise

    async def _load_model(self):
        """Load trained ML model"""
        try:
            model_path = settings.MODEL_PATH or "models/idx_quant_model.pkl"

            if Path(model_path).exists():
                # Load model asynchronously
                self.ml_model = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: IDXQuantitativeModel.load_models(model_path)
                )
                self.model_loaded = True
                logger.info(f"Model loaded from {model_path}")
            else:
                logger.warning(f"Model file not found: {model_path}")
                self.model_loaded = False

        except Exception as e:
            logger.error(f"Failed to load model: {str(e)}")
            self.model_loaded = False

    async def _initialize_portfolio_tracking(self):
        """Initialize portfolio tracking from database"""
        try:
            # Load current positions from database
            positions = await self.db_manager.get_portfolio_positions()

            self.current_positions = {
                pos['stock_code']: {
                    'quantity': pos['quantity'],
                    'average_price': pos['average_price'],
                    'current_price': pos.get('current_price', pos['average_price']),
                    'sector': pos.get('sector'),
                    'last_updated': pos['last_updated']
                }
                for pos in positions
            }

            # Calculate initial portfolio metrics
            await self._update_portfolio_metrics()

            logger.info(f"Portfolio tracking initialized with {len(self.current_positions)} positions")

        except Exception as e:
            logger.error(f"Failed to initialize portfolio tracking: {str(e)}")

    async def start_signal_generation(self, force: bool = False) -> str:
        """Start daily signal generation process"""
        try:
            # Check if already running
            if not force and await self._is_signal_generation_running():
                raise ValueError("Signal generation already in progress")

            # Create task ID
            task_id = str(uuid.uuid4())

            # Save task to database
            task_data = {
                'id': task_id,
                'status': 'started',
                'metadata': {
                    'force': force,
                    'market_date': datetime.now().date().isoformat()
                }
            }

            # Start generation in background
            asyncio.create_task(self._run_signal_generation(task_id))

            self.active_tasks[task_id] = task_data

            logger.info(f"Signal generation started with task ID: {task_id}")
            return task_id

        except Exception as e:
            logger.error(f"Failed to start signal generation: {str(e)}")
            raise

    async def _is_signal_generation_running(self) -> bool:
        """Check if signal generation is currently running"""
        # Check for active tasks
        for task_id, task_data in self.active_tasks.items():
            if task_data['status'] in ['started', 'running']:
                return True

        # Check Redis cache for running status
        running_status = await self.redis_client.get("signal_generation:running")
        return running_status == "true"

    async def _run_signal_generation(self, task_id: str):
        """Run the complete signal generation pipeline"""
        try:
            # Update task status
            self.active_tasks[task_id]['status'] = 'running'
            self.active_tasks[task_id]['started_at'] = datetime.now()

            # Set running flag in Redis
            await self.redis_client.setex("signal_generation:running", 3600, "true")

            # Step 1: Collect market data
            logger.info("Starting data collection...")
            await self._update_task_status(task_id, "collecting_data")

            raw_data = await asyncio.get_event_loop().run_in_executor(
                None,
                self.data_collector.collect_daily_data
            )

            # Step 2: Feature engineering
            logger.info("Starting feature engineering...")
            await self._update_task_status(task_id, "engineering_features")

            features = await self._engineer_features(raw_data)

            # Step 3: Model inference
            logger.info("Running model inference...")
            await self._update_task_status(task_id, "model_inference")

            if not self.model_loaded:
                raise ValueError("Model not loaded")

            predictions = await asyncio.get_event_loop().run_in_executor(
                None,
                self.ml_model.predict,
                features
            )

            # Step 4: Signal generation
            logger.info("Generating trading signals...")
            await self._update_task_status(task_id, "generating_signals")

            signals_df = await asyncio.get_event_loop().run_in_executor(
                None,
                self.signal_generator.generate_daily_signals,
                predictions,
                raw_data['price_data'],
                raw_data.get('fundamental_data')
            )

            # Step 5: Save signals to database
            logger.info("Saving signals to database...")
            await self._update_task_status(task_id, "saving_signals")

            signals_saved = await self._save_signals_to_database(signals_df)

            # Step 6: Update portfolio and risk metrics
            logger.info("Updating portfolio metrics...")
            await self._update_task_status(task_id, "updating_portfolio")

            portfolio_summary = await self._update_portfolio_from_signals(signals_df)

            # Step 7: Generate alerts for significant signals
            logger.info("Processing alerts...")
            await self._update_task_status(task_id, "processing_alerts")

            alerts_generated = await self._process_signal_alerts(signals_df, portfolio_summary)

            # Step 8: Cache results for quick access
            await self._cache_signal_results(signals_df, portfolio_summary)

            # Complete task
            self.active_tasks[task_id].update({
                'status': 'completed',
                'completed_at': datetime.now(),
                'signals_generated': len(signals_df),
                'alerts_generated': len(alerts_generated),
                'portfolio_summary': portfolio_summary
            })

            self.last_signal_generation = datetime.now()

            # Clear running flag
            await self.redis_client.delete("signal_generation:running")

            logger.info(f"Signal generation completed successfully: {len(signals_df)} signals generated")

        except Exception as e:
            # Handle error
            error_msg = str(e)
            logger.error(f"Signal generation failed: {error_msg}")

            self.active_tasks[task_id].update({
                'status': 'failed',
                'completed_at': datetime.now(),
                'error_message': error_msg
            })

            # Clear running flag
            await self.redis_client.delete("signal_generation:running")

    async def _update_task_status(self, task_id: str, status: str):
        """Update task status"""
        if task_id in self.active_tasks:
            self.active_tasks[task_id]['status'] = status
            self.active_tasks[task_id]['last_updated'] = datetime.now()

    async def _engineer_features(self, raw_data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """Engineer features from raw data"""
        price_data = raw_data['price_data']

        # Generate technical features
        features = await asyncio.get_event_loop().run_in_executor(
            None,
            self.feature_engineer.generate_technical_features,
            price_data
        )

        # Add fundamental features if available
        if not raw_data.get('fundamental_data', pd.DataFrame()).empty:
            fundamental_features = await asyncio.get_event_loop().run_in_executor(
                None,
                self.feature_engineer.generate_fundamental_features,
                raw_data['fundamental_data'],
                price_data
            )
            features = features.merge(
                fundamental_features, on=['stock_code', 'date'], how='left'
            )

        # Add sentiment features if available
        if not raw_data.get('news_data', pd.DataFrame()).empty:
            sentiment_features = await asyncio.get_event_loop().run_in_executor(
                None,
                self.feature_engineer.generate_sentiment_features,
                raw_data['news_data'],
                features
            )
            features = features.merge(
                sentiment_features, on=['stock_code', 'date'], how='left'
            )

        return features

    async def _save_signals_to_database(self, signals_df: pd.DataFrame) -> int:
        """Save trading signals to database"""
        signals_data = []

        for _, row in signals_df.iterrows():
            signal_data = {
                'date': datetime.now(),
                'stock_code': row['stock_code'],
                'sector': row.get('sector'),
                'signal_type': row['signal_type'],
                'composite_score': float(row['composite_score']),
                'confidence': float(row['confidence']),
                'position_size': float(row['position_size']),
                'current_price': float(row['current_price']),
                'volume': float(row.get('volume', 0)),
                'technical_score': float(row.get('technical_score', 0)),
                'fundamental_score': float(row.get('fundamental_score', 0)),
                'sentiment_score': float(row.get('sentiment_score', 0)),
                'risk_adjusted': bool(row.get('risk_adjusted', False)),
                'metadata': {
                    'generation_timestamp': datetime.now().isoformat(),
                    'model_version': getattr(self.ml_model, 'version', '1.0'),
                    'feature_count': len(signals_df.columns)
                }
            }
            signals_data.append(signal_data)

        # Save to database
        saved_signals = await self.db_manager.save_trading_signals(signals_data)
        return len(saved_signals)

    async def _update_portfolio_from_signals(self, signals_df: pd.DataFrame) -> Dict[str, Any]:
        """Update portfolio tracking from new signals"""
        # Generate portfolio summary using existing signal generator
        portfolio_summary = await asyncio.get_event_loop().run_in_executor(
            None,
            self.signal_generator.generate_portfolio_summary,
            signals_df
        )

        # Update internal portfolio metrics
        self.portfolio_metrics = portfolio_summary

        return portfolio_summary

    async def _process_signal_alerts(self, signals_df: pd.DataFrame,
                                   portfolio_summary: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Process alerts for significant signals"""
        # Use existing alert system to check for alerts
        alerts = await asyncio.get_event_loop().run_in_executor(
            None,
            self.alert_system.check_alerts,
            signals_df,
            portfolio_summary
        )

        # Convert alerts to our alert format and create in database
        created_alerts = []

        for alert in alerts:
            alert_data = {
                'alert_type': alert['type'],
                'message': alert['message'],
                'priority': alert['priority'].lower(),
                'stock_code': alert.get('stock_code'),
                'metadata': {
                    'source': 'signal_generation',
                    'original_alert': alert
                }
            }

            # Create alert in database (this would integrate with AlertEngine)
            # For now, just track them
            created_alerts.append(alert_data)

        return created_alerts

    async def _cache_signal_results(self, signals_df: pd.DataFrame,
                                  portfolio_summary: Dict[str, Any]):
        """Cache signal results for quick access"""
        try:
            # Cache latest signals
            signals_json = signals_df.to_json(orient='records', date_format='iso')
            await self.redis_client.setex(
                "latest_signals",
                3600,  # 1 hour TTL
                signals_json
            )

            # Cache portfolio summary
            await self.redis_client.setex(
                "portfolio_summary",
                1800,  # 30 minutes TTL
                json.dumps(portfolio_summary, default=str)
            )

            # Cache individual stock signals for quick lookup
            for _, row in signals_df.iterrows():
                stock_key = f"signal:{row['stock_code']}"
                signal_data = {
                    'signal_type': row['signal_type'],
                    'confidence': float(row['confidence']),
                    'position_size': float(row['position_size']),
                    'current_price': float(row['current_price']),
                    'generated_at': datetime.now().isoformat()
                }
                await self.redis_client.setex(
                    stock_key,
                    3600,
                    json.dumps(signal_data)
                )

            logger.info("Signal results cached successfully")

        except Exception as e:
            logger.error(f"Failed to cache signal results: {str(e)}")

    async def get_daily_signals(self, date: datetime.date) -> List[Dict[str, Any]]:
        """Get daily trading signals"""
        try:
            # First try cache for today's signals
            if date == datetime.now().date():
                cached_signals = await self.redis_client.get("latest_signals")
                if cached_signals:
                    signals_data = json.loads(cached_signals)
                    return signals_data

            # Fall back to database
            signals = await self.db_manager.get_daily_signals(datetime.combine(date, time.min))
            return signals

        except Exception as e:
            logger.error(f"Failed to get daily signals: {str(e)}")
            return []

    async def get_portfolio_summary(self) -> Dict[str, Any]:
        """Get current portfolio summary"""
        try:
            # Try cache first
            cached_summary = await self.redis_client.get("portfolio_summary")
            if cached_summary:
                return json.loads(cached_summary)

            # Calculate from current positions
            await self._update_portfolio_metrics()
            return self.portfolio_metrics

        except Exception as e:
            logger.error(f"Failed to get portfolio summary: {str(e)}")
            return {}

    async def get_current_positions(self) -> List[Dict[str, Any]]:
        """Get current portfolio positions"""
        try:
            positions = await self.db_manager.get_portfolio_positions()

            # Update with current prices if available
            stock_codes = [pos['stock_code'] for pos in positions]
            if stock_codes:
                latest_prices = await self.db_manager.get_latest_prices(stock_codes)

                for pos in positions:
                    stock_code = pos['stock_code']
                    if stock_code in latest_prices:
                        pos['current_price'] = latest_prices[stock_code]
                        pos['market_value'] = pos['quantity'] * latest_prices[stock_code]
                        pos['unrealized_pnl'] = pos['market_value'] - (pos['quantity'] * pos['average_price'])
                        pos['unrealized_pnl_percent'] = pos['unrealized_pnl'] / (pos['quantity'] * pos['average_price'])

            return positions

        except Exception as e:
            logger.error(f"Failed to get current positions: {str(e)}")
            return []

    async def update_position(self, stock_code: str, quantity: int, average_price: float,
                            user_id: str) -> Dict[str, Any]:
        """Update portfolio position"""
        try:
            position = await self.db_manager.update_position(
                stock_code=stock_code,
                quantity=quantity,
                average_price=average_price,
                user_id=user_id
            )

            # Update internal tracking
            if quantity > 0:
                self.current_positions[stock_code] = {
                    'quantity': quantity,
                    'average_price': average_price,
                    'last_updated': datetime.now()
                }
            else:
                self.current_positions.pop(stock_code, None)

            # Refresh portfolio metrics
            await self._update_portfolio_metrics()

            return position

        except Exception as e:
            logger.error(f"Failed to update position: {str(e)}")
            raise

    async def _update_portfolio_metrics(self):
        """Update portfolio metrics"""
        try:
            positions = await self.get_current_positions()

            total_value = sum(pos.get('market_value', 0) for pos in positions)
            total_cost = sum(pos['quantity'] * pos['average_price'] for pos in positions)
            total_pnl = sum(pos.get('unrealized_pnl', 0) for pos in positions)

            # Calculate sector breakdown
            sector_breakdown = {}
            for pos in positions:
                sector = pos.get('sector', 'Unknown')
                market_value = pos.get('market_value', 0)
                sector_breakdown[sector] = sector_breakdown.get(sector, 0) + market_value

            # Normalize sector breakdown to percentages
            if total_value > 0:
                sector_breakdown = {
                    sector: value / total_value
                    for sector, value in sector_breakdown.items()
                }

            self.portfolio_metrics = {
                'total_positions': len(positions),
                'total_market_value': total_value,
                'total_cost_basis': total_cost,
                'total_unrealized_pnl': total_pnl,
                'total_unrealized_pnl_percent': (total_pnl / total_cost) if total_cost > 0 else 0,
                'sector_breakdown': sector_breakdown,
                'last_updated': datetime.now()
            }

        except Exception as e:
            logger.error(f"Failed to update portfolio metrics: {str(e)}")

    async def get_generation_status(self, task_id: str) -> Dict[str, Any]:
        """Get signal generation task status"""
        if task_id in self.active_tasks:
            return self.active_tasks[task_id]
        else:
            return {'status': 'not_found', 'message': 'Task not found'}

    async def get_performance_analytics(self, days: int = 30) -> Dict[str, Any]:
        """Get performance analytics for the specified period"""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)

            # Get signals for the period
            signals = []
            current_date = start_date.date()
            while current_date <= end_date.date():
                daily_signals = await self.get_daily_signals(current_date)
                signals.extend(daily_signals)
                current_date += timedelta(days=1)

            if not signals:
                return {'error': 'No signals found for the specified period'}

            # Calculate analytics
            total_signals = len(signals)

            # Signal type distribution
            signal_types = {}
            confidence_scores = []
            position_sizes = []

            for signal in signals:
                signal_type = signal['signal_type']
                signal_types[signal_type] = signal_types.get(signal_type, 0) + 1
                confidence_scores.append(signal['confidence'])
                position_sizes.append(signal['position_size'])

            # Calculate averages
            avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0
            avg_position_size = sum(position_sizes) / len(position_sizes) if position_sizes else 0

            # Daily signal counts
            daily_counts = {}
            for signal in signals:
                date_key = signal['generated_at'][:10]  # Extract date part
                daily_counts[date_key] = daily_counts.get(date_key, 0) + 1

            avg_daily_signals = sum(daily_counts.values()) / len(daily_counts) if daily_counts else 0

            return {
                'period_days': days,
                'total_signals': total_signals,
                'signal_type_distribution': signal_types,
                'avg_confidence': avg_confidence,
                'avg_position_size': avg_position_size,
                'avg_daily_signals': avg_daily_signals,
                'daily_signal_counts': daily_counts,
                'analysis_date': datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Failed to get performance analytics: {str(e)}")
            return {'error': str(e)}

    async def generate_daily_report(self, date: datetime.date, format: str = "json") -> Dict[str, Any]:
        """Generate daily trading report"""
        try:
            # Get signals for the date
            signals = await self.get_daily_signals(date)

            if not signals:
                return {'error': 'No signals found for the specified date'}

            # Get portfolio summary
            portfolio_summary = await self.get_portfolio_summary()

            # Create report data
            report_data = {
                'date': date.isoformat(),
                'total_signals': len(signals),
                'signal_breakdown': {},
                'top_signals': [],
                'portfolio_summary': portfolio_summary,
                'generated_at': datetime.now().isoformat()
            }

            # Signal breakdown by type
            for signal in signals:
                signal_type = signal['signal_type']
                report_data['signal_breakdown'][signal_type] = \
                    report_data['signal_breakdown'].get(signal_type, 0) + 1

            # Top 10 signals by confidence
            sorted_signals = sorted(signals, key=lambda x: x['confidence'], reverse=True)
            report_data['top_signals'] = sorted_signals[:10]

            if format == "json":
                return report_data
            else:
                # For other formats, would implement file generation
                return {'message': f'Report generated in {format} format', 'data': report_data}

        except Exception as e:
            logger.error(f"Failed to generate daily report: {str(e)}")
            return {'error': str(e)}

    async def health_check(self) -> Dict[str, Any]:
        """Health check for signal service"""
        return {
            'service': 'signal_service',
            'status': 'healthy' if self.is_initialized else 'unhealthy',
            'model_loaded': self.model_loaded,
            'last_signal_generation': self.last_signal_generation.isoformat() if self.last_signal_generation else None,
            'active_positions': len(self.current_positions),
            'redis_connected': self.redis_client is not None
        }