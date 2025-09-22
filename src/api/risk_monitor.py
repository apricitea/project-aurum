"""
Risk Monitor for Indonesian Quantitative Trading System
Real-time monitoring of portfolio risk, position limits, and market conditions
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta, time
import json
import numpy as np
import pandas as pd
from dataclasses import dataclass
from enum import Enum
import aioredis

from .database import DatabaseManager
from .config import settings

logger = logging.getLogger(__name__)


class RiskLevel(Enum):
    """Risk level enumeration"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RiskMetricType(Enum):
    """Risk metric types"""
    POSITION_CONCENTRATION = "position_concentration"
    SECTOR_CONCENTRATION = "sector_concentration"
    PORTFOLIO_VOLATILITY = "portfolio_volatility"
    VALUE_AT_RISK = "value_at_risk"
    MAXIMUM_DRAWDOWN = "maximum_drawdown"
    BETA_EXPOSURE = "beta_exposure"
    LIQUIDITY_RISK = "liquidity_risk"
    CORRELATION_RISK = "correlation_risk"
    CURRENCY_EXPOSURE = "currency_exposure"


@dataclass
class RiskLimit:
    """Risk limit definition"""
    metric_type: RiskMetricType
    limit_value: float
    warning_threshold: float
    critical_threshold: float
    enabled: bool = True
    description: str = ""


@dataclass
class RiskAlert:
    """Risk alert definition"""
    alert_id: str
    metric_type: RiskMetricType
    current_value: float
    limit_value: float
    risk_level: RiskLevel
    message: str
    stock_code: Optional[str] = None
    sector: Optional[str] = None
    timestamp: datetime = None


