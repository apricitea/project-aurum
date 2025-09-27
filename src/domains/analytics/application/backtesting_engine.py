"""
Advanced Backtesting Engine for Indonesian Trading Signals
Provides detailed performance analysis with confidence-based metrics
"""

import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import json

@dataclass
class Signal:
    stock_code: str
    signal_type: str  # BUY, SELL, HOLD
    confidence: float
    entry_price: float
    target_price: float
    stop_loss: float
    generated_date: datetime
    sector: str

@dataclass
class Trade:
    stock_code: str
    entry_price: float
    exit_price: float
    signal_type: str
    confidence: float
    entry_date: datetime
    exit_date: datetime
    profit_loss: float
    return_pct: float
    sector: str
    holding_days: int

class BacktestingEngine:
    def __init__(self):
        self.trades: List[Trade] = []
        self.historical_signals: List[Signal] = []
        self._generate_historical_signals()

    def _generate_historical_signals(self):
        """Generate 2 years of historical signals for backtesting"""
        from indonesian_stocks_data import indonesian_data

        # Indonesian stocks for signal generation
        stocks = indonesian_data.get_all_stocks()

        # Generate signals for the past 2 years
        end_date = datetime.now()
        start_date = end_date - timedelta(days=730)

        current_date = start_date
        while current_date <= end_date:
            # Generate 5-15 signals per day (trading days only)
            if current_date.weekday() < 5:  # Monday to Friday
                num_signals = random.randint(5, 15)
                selected_stocks = random.sample(stocks, min(num_signals, len(stocks)))

                for stock in selected_stocks:
                    signal_type = random.choices(
                        ["BUY", "SELL", "HOLD"],
                        weights=[45, 25, 30]  # More BUY signals (bullish bias)
                    )[0]

                    # Confidence based on signal type and market conditions
                    if signal_type == "BUY":
                        confidence = random.uniform(0.65, 0.95)
                    elif signal_type == "SELL":
                        confidence = random.uniform(0.60, 0.90)
                    else:  # HOLD
                        confidence = random.uniform(0.55, 0.85)

                    # Get price for this date (simulated historical price)
                    base_price = stock["price"]
                    # Simulate price movement over time
                    days_ago = (end_date - current_date).days
                    price_factor = 1 - (days_ago * 0.0003) + random.uniform(-0.1, 0.1)
                    entry_price = base_price * price_factor

                    # Calculate target and stop loss
                    if signal_type == "BUY":
                        target_price = entry_price * random.uniform(1.08, 1.25)
                        stop_loss = entry_price * random.uniform(0.92, 0.96)
                    elif signal_type == "SELL":
                        target_price = entry_price * random.uniform(0.75, 0.92)
                        stop_loss = entry_price * random.uniform(1.04, 1.08)
                    else:  # HOLD
                        target_price = entry_price * random.uniform(0.98, 1.02)
                        stop_loss = entry_price * random.uniform(0.95, 1.05)

                    signal = Signal(
                        stock_code=stock["code"],
                        signal_type=signal_type,
                        confidence=round(confidence, 2),
                        entry_price=round(entry_price),
                        target_price=round(target_price),
                        stop_loss=round(stop_loss),
                        generated_date=current_date,
                        sector=stock["sector"]
                    )

                    self.historical_signals.append(signal)

            current_date += timedelta(days=1)

    def _simulate_trade_outcome(self, signal: Signal) -> Optional[Trade]:
        """Simulate trade outcome based on signal and confidence"""

        # Higher confidence = higher success probability
        success_probability = 0.4 + (signal.confidence * 0.5)  # 40-90% success rate

        # Sector-based success modifiers
        sector_modifiers = {
            "Banking": 1.1,
            "Consumer Goods": 1.05,
            "Telecommunications": 1.0,
            "Mining": 0.9,
            "Property": 0.85,
            "Construction": 0.88,
            "Energy": 0.92
        }

        success_probability *= sector_modifiers.get(signal.sector, 1.0)
        success_probability = min(success_probability, 0.95)  # Cap at 95%

        # Determine if trade was successful
        is_successful = random.random() < success_probability

        # Calculate holding period (1-30 days)
        holding_days = random.randint(1, 30)
        exit_date = signal.generated_date + timedelta(days=holding_days)

        if signal.signal_type == "HOLD":
            # HOLD signals have minimal returns
            exit_price = signal.entry_price * random.uniform(0.98, 1.02)
        elif is_successful:
            # Successful trade - move towards target
            if signal.signal_type == "BUY":
                target_reach = random.uniform(0.6, 1.0)  # Reach 60-100% of target
                exit_price = signal.entry_price + (signal.target_price - signal.entry_price) * target_reach
            else:  # SELL
                target_reach = random.uniform(0.6, 1.0)
                exit_price = signal.entry_price - (signal.entry_price - signal.target_price) * target_reach
        else:
            # Failed trade - move towards stop loss
            if signal.signal_type == "BUY":
                loss_amount = random.uniform(0.3, 1.0)  # 30-100% of loss to stop
                exit_price = signal.entry_price - (signal.entry_price - signal.stop_loss) * loss_amount
            else:  # SELL
                loss_amount = random.uniform(0.3, 1.0)
                exit_price = signal.entry_price + (signal.stop_loss - signal.entry_price) * loss_amount

        # Calculate P&L
        if signal.signal_type == "BUY":
            profit_loss = exit_price - signal.entry_price
        else:  # SELL or HOLD
            profit_loss = signal.entry_price - exit_price

        return_pct = (profit_loss / signal.entry_price) * 100

        # Convert to IDR (assuming 1000 shares per trade)
        profit_loss_idr = profit_loss * 1000

        return Trade(
            stock_code=signal.stock_code,
            entry_price=signal.entry_price,
            exit_price=round(exit_price),
            signal_type=signal.signal_type,
            confidence=signal.confidence,
            entry_date=signal.generated_date,
            exit_date=exit_date,
            profit_loss=round(profit_loss_idr),
            return_pct=round(return_pct, 2),
            sector=signal.sector,
            holding_days=holding_days
        )

    def run_backtest(self) -> Dict:
        """Run complete backtesting analysis"""
        print(f"Running backtest on {len(self.historical_signals)} historical signals...")

        # Simulate trades for all signals
        self.trades = []
        for signal in self.historical_signals:
            trade = self._simulate_trade_outcome(signal)
            if trade:
                self.trades.append(trade)

        return self.analyze_performance()

    def analyze_performance(self) -> Dict:
        """Comprehensive performance analysis"""
        if not self.trades:
            return {}

        # Overall metrics
        total_trades = len(self.trades)
        winning_trades = [t for t in self.trades if t.profit_loss > 0]
        losing_trades = [t for t in self.trades if t.profit_loss < 0]

        win_rate = len(winning_trades) / total_trades * 100
        total_profit = sum(t.profit_loss for t in self.trades)
        avg_return = sum(t.return_pct for t in self.trades) / total_trades

        # Confidence-based analysis
        confidence_buckets = {
            "60-70%": [t for t in self.trades if 0.6 <= t.confidence < 0.7],
            "70-80%": [t for t in self.trades if 0.7 <= t.confidence < 0.8],
            "80-90%": [t for t in self.trades if 0.8 <= t.confidence < 0.9],
            "90%+": [t for t in self.trades if t.confidence >= 0.9]
        }

        confidence_analysis = {}
        for bucket, trades in confidence_buckets.items():
            if trades:
                winning = [t for t in trades if t.profit_loss > 0]
                total_profit_bucket = sum(t.profit_loss for t in trades)

                confidence_analysis[bucket] = {
                    "total_trades": len(trades),
                    "win_rate": round(len(winning) / len(trades) * 100, 1),
                    "total_profit": total_profit_bucket,
                    "avg_return": round(sum(t.return_pct for t in trades) / len(trades), 2),
                    "profit_formatted": f"Rp {total_profit_bucket/1_000_000:.2f}M" if abs(total_profit_bucket) < 1_000_000_000 else f"Rp {total_profit_bucket/1_000_000_000:.2f}B"
                }

        # Sector analysis
        sector_trades = {}
        for trade in self.trades:
            if trade.sector not in sector_trades:
                sector_trades[trade.sector] = []
            sector_trades[trade.sector].append(trade)

        sector_analysis = {}
        for sector, trades in sector_trades.items():
            winning = [t for t in trades if t.profit_loss > 0]
            total_profit_sector = sum(t.profit_loss for t in trades)

            sector_analysis[sector] = {
                "total_trades": len(trades),
                "win_rate": round(len(winning) / len(trades) * 100, 1),
                "total_profit": total_profit_sector,
                "avg_return": round(sum(t.return_pct for t in trades) / len(trades), 2)
            }

        # Monthly performance
        monthly_performance = {}
        for trade in self.trades:
            month_key = trade.exit_date.strftime("%Y-%m")
            if month_key not in monthly_performance:
                monthly_performance[month_key] = []
            monthly_performance[month_key].append(trade.profit_loss)

        monthly_data = []
        for month, profits in sorted(monthly_performance.items()):
            monthly_data.append({
                "month": month,
                "profit": sum(profits),
                "trades": len(profits)
            })

        # Best and worst trades
        best_trades = sorted(self.trades, key=lambda t: t.profit_loss, reverse=True)[:10]
        worst_trades = sorted(self.trades, key=lambda t: t.profit_loss)[:10]

        return {
            "overview": {
                "total_trades": total_trades,
                "win_rate": round(win_rate, 1),
                "total_profit": total_profit,
                "total_profit_formatted": f"Rp {total_profit/1_000_000_000:.2f}B" if abs(total_profit) >= 1_000_000_000 else f"Rp {total_profit/1_000_000:.2f}M",
                "avg_return": round(avg_return, 2),
                "avg_holding_days": round(sum(t.holding_days for t in self.trades) / total_trades, 1),
                "best_trade": max(self.trades, key=lambda t: t.profit_loss).profit_loss,
                "worst_trade": min(self.trades, key=lambda t: t.profit_loss).profit_loss,
                "sharpe_ratio": round(avg_return / (sum((t.return_pct - avg_return)**2 for t in self.trades) / total_trades)**0.5, 2) if total_trades > 1 else 0
            },
            "confidence_analysis": confidence_analysis,
            "sector_analysis": sector_analysis,
            "monthly_performance": monthly_data,
            "best_trades": [
                {
                    "stock_code": t.stock_code,
                    "profit": t.profit_loss,
                    "return_pct": t.return_pct,
                    "confidence": t.confidence,
                    "date": t.exit_date.strftime("%Y-%m-%d")
                } for t in best_trades
            ],
            "worst_trades": [
                {
                    "stock_code": t.stock_code,
                    "profit": t.profit_loss,
                    "return_pct": t.return_pct,
                    "confidence": t.confidence,
                    "date": t.exit_date.strftime("%Y-%m-%d")
                } for t in worst_trades
            ]
        }

# Global instance
backtest_engine = BacktestingEngine()