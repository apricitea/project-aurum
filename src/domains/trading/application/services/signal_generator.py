"""
Daily Signal Generation System for Indonesian Quantitative Trading
Processes model outputs into actionable buy/sell/hold signals with risk management
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')


class RiskManager:
    """
    Risk management layer for position sizing and portfolio constraints
    Tailored for Indonesian market characteristics
    """

    def __init__(self, config: Dict = None):
        self.config = config or {
            'max_position_size': 0.05,  # 5% max per stock
            'max_sector_concentration': 0.25,  # 25% max per sector
            'min_liquidity_threshold': 1000000,  # Minimum daily volume in IDR
            'max_portfolio_beta': 1.5,
            'min_diversification': 15,  # Minimum number of positions
            'cash_reserve': 0.15,  # 15% cash buffer
            'max_correlation': 0.7,  # Maximum correlation between positions
            'drawdown_limit': 0.10,  # 10% maximum drawdown stop
        }

        self.current_positions = {}
        self.sector_exposures = {}
        self.correlation_matrix = None

    def calculate_position_size(self, signal_strength: float, volatility: float,
                              liquidity: float, current_price: float) -> float:
        """
        Calculate optimal position size based on signal strength and risk factors

        Args:
            signal_strength: Model confidence score (-1 to 1)
            volatility: 20-day volatility
            liquidity: Average daily volume
            current_price: Current stock price

        Returns:
            Position size as fraction of portfolio
        """
        # Base position size from signal strength
        base_size = abs(signal_strength) * self.config['max_position_size']

        # Volatility adjustment (Kelly criterion inspired)
        vol_adjustment = min(1.0, 0.02 / max(volatility, 0.01))

        # Liquidity adjustment for IDX market
        liquidity_score = min(1.0, liquidity / self.config['min_liquidity_threshold'])

        # Combined position size
        position_size = base_size * vol_adjustment * liquidity_score

        # Ensure minimum viable position
        min_position = 10000000 / current_price  # 10M IDR minimum
        position_size = max(position_size, min_position)

        return min(position_size, self.config['max_position_size'])

    def check_sector_limits(self, stock_code: str, sector: str,
                           proposed_size: float) -> Tuple[bool, float]:
        """
        Check if proposed position violates sector concentration limits

        Args:
            stock_code: Stock ticker
            sector: Sector classification
            proposed_size: Proposed position size

        Returns:
            Tuple of (is_allowed, adjusted_size)
        """
        current_sector_exposure = self.sector_exposures.get(sector, 0)
        new_exposure = current_sector_exposure + proposed_size

        if new_exposure > self.config['max_sector_concentration']:
            # Adjust size to respect sector limit
            adjusted_size = self.config['max_sector_concentration'] - current_sector_exposure
            return True if adjusted_size > 0 else False, max(0, adjusted_size)

        return True, proposed_size

    def check_correlation_limits(self, stock_code: str, proposed_size: float) -> bool:
        """
        Check if proposed position would create excessive correlation

        Args:
            stock_code: Stock ticker
            proposed_size: Proposed position size

        Returns:
            Boolean indicating if position is allowed
        """
        if self.correlation_matrix is None or len(self.current_positions) < 5:
            return True  # Not enough positions to check correlation

        # Check correlation with existing positions
        for existing_stock, existing_size in self.current_positions.items():
            if existing_stock in self.correlation_matrix.index and \
               stock_code in self.correlation_matrix.columns:

                correlation = self.correlation_matrix.loc[existing_stock, stock_code]
                if abs(correlation) > self.config['max_correlation']:
                    # Weight correlation concern by position sizes
                    risk_score = abs(correlation) * existing_size * proposed_size
                    if risk_score > 0.01:  # 1% risk threshold
                        return False

        return True

    def update_positions(self, stock_code: str, new_position: float, sector: str):
        """Update tracking of current positions and sector exposures"""
        old_position = self.current_positions.get(stock_code, 0)
        old_sector_exposure = self.sector_exposures.get(sector, 0)

        # Update position
        self.current_positions[stock_code] = new_position

        # Update sector exposure
        self.sector_exposures[sector] = old_sector_exposure - old_position + new_position

        # Clean up zero positions
        if new_position == 0:
            self.current_positions.pop(stock_code, None)
        if self.sector_exposures.get(sector, 0) <= 0:
            self.sector_exposures.pop(sector, None)


class SignalGenerator:
    """
    Converts model predictions into actionable trading signals
    Integrates risk management and market timing
    """

    def __init__(self, config: Dict = None):
        self.config = config or {
            'signal_thresholds': {
                'strong_buy': 0.7,
                'buy': 0.3,
                'hold': 0.1,
                'sell': -0.1,
                'strong_sell': -0.5
            },
            'confidence_threshold': 0.6,
            'min_volume_filter': 500000000,  # 500M IDR daily volume
            'max_spread_filter': 0.05,  # 5% bid-ask spread
            'market_timing_weight': 0.2,
            'fundamental_weight': 0.4,
            'technical_weight': 0.3,
            'sentiment_weight': 0.1
        }

        self.risk_manager = RiskManager()
        self.signal_history = []

    def generate_daily_signals(self, predictions: Dict[str, np.ndarray],
                             market_data: pd.DataFrame,
                             fundamental_data: pd.DataFrame = None) -> pd.DataFrame:
        """
        Generate daily buy/sell/hold signals with position sizing

        Args:
            predictions: Dictionary with model predictions
            market_data: Current market data (price, volume, etc.)
            fundamental_data: Fundamental data for risk assessment

        Returns:
            DataFrame with trading signals and position sizes
        """
        signals = []

        for i, row in market_data.iterrows():
            stock_code = row.get('stock_code', f'stock_{i}')
            sector = row.get('sector', 'UNKNOWN')

            # Extract predictions for this stock
            signal_data = self._extract_stock_predictions(predictions, i)

            # Calculate composite signal
            composite_score = self._calculate_composite_signal(signal_data)

            # Apply market filters
            if not self._passes_market_filters(row):
                signal_type = 'HOLD'
                position_size = 0
                confidence = 0
            else:
                # Determine signal type and confidence
                signal_type, confidence = self._classify_signal(composite_score)

                # Calculate position size with risk management
                position_size = self._calculate_position_size(
                    stock_code, sector, composite_score, confidence, row
                )

            # Create signal record
            signal_record = {
                'timestamp': datetime.now(),
                'stock_code': stock_code,
                'sector': sector,
                'signal_type': signal_type,
                'composite_score': composite_score,
                'confidence': confidence,
                'position_size': position_size,
                'current_price': row.get('close', 0),
                'volume': row.get('volume', 0),
                'technical_score': signal_data.get('technical', 0),
                'fundamental_score': signal_data.get('fundamental', 0),
                'sentiment_score': signal_data.get('sentiment', 0),
                'risk_adjusted': True if position_size != abs(composite_score) * 0.05 else False
            }

            signals.append(signal_record)

            # Update risk manager
            if signal_type in ['BUY', 'STRONG_BUY']:
                self.risk_manager.update_positions(stock_code, position_size, sector)

        signals_df = pd.DataFrame(signals)
        self.signal_history.append(signals_df)

        return signals_df

    def _extract_stock_predictions(self, predictions: Dict[str, np.ndarray],
                                 index: int) -> Dict[str, float]:
        """Extract predictions for a specific stock"""
        signal_data = {}

        # Technical signal (convert probabilities to score)
        if 'technical_prob' in predictions:
            tech_probs = predictions['technical_prob'][index]
            if len(tech_probs) >= 3:  # Assuming [Sell, Hold, Buy, Strong_Buy]
                signal_data['technical'] = tech_probs[-1] + 0.5 * tech_probs[-2] - \
                                         tech_probs[0] - 0.5 * tech_probs[1]
            else:
                signal_data['technical'] = 0

        # Fundamental score (already a continuous value)
        if 'fundamental_score' in predictions:
            signal_data['fundamental'] = predictions['fundamental_score'][index]
        else:
            signal_data['fundamental'] = 0

        # Sentiment signal (convert probabilities to score)
        if 'sentiment_prob' in predictions:
            sent_probs = predictions['sentiment_prob'][index]
            if len(sent_probs) >= 3:  # Assuming [Weak, Neutral, Strong]
                signal_data['sentiment'] = sent_probs[-1] - sent_probs[0]
            else:
                signal_data['sentiment'] = 0

        # Ensemble score
        if 'ensemble_score' in predictions:
            signal_data['ensemble'] = predictions['ensemble_score'][index]

        return signal_data

    def _calculate_composite_signal(self, signal_data: Dict[str, float]) -> float:
        """
        Calculate weighted composite signal from all models

        Args:
            signal_data: Dictionary with individual model signals

        Returns:
            Composite signal score (-1 to 1)
        """
        # Normalize individual signals to [-1, 1] range
        technical = np.clip(signal_data.get('technical', 0), -1, 1)
        fundamental = np.clip(signal_data.get('fundamental', 0) / 2, -1, 1)  # Scale down
        sentiment = np.clip(signal_data.get('sentiment', 0), -1, 1)

        # Weighted combination
        composite = (
            self.config['technical_weight'] * technical +
            self.config['fundamental_weight'] * fundamental +
            self.config['sentiment_weight'] * sentiment
        )

        # Use ensemble score if available (higher weight)
        if 'ensemble' in signal_data:
            ensemble_normalized = np.clip(signal_data['ensemble'] / 2, -1, 1)
            composite = 0.6 * ensemble_normalized + 0.4 * composite

        return np.clip(composite, -1, 1)

    def _passes_market_filters(self, stock_data: pd.Series) -> bool:
        """
        Check if stock passes basic market filters

        Args:
            stock_data: Stock market data

        Returns:
            Boolean indicating if stock passes filters
        """
        # Volume filter
        daily_volume_idr = stock_data.get('volume', 0) * stock_data.get('close', 0)
        if daily_volume_idr < self.config['min_volume_filter']:
            return False

        # Spread filter (if available)
        if 'bid' in stock_data and 'ask' in stock_data:
            spread = (stock_data['ask'] - stock_data['bid']) / stock_data['close']
            if spread > self.config['max_spread_filter']:
                return False

        # Price filter (avoid penny stocks)
        if stock_data.get('close', 0) < 50:  # Below 50 IDR
            return False

        return True

    def _classify_signal(self, composite_score: float) -> Tuple[str, float]:
        """
        Classify composite score into signal type

        Args:
            composite_score: Composite signal score

        Returns:
            Tuple of (signal_type, confidence)
        """
        thresholds = self.config['signal_thresholds']
        confidence = abs(composite_score)

        if composite_score >= thresholds['strong_buy']:
            return 'STRONG_BUY', confidence
        elif composite_score >= thresholds['buy']:
            return 'BUY', confidence
        elif composite_score >= thresholds['hold']:
            return 'HOLD', confidence
        elif composite_score >= thresholds['sell']:
            return 'HOLD', confidence  # Conservative: avoid sells unless very confident
        else:
            return 'SELL', confidence

    def _calculate_position_size(self, stock_code: str, sector: str,
                               composite_score: float, confidence: float,
                               stock_data: pd.Series) -> float:
        """
        Calculate position size with risk management

        Args:
            stock_code: Stock ticker
            sector: Stock sector
            composite_score: Signal strength
            confidence: Model confidence
            stock_data: Market data for the stock

        Returns:
            Position size as fraction of portfolio
        """
        if composite_score <= 0 or confidence < self.config['confidence_threshold']:
            return 0

        # Calculate volatility
        volatility = stock_data.get('volatility_20d', 0.02)

        # Calculate liquidity
        liquidity = stock_data.get('volume', 0) * stock_data.get('close', 1)

        # Base position size
        position_size = self.risk_manager.calculate_position_size(
            composite_score, volatility, liquidity, stock_data.get('close', 1)
        )

        # Check sector limits
        allowed, adjusted_size = self.risk_manager.check_sector_limits(
            stock_code, sector, position_size
        )

        if not allowed:
            return 0

        # Check correlation limits
        if not self.risk_manager.check_correlation_limits(stock_code, adjusted_size):
            return adjusted_size * 0.5  # Reduce size due to correlation concern

        return adjusted_size

    def generate_portfolio_summary(self, signals_df: pd.DataFrame) -> Dict:
        """
        Generate portfolio-level summary and risk metrics

        Args:
            signals_df: DataFrame with trading signals

        Returns:
            Dictionary with portfolio summary
        """
        # Active signals (excluding holds)
        active_signals = signals_df[signals_df['signal_type'].isin(['BUY', 'STRONG_BUY', 'SELL'])]

        # Portfolio statistics
        total_long_exposure = active_signals[
            active_signals['signal_type'].isin(['BUY', 'STRONG_BUY'])
        ]['position_size'].sum()

        sector_breakdown = active_signals.groupby('sector')['position_size'].sum().to_dict()

        # Risk metrics
        avg_confidence = active_signals['confidence'].mean()
        num_positions = len(active_signals)

        portfolio_summary = {
            'timestamp': datetime.now(),
            'total_signals': len(signals_df),
            'active_signals': len(active_signals),
            'buy_signals': len(active_signals[active_signals['signal_type'].isin(['BUY', 'STRONG_BUY'])]),
            'sell_signals': len(active_signals[active_signals['signal_type'] == 'SELL']),
            'total_long_exposure': total_long_exposure,
            'cash_available': 1.0 - total_long_exposure,
            'num_positions': num_positions,
            'avg_confidence': avg_confidence,
            'sector_breakdown': sector_breakdown,
            'diversification_score': min(1.0, num_positions / self.risk_manager.config['min_diversification']),
            'risk_budget_used': total_long_exposure / (1 - self.risk_manager.config['cash_reserve'])
        }

        return portfolio_summary

    def create_daily_report(self, signals_df: pd.DataFrame,
                          portfolio_summary: Dict) -> str:
        """
        Create formatted daily trading report

        Args:
            signals_df: Trading signals
            portfolio_summary: Portfolio summary

        Returns:
            Formatted report string
        """
        report = f"""