class PortfolioRiskCalculator:
    """Portfolio risk calculation engine"""

    def __init__(self):
        self.lookback_days = 252  # 1 year for risk calculations
        self.confidence_level = 0.95  # VaR confidence level

    def calculate_position_concentration(self, positions: List[Dict[str, Any]],
                                       total_portfolio_value: float) -> Dict[str, float]:
        """Calculate position concentration risk"""
        concentrations = {}

        for position in positions:
            stock_code = position['stock_code']
            market_value = position.get('market_value', 0)

            if total_portfolio_value > 0:
                concentration = market_value / total_portfolio_value
            else:
                concentration = 0

            concentrations[stock_code] = concentration

        return concentrations

    def calculate_sector_concentration(self, positions: List[Dict[str, Any]],
                                     total_portfolio_value: float) -> Dict[str, float]:
        """Calculate sector concentration risk"""
        sector_values = {}

        for position in positions:
            sector = position.get('sector', 'Unknown')
            market_value = position.get('market_value', 0)
            sector_values[sector] = sector_values.get(sector, 0) + market_value

        sector_concentrations = {}
        if total_portfolio_value > 0:
            for sector, value in sector_values.items():
                sector_concentrations[sector] = value / total_portfolio_value

        return sector_concentrations

    def calculate_portfolio_volatility(self, positions: List[Dict[str, Any]],
                                     price_history: pd.DataFrame) -> float:
        """Calculate portfolio volatility"""
        try:
            if price_history.empty or not positions:
                return 0.0

            # Calculate position weights
            total_value = sum(pos.get('market_value', 0) for pos in positions)
            weights = {}

            for position in positions:
                stock_code = position['stock_code']
                market_value = position.get('market_value', 0)
                weights[stock_code] = market_value / total_value if total_value > 0 else 0

            # Get returns for stocks in portfolio
            portfolio_stocks = list(weights.keys())
            available_stocks = [stock for stock in portfolio_stocks if stock in price_history.columns]

            if not available_stocks:
                return 0.0

            # Calculate returns
            returns = price_history[available_stocks].pct_change().dropna()

            if returns.empty:
                return 0.0

            # Calculate portfolio returns
            portfolio_weights = np.array([weights.get(stock, 0) for stock in available_stocks])
            portfolio_returns = (returns * portfolio_weights).sum(axis=1)

            # Annualized volatility
            volatility = portfolio_returns.std() * np.sqrt(252)
            return float(volatility)

        except Exception as e:
            logger.error(f"Error calculating portfolio volatility: {str(e)}")
            return 0.0

    def calculate_value_at_risk(self, positions: List[Dict[str, Any]],
                              price_history: pd.DataFrame,
                              confidence_level: float = 0.95) -> float:
        """Calculate portfolio Value at Risk (VaR)"""
        try:
            if price_history.empty or not positions:
                return 0.0

            # Calculate portfolio value
            total_value = sum(pos.get('market_value', 0) for pos in positions)

            if total_value <= 0:
                return 0.0

            # Calculate position weights
            weights = {}
            for position in positions:
                stock_code = position['stock_code']
                market_value = position.get('market_value', 0)
                weights[stock_code] = market_value / total_value

            # Get returns for stocks in portfolio
            portfolio_stocks = list(weights.keys())
            available_stocks = [stock for stock in portfolio_stocks if stock in price_history.columns]

            if not available_stocks:
                return 0.0

            # Calculate returns
            returns = price_history[available_stocks].pct_change().dropna()

            if returns.empty:
                return 0.0

            # Calculate portfolio returns
            portfolio_weights = np.array([weights.get(stock, 0) for stock in available_stocks])
            portfolio_returns = (returns * portfolio_weights).sum(axis=1)

            # Calculate VaR
            var_percentile = (1 - confidence_level) * 100
            var_return = np.percentile(portfolio_returns, var_percentile)
            var_amount = abs(var_return * total_value)

            return float(var_amount)

        except Exception as e:
            logger.error(f"Error calculating VaR: {str(e)}")
            return 0.0

    def calculate_maximum_drawdown(self, portfolio_history: pd.Series) -> float:
        """Calculate maximum drawdown"""
        try:
            if portfolio_history.empty:
                return 0.0

            # Calculate cumulative returns
            cumulative = (1 + portfolio_history).cumprod()

            # Calculate running maximum
            running_max = cumulative.expanding().max()

            # Calculate drawdown
            drawdown = (cumulative - running_max) / running_max

            # Return maximum drawdown (as positive number)
            max_drawdown = abs(drawdown.min())
            return float(max_drawdown)

        except Exception as e:
            logger.error(f"Error calculating maximum drawdown: {str(e)}")
            return 0.0

    def calculate_beta_exposure(self, positions: List[Dict[str, Any]],
                              stock_betas: Dict[str, float],
                              total_portfolio_value: float) -> float:
        """Calculate portfolio beta exposure"""
        try:
            if not positions or total_portfolio_value <= 0:
                return 1.0

            weighted_beta = 0.0

            for position in positions:
                stock_code = position['stock_code']
                market_value = position.get('market_value', 0)
                weight = market_value / total_portfolio_value

                # Use stock beta if available, default to 1.0
                beta = stock_betas.get(stock_code, 1.0)
                weighted_beta += weight * beta

            return float(weighted_beta)

        except Exception as e:
            logger.error(f"Error calculating beta exposure: {str(e)}")
            return 1.0