=== DAILY TRADING SIGNALS REPORT ===
Date: {datetime.now().strftime('%Y-%m-%d %H:%M WIB')}

PORTFOLIO OVERVIEW:
- Total Signals Generated: {portfolio_summary['total_signals']}
- Active Positions: {portfolio_summary['active_signals']}
- Buy Signals: {portfolio_summary['buy_signals']}
- Sell Signals: {portfolio_summary['sell_signals']}
- Portfolio Exposure: {portfolio_summary['total_long_exposure']:.1%}
- Cash Available: {portfolio_summary['cash_available']:.1%}
- Average Confidence: {portfolio_summary['avg_confidence']:.2f}

SECTOR ALLOCATION:
"""
        for sector, allocation in portfolio_summary['sector_breakdown'].items():
            report += f"- {sector}: {allocation:.1%}\n"

        report += f"""
RISK METRICS:
- Diversification Score: {portfolio_summary['diversification_score']:.2f}
- Risk Budget Used: {portfolio_summary['risk_budget_used']:.1%}

TOP SIGNALS:
"""
        # Top 10 signals by confidence
        top_signals = signals_df.nlargest(10, 'confidence')[
            ['stock_code', 'signal_type', 'confidence', 'position_size', 'current_price']
        ]

        for _, signal in top_signals.iterrows():
            report += f"- {signal['stock_code']}: {signal['signal_type']} "
            report += f"(Conf: {signal['confidence']:.2f}, Size: {signal['position_size']:.1%}, "
            report += f"Price: {signal['current_price']:.0f})\n"

        report += "\n=== END REPORT ===\n"

        return report


class AlertSystem:
    """
    Alert and notification system for trading signals
    """

    def __init__(self, config: Dict = None):
        self.config = config or {
            'alert_thresholds': {
                'high_confidence': 0.8,
                'large_position': 0.03,
                'sector_concentration': 0.20
            },
            'notification_channels': ['email', 'telegram'],
            'market_hours': {
                'start': '09:00',
                'end': '16:00',
                'timezone': 'Asia/Jakarta'
            }
        }

    def check_alerts(self, signals_df: pd.DataFrame,
                    portfolio_summary: Dict) -> List[Dict]:
        """
        Check for alert conditions and generate notifications

        Args:
            signals_df: Trading signals
            portfolio_summary: Portfolio summary

        Returns:
            List of alert dictionaries
        """
        alerts = []

        # High confidence signals
        high_conf_signals = signals_df[
            signals_df['confidence'] > self.config['alert_thresholds']['high_confidence']
        ]

        for _, signal in high_conf_signals.iterrows():
            alerts.append({
                'type': 'HIGH_CONFIDENCE_SIGNAL',
                'priority': 'HIGH',
                'message': f"High confidence {signal['signal_type']} signal for {signal['stock_code']} "
                          f"(confidence: {signal['confidence']:.2f})",
                'stock_code': signal['stock_code'],
                'signal_type': signal['signal_type']
            })

        # Large position alerts
        large_positions = signals_df[
            signals_df['position_size'] > self.config['alert_thresholds']['large_position']
        ]

        for _, signal in large_positions.iterrows():
            alerts.append({
                'type': 'LARGE_POSITION',
                'priority': 'MEDIUM',
                'message': f"Large position recommendation for {signal['stock_code']} "
                          f"({signal['position_size']:.1%} of portfolio)",
                'stock_code': signal['stock_code'],
                'position_size': signal['position_size']
            })

        # Sector concentration alerts
        for sector, allocation in portfolio_summary['sector_breakdown'].items():
            if allocation > self.config['alert_thresholds']['sector_concentration']:
                alerts.append({
                    'type': 'SECTOR_CONCENTRATION',
                    'priority': 'MEDIUM',
                    'message': f"High sector concentration in {sector} ({allocation:.1%})",
                    'sector': sector,
                    'allocation': allocation
                })

        # Risk budget alerts
        if portfolio_summary['risk_budget_used'] > 0.9:
            alerts.append({
                'type': 'RISK_BUDGET',
                'priority': 'HIGH',
                'message': f"Risk budget {portfolio_summary['risk_budget_used']:.1%} utilized",
                'risk_level': portfolio_summary['risk_budget_used']
            })

        return alerts

    def send_alerts(self, alerts: List[Dict]):
        """
        Send alerts through configured channels
        (Placeholder for actual implementation)
        """
        for alert in alerts:
            print(f"[{alert['priority']}] {alert['type']}: {alert['message']}")


if __name__ == "__main__":
    # Example usage
    import numpy as np

    # Generate sample predictions
    n_stocks = 50
    sample_predictions = {
        'technical_prob': np.random.dirichlet([1, 1, 2, 1], size=n_stocks),
        'fundamental_score': np.random.normal(0, 1, n_stocks),
        'sentiment_prob': np.random.dirichlet([1, 2, 1], size=n_stocks),
        'ensemble_score': np.random.normal(0, 0.5, n_stocks)
    }

    # Generate sample market data
    sample_market_data = pd.DataFrame({
        'stock_code': [f'STOCK{i:02d}.JK' for i in range(n_stocks)],
        'sector': np.random.choice(['BANKING', 'MINING', 'CONSUMER', 'TELECOM'], n_stocks),
        'close': np.random.uniform(1000, 50000, n_stocks),
        'volume': np.random.uniform(1000000, 100000000, n_stocks),
        'volatility_20d': np.random.uniform(0.15, 0.45, n_stocks)
    })

    # Initialize signal generator
    signal_gen = SignalGenerator()

    # Generate signals
    signals = signal_gen.generate_daily_signals(
        sample_predictions, sample_market_data
    )

    # Generate portfolio summary
    portfolio_summary = signal_gen.generate_portfolio_summary(signals)

    # Create daily report
    report = signal_gen.create_daily_report(signals, portfolio_summary)

    print(report)

    # Check alerts
    alert_system = AlertSystem()
    alerts = alert_system.check_alerts(signals, portfolio_summary)
    alert_system.send_alerts(alerts)