class RiskMonitor:
    """
    Real-time risk monitoring service for portfolio and market conditions
    """

    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.redis_client = None
        self.risk_calculator = PortfolioRiskCalculator()

        # Risk limits configuration
        self.risk_limits = self._initialize_risk_limits()

        # Monitoring state
        self.is_monitoring = False
        self.monitoring_task = None
        self.last_risk_check = None

        # Risk metrics cache
        self.current_risk_metrics = {}
        self.risk_alerts = []

    def _initialize_risk_limits(self) -> Dict[RiskMetricType, RiskLimit]:
        """Initialize default risk limits for Indonesian market"""
        return {
            RiskMetricType.POSITION_CONCENTRATION: RiskLimit(
                metric_type=RiskMetricType.POSITION_CONCENTRATION,
                limit_value=0.05,  # 5% max per position
                warning_threshold=0.04,  # 4% warning
                critical_threshold=0.06,  # 6% critical
                description="Maximum single position concentration"
            ),
            RiskMetricType.SECTOR_CONCENTRATION: RiskLimit(
                metric_type=RiskMetricType.SECTOR_CONCENTRATION,
                limit_value=0.25,  # 25% max per sector
                warning_threshold=0.20,  # 20% warning
                critical_threshold=0.30,  # 30% critical
                description="Maximum sector concentration"
            ),
            RiskMetricType.PORTFOLIO_VOLATILITY: RiskLimit(
                metric_type=RiskMetricType.PORTFOLIO_VOLATILITY,
                limit_value=0.20,  # 20% annual volatility limit
                warning_threshold=0.18,  # 18% warning
                critical_threshold=0.25,  # 25% critical
                description="Maximum portfolio volatility (annualized)"
            ),
            RiskMetricType.VALUE_AT_RISK: RiskLimit(
                metric_type=RiskMetricType.VALUE_AT_RISK,
                limit_value=0.02,  # 2% of portfolio value
                warning_threshold=0.015,  # 1.5% warning
                critical_threshold=0.025,  # 2.5% critical
                description="Maximum Value at Risk (95% confidence)"
            ),
            RiskMetricType.MAXIMUM_DRAWDOWN: RiskLimit(
                metric_type=RiskMetricType.MAXIMUM_DRAWDOWN,
                limit_value=0.15,  # 15% maximum drawdown
                warning_threshold=0.12,  # 12% warning
                critical_threshold=0.18,  # 18% critical
                description="Maximum portfolio drawdown"
            ),
            RiskMetricType.BETA_EXPOSURE: RiskLimit(
                metric_type=RiskMetricType.BETA_EXPOSURE,
                limit_value=1.5,  # Maximum beta exposure
                warning_threshold=1.3,  # Warning threshold
                critical_threshold=1.8,  # Critical threshold
                description="Maximum portfolio beta exposure"
            )
        }

    async def initialize(self):
        """Initialize risk monitor"""
        try:
            # Connect to Redis for caching
            self.redis_client = await aioredis.from_url(
                f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}",
                encoding="utf-8",
                decode_responses=True
            )

            logger.info("Risk monitor initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize risk monitor: {str(e)}")
            raise

    async def start_monitoring(self):
        """Start real-time risk monitoring"""
        if self.is_monitoring:
            logger.warning("Risk monitoring already running")
            return

        self.is_monitoring = True
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())
        logger.info("Risk monitoring started")

    async def stop_monitoring(self):
        """Stop risk monitoring"""
        self.is_monitoring = False

        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass

        logger.info("Risk monitoring stopped")

    async def _monitoring_loop(self):
        """Main monitoring loop"""
        while self.is_monitoring:
            try:
                # Perform risk checks every 5 minutes during market hours
                await self._perform_risk_checks()

                # Sleep for monitoring interval
                await asyncio.sleep(300)  # 5 minutes

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in risk monitoring loop: {str(e)}")
                await asyncio.sleep(60)  # Wait 1 minute before retrying

    async def _perform_risk_checks(self):
        """Perform comprehensive risk checks"""
        try:
            # Get current portfolio positions
            positions = await self.db_manager.get_portfolio_positions()

            if not positions:
                logger.debug("No positions to monitor")
                return

            # Calculate current portfolio value
            total_value = sum(pos.get('market_value', 0) for pos in positions)

            # Calculate risk metrics
            risk_metrics = await self._calculate_all_risk_metrics(positions, total_value)

            # Check for limit breaches
            alerts = await self._check_risk_limits(risk_metrics, positions)

            # Update cache
            await self._cache_risk_metrics(risk_metrics)

            # Process alerts
            if alerts:
                await self._process_risk_alerts(alerts)

            self.current_risk_metrics = risk_metrics
            self.last_risk_check = datetime.now()

            logger.debug(f"Risk check completed: {len(alerts)} alerts generated")

        except Exception as e:
            logger.error(f"Error performing risk checks: {str(e)}")

    async def _calculate_all_risk_metrics(self, positions: List[Dict[str, Any]],
                                        total_value: float) -> Dict[str, Any]:
        """Calculate all risk metrics"""
        risk_metrics = {
            'timestamp': datetime.now(),
            'total_portfolio_value': total_value,
            'position_count': len(positions)
        }

        # Position concentration
        position_concentrations = self.risk_calculator.calculate_position_concentration(
            positions, total_value
        )
        risk_metrics['position_concentrations'] = position_concentrations
        risk_metrics['max_position_concentration'] = max(position_concentrations.values()) if position_concentrations else 0

        # Sector concentration
        sector_concentrations = self.risk_calculator.calculate_sector_concentration(
            positions, total_value
        )
        risk_metrics['sector_concentrations'] = sector_concentrations
        risk_metrics['max_sector_concentration'] = max(sector_concentrations.values()) if sector_concentrations else 0

        # Get price history for volatility and VaR calculations
        stock_codes = [pos['stock_code'] for pos in positions]
        price_history = await self._get_price_history(stock_codes)

        # Portfolio volatility
        portfolio_volatility = self.risk_calculator.calculate_portfolio_volatility(
            positions, price_history
        )
        risk_metrics['portfolio_volatility'] = portfolio_volatility

        # Value at Risk
        value_at_risk = self.risk_calculator.calculate_value_at_risk(
            positions, price_history
        )
        risk_metrics['value_at_risk'] = value_at_risk
        risk_metrics['value_at_risk_percent'] = (value_at_risk / total_value) if total_value > 0 else 0

        # Portfolio returns for drawdown calculation
        portfolio_returns = await self._calculate_portfolio_returns(positions, price_history)
        maximum_drawdown = self.risk_calculator.calculate_maximum_drawdown(portfolio_returns)
        risk_metrics['maximum_drawdown'] = maximum_drawdown

        # Beta exposure (using default betas for now)
        stock_betas = {stock: 1.0 for stock in stock_codes}  # Default beta
        beta_exposure = self.risk_calculator.calculate_beta_exposure(
            positions, stock_betas, total_value
        )
        risk_metrics['beta_exposure'] = beta_exposure

        return risk_metrics

    async def _get_price_history(self, stock_codes: List[str],
                                days: int = 252) -> pd.DataFrame:
        """Get price history for stocks"""
        try:
            # This would typically query the market_data table
            # For now, return empty DataFrame
            return pd.DataFrame()

        except Exception as e:
            logger.error(f"Error getting price history: {str(e)}")
            return pd.DataFrame()

    async def _calculate_portfolio_returns(self, positions: List[Dict[str, Any]],
                                         price_history: pd.DataFrame) -> pd.Series:
        """Calculate portfolio returns time series"""
        try:
            # This would calculate historical portfolio returns
            # For now, return empty Series
            return pd.Series()

        except Exception as e:
            logger.error(f"Error calculating portfolio returns: {str(e)}")
            return pd.Series()

    async def _check_risk_limits(self, risk_metrics: Dict[str, Any],
                               positions: List[Dict[str, Any]]) -> List[RiskAlert]:
        """Check risk metrics against limits"""
        alerts = []

        # Check position concentration
        max_position_concentration = risk_metrics.get('max_position_concentration', 0)
        position_limit = self.risk_limits[RiskMetricType.POSITION_CONCENTRATION]

        if max_position_concentration > position_limit.critical_threshold:
            risk_level = RiskLevel.CRITICAL
        elif max_position_concentration > position_limit.warning_threshold:
            risk_level = RiskLevel.HIGH
        else:
            risk_level = None

        if risk_level:
            # Find the stock with highest concentration
            concentrations = risk_metrics.get('position_concentrations', {})
            max_stock = max(concentrations.items(), key=lambda x: x[1]) if concentrations else (None, 0)

            alerts.append(RiskAlert(
                alert_id=f"position_concentration_{datetime.now().timestamp()}",
                metric_type=RiskMetricType.POSITION_CONCENTRATION,
                current_value=max_position_concentration,
                limit_value=position_limit.limit_value,
                risk_level=risk_level,
                message=f"Position concentration limit exceeded: {max_stock[0]} at {max_position_concentration:.1%}",
                stock_code=max_stock[0],
                timestamp=datetime.now()
            ))

        # Check sector concentration
        max_sector_concentration = risk_metrics.get('max_sector_concentration', 0)
        sector_limit = self.risk_limits[RiskMetricType.SECTOR_CONCENTRATION]

        if max_sector_concentration > sector_limit.critical_threshold:
            risk_level = RiskLevel.CRITICAL
        elif max_sector_concentration > sector_limit.warning_threshold:
            risk_level = RiskLevel.HIGH
        else:
            risk_level = None

        if risk_level:
            # Find sector with highest concentration
            concentrations = risk_metrics.get('sector_concentrations', {})
            max_sector = max(concentrations.items(), key=lambda x: x[1]) if concentrations else (None, 0)

            alerts.append(RiskAlert(
                alert_id=f"sector_concentration_{datetime.now().timestamp()}",
                metric_type=RiskMetricType.SECTOR_CONCENTRATION,
                current_value=max_sector_concentration,
                limit_value=sector_limit.limit_value,
                risk_level=risk_level,
                message=f"Sector concentration limit exceeded: {max_sector[0]} at {max_sector_concentration:.1%}",
                sector=max_sector[0],
                timestamp=datetime.now()
            ))

        # Check portfolio volatility
        portfolio_volatility = risk_metrics.get('portfolio_volatility', 0)
        vol_limit = self.risk_limits[RiskMetricType.PORTFOLIO_VOLATILITY]

        if portfolio_volatility > vol_limit.critical_threshold:
            risk_level = RiskLevel.CRITICAL
        elif portfolio_volatility > vol_limit.warning_threshold:
            risk_level = RiskLevel.HIGH
        else:
            risk_level = None

        if risk_level:
            alerts.append(RiskAlert(
                alert_id=f"portfolio_volatility_{datetime.now().timestamp()}",
                metric_type=RiskMetricType.PORTFOLIO_VOLATILITY,
                current_value=portfolio_volatility,
                limit_value=vol_limit.limit_value,
                risk_level=risk_level,
                message=f"Portfolio volatility limit exceeded: {portfolio_volatility:.1%}",
                timestamp=datetime.now()
            ))

        # Check Value at Risk
        var_percent = risk_metrics.get('value_at_risk_percent', 0)
        var_limit = self.risk_limits[RiskMetricType.VALUE_AT_RISK]

        if var_percent > var_limit.critical_threshold:
            risk_level = RiskLevel.CRITICAL
        elif var_percent > var_limit.warning_threshold:
            risk_level = RiskLevel.HIGH
        else:
            risk_level = None

        if risk_level:
            alerts.append(RiskAlert(
                alert_id=f"value_at_risk_{datetime.now().timestamp()}",
                metric_type=RiskMetricType.VALUE_AT_RISK,
                current_value=var_percent,
                limit_value=var_limit.limit_value,
                risk_level=risk_level,
                message=f"Value at Risk limit exceeded: {var_percent:.1%} of portfolio",
                timestamp=datetime.now()
            ))

        return alerts

    async def _cache_risk_metrics(self, risk_metrics: Dict[str, Any]):
        """Cache risk metrics for quick access"""
        try:
            await self.redis_client.setex(
                "risk_metrics",
                300,  # 5 minutes TTL
                json.dumps(risk_metrics, default=str)
            )

        except Exception as e:
            logger.error(f"Error caching risk metrics: {str(e)}")

    async def _process_risk_alerts(self, alerts: List[RiskAlert]):
        """Process and save risk alerts"""
        try:
            for alert in alerts:
                # Save to database
                alert_data = {
                    'alert_type': alert.metric_type.value,
                    'severity': alert.risk_level.value,
                    'message': alert.message,
                    'stock_code': alert.stock_code,
                    'sector': alert.sector,
                    'threshold_value': alert.limit_value,
                    'current_value': alert.current_value,
                    'metadata': {
                        'alert_id': alert.alert_id,
                        'metric_type': alert.metric_type.value,
                        'risk_level': alert.risk_level.value
                    }
                }

                # This would save to risk_alerts table
                # await self.db_manager.save_risk_alert(alert_data)

                # Add to current alerts
                self.risk_alerts.append(alert)

            # Keep only recent alerts (last 24 hours)
            cutoff_time = datetime.now() - timedelta(hours=24)
            self.risk_alerts = [
                alert for alert in self.risk_alerts
                if alert.timestamp and alert.timestamp > cutoff_time
            ]

        except Exception as e:
            logger.error(f"Error processing risk alerts: {str(e)}")

    async def get_risk_overview(self) -> Dict[str, Any]:
        """Get current risk overview"""
        try:
            # Try cache first
            cached_metrics = await self.redis_client.get("risk_metrics")
            if cached_metrics:
                risk_metrics = json.loads(cached_metrics)
            else:
                risk_metrics = self.current_risk_metrics

            # Add alert counts
            active_alerts = [alert for alert in self.risk_alerts if alert.timestamp > datetime.now() - timedelta(hours=1)]

            alert_counts = {
                'total': len(active_alerts),
                'critical': len([a for a in active_alerts if a.risk_level == RiskLevel.CRITICAL]),
                'high': len([a for a in active_alerts if a.risk_level == RiskLevel.HIGH]),
                'medium': len([a for a in active_alerts if a.risk_level == RiskLevel.MEDIUM]),
                'low': len([a for a in active_alerts if a.risk_level == RiskLevel.LOW])
            }

            return {
                'risk_metrics': risk_metrics,
                'alert_counts': alert_counts,
                'monitoring_status': 'active' if self.is_monitoring else 'inactive',
                'last_check': self.last_risk_check.isoformat() if self.last_risk_check else None,
                'risk_limits': {
                    limit_type.value: {
                        'limit_value': limit.limit_value,
                        'warning_threshold': limit.warning_threshold,
                        'critical_threshold': limit.critical_threshold,
                        'description': limit.description
                    }
                    for limit_type, limit in self.risk_limits.items()
                }
            }

        except Exception as e:
            logger.error(f"Error getting risk overview: {str(e)}")
            return {'error': str(e)}

    async def get_risk_alerts(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """Get risk alerts"""
        try:
            alerts = self.risk_alerts

            if active_only:
                # Filter to recent alerts
                cutoff_time = datetime.now() - timedelta(hours=24)
                alerts = [
                    alert for alert in alerts
                    if alert.timestamp and alert.timestamp > cutoff_time
                ]

            return [
                {
                    'id': alert.alert_id,
                    'alert_type': alert.metric_type.value,
                    'severity': alert.risk_level.value,
                    'message': alert.message,
                    'stock_code': alert.stock_code,
                    'sector': alert.sector,
                    'current_value': alert.current_value,
                    'limit_value': alert.limit_value,
                    'timestamp': alert.timestamp.isoformat() if alert.timestamp else None
                }
                for alert in alerts
            ]

        except Exception as e:
            logger.error(f"Error getting risk alerts: {str(e)}")
            return []

    async def update_risk_limits(self, limits: Dict[str, Any]) -> bool:
        """Update risk limits"""
        try:
            for metric_type_str, limit_config in limits.items():
                try:
                    metric_type = RiskMetricType(metric_type_str)
                    if metric_type in self.risk_limits:
                        limit = self.risk_limits[metric_type]
                        limit.limit_value = limit_config.get('limit_value', limit.limit_value)
                        limit.warning_threshold = limit_config.get('warning_threshold', limit.warning_threshold)
                        limit.critical_threshold = limit_config.get('critical_threshold', limit.critical_threshold)
                        limit.enabled = limit_config.get('enabled', limit.enabled)

                except ValueError:
                    logger.warning(f"Unknown metric type: {metric_type_str}")

            logger.info("Risk limits updated successfully")
            return True

        except Exception as e:
            logger.error(f"Error updating risk limits: {str(e)}")
            return False

    async def force_risk_check(self) -> Dict[str, Any]:
        """Force immediate risk check"""
        try:
            await self._perform_risk_checks()

            return {
                'status': 'completed',
                'timestamp': datetime.now().isoformat(),
                'alerts_generated': len(self.risk_alerts),
                'risk_metrics': self.current_risk_metrics
            }

        except Exception as e:
            logger.error(f"Error in forced risk check: {str(e)}")
            return {'status': 'failed', 'error': str(e)}

    async def health_check(self) -> Dict[str, Any]:
        """Health check for risk monitor"""
        return {
            'service': 'risk_monitor',
            'status': 'healthy' if self.is_monitoring else 'inactive',
            'last_check': self.last_risk_check.isoformat() if self.last_risk_check else None,
            'active_alerts': len(self.risk_alerts),
            'redis_connected': self.redis_client is not None,
            'risk_limits_count': len(self.risk_limits)
        }