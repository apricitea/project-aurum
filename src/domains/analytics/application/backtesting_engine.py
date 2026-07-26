"""
Backtesting Engine for Indonesian Stock Exchange (IDX) trading signals.
Accepts real OHLCV price data and signal series from LightGBMSignalModel.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
import pandas as pd
import numpy as np


@dataclass
class BacktestResult:
    total_return_pct: float
    sharpe_ratio: float
    max_drawdown_pct: float
    win_rate_pct: float
    total_trades: int
    annualised_return_pct: float
    equity_curve: pd.Series
    monthly_returns: pd.Series
    trade_log: pd.DataFrame


class BacktestingEngine:
    """
    Vectorbt-based backtesting engine with pure-Python fallback.

    IDX transaction costs: buy 0.15%, sell 0.25%.
    """

    BUY_FEE = 0.0015
    SELL_FEE = 0.0025
    SLIPPAGE = 0.001

    def __init__(self, initial_capital: float = 100_000_000.0):
        """
        Args:
            initial_capital: Starting capital in IDR. Default 100 million IDR.
        """
        self.initial_capital = initial_capital

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(
        self,
        prices: pd.DataFrame,
        signals: pd.Series,
        confidence: Optional[pd.Series] = None,
        confidence_threshold: float = 0.6,
    ) -> BacktestResult:
        """
        Run a backtest.

        Args:
            prices: OHLCV DataFrame with DatetimeIndex. Must have a 'close' column
                    (case-insensitive). If not present, the first numeric column is used.
            signals: Float series indexed like prices. +1.0=BUY, -1.0=EXIT, 0.0=HOLD.
            confidence: Optional bet-size scores from MetaLabeler. Signals below
                        confidence_threshold are suppressed.
            confidence_threshold: Minimum confidence to act on a signal (default 0.6).

        Returns:
            BacktestResult dataclass.
        """
        close = self._extract_close(prices)
        signals = signals.reindex(close.index).fillna(0.0)

        if confidence is not None:
            confidence = confidence.reindex(close.index).fillna(0.0)
            mask = confidence < confidence_threshold
            signals = signals.copy()
            signals[mask] = 0.0

        try:
            import vectorbt as vbt  # noqa: F401
            return self._vectorbt_backtest(close, signals)
        except ImportError:
            return self._simple_backtest(close, signals)

    def to_api_dict(self, result: BacktestResult) -> Dict:
        """
        Serialise a BacktestResult to a JSON-safe dict for API responses.

        Returns dict with keys:
            overview, monthly_performance, best_trades, worst_trades
        """
        overview = {
            "total_return_pct": round(result.total_return_pct, 2),
            "sharpe_ratio": round(result.sharpe_ratio, 3),
            "max_drawdown_pct": round(result.max_drawdown_pct, 2),
            "win_rate_pct": round(result.win_rate_pct, 1),
            "total_trades": result.total_trades,
            "annualised_return_pct": round(result.annualised_return_pct, 2),
        }

        monthly_performance = [
            {"month": str(dt)[:7], "return_pct": round(float(v) * 100, 2)}
            for dt, v in result.monthly_returns.items()
        ]

        best_trades: List[Dict] = []
        worst_trades: List[Dict] = []
        if not result.trade_log.empty:
            log = result.trade_log
            best = log.nlargest(10, "return_pct") if "return_pct" in log.columns else log.head(10)
            worst = log.nsmallest(10, "return_pct") if "return_pct" in log.columns else log.tail(10)
            best_trades = best.to_dict(orient="records")
            worst_trades = worst.to_dict(orient="records")

        return {
            "overview": overview,
            "monthly_performance": monthly_performance,
            "best_trades": best_trades,
            "worst_trades": worst_trades,
        }

    # ------------------------------------------------------------------
    # Vectorbt path
    # ------------------------------------------------------------------

    def _vectorbt_backtest(self, close: pd.Series, signals: pd.Series) -> BacktestResult:
        import vectorbt as vbt

        entries = signals == 1.0
        exits = signals == -1.0

        pf = vbt.Portfolio.from_signals(
            close,
            entries=entries,
            exits=exits,
            init_cash=self.initial_capital,
            fees=self.BUY_FEE,
            slippage=self.SLIPPAGE,
            freq="D",
        )

        equity = pf.value()
        daily_returns = equity.pct_change().dropna()

        total_return_pct = float((equity.iloc[-1] / equity.iloc[0] - 1) * 100)
        sharpe = self._sharpe(daily_returns)
        max_dd = self._max_drawdown(equity)
        monthly_returns = equity.resample("ME").last().pct_change().dropna()

        trades_df = pf.trades.records_readable
        total_trades = len(trades_df)
        win_rate_pct = 0.0
        if total_trades > 0 and "PnL" in trades_df.columns:
            win_rate_pct = float((trades_df["PnL"] > 0).mean() * 100)
            trades_df = trades_df.rename(columns={"PnL": "pnl"})
            if "Return" in trades_df.columns:
                trades_df = trades_df.rename(columns={"Return": "return_pct"})
                trades_df["return_pct"] = trades_df["return_pct"] * 100

        n_years = len(close) / 252
        annualised = float(((1 + total_return_pct / 100) ** (1 / max(n_years, 1e-9)) - 1) * 100)

        return BacktestResult(
            total_return_pct=total_return_pct,
            sharpe_ratio=sharpe,
            max_drawdown_pct=max_dd,
            win_rate_pct=win_rate_pct,
            total_trades=total_trades,
            annualised_return_pct=annualised,
            equity_curve=equity,
            monthly_returns=monthly_returns,
            trade_log=trades_df if total_trades > 0 else pd.DataFrame(),
        )

    # ------------------------------------------------------------------
    # Pure-Python fallback
    # ------------------------------------------------------------------

    def _simple_backtest(self, close: pd.Series, signals: pd.Series) -> BacktestResult:
        """
        Iterate through signals day by day. Enter on +1.0, exit on -1.0.
        Tracks daily portfolio value = cash + shares * price.
        """
        cash = float(self.initial_capital)
        shares = 0.0
        entry_price = 0.0
        entry_date = None

        equity_values = []
        trade_records = []

        for date, price in close.items():
            sig = float(signals.get(date, 0.0))
            price = float(price)

            if sig == 1.0 and shares == 0.0 and cash > 0:
                # BUY: spend all cash, apply buy cost + slippage
                effective_price = price * (1 + self.SLIPPAGE)
                cost_per_share = effective_price * (1 + self.BUY_FEE)
                shares = cash / cost_per_share
                cash = 0.0
                entry_price = price
                entry_date = date

            elif sig == -1.0 and shares > 0.0:
                # EXIT: sell all shares, apply sell cost + slippage
                effective_price = price * (1 - self.SLIPPAGE)
                proceeds_per_share = effective_price * (1 - self.SELL_FEE)
                proceeds = shares * proceeds_per_share
                pnl = proceeds - shares * entry_price
                return_pct = pnl / (shares * entry_price) * 100 if entry_price > 0 else 0.0
                trade_records.append({
                    "entry_date": entry_date,
                    "exit_date": date,
                    "entry_price": round(entry_price, 2),
                    "exit_price": round(price, 2),
                    "pnl": round(pnl, 2),
                    "return_pct": round(return_pct, 2),
                })
                cash = proceeds
                shares = 0.0
                entry_price = 0.0
                entry_date = None

            portfolio_value = cash + shares * price
            equity_values.append(portfolio_value)

        equity = pd.Series(equity_values, index=close.index, name="equity")

        # Force-close any open position at last price
        if shares > 0.0:
            last_price = float(close.iloc[-1])
            proceeds = shares * last_price * (1 - self.SELL_FEE)
            pnl = proceeds - shares * entry_price
            return_pct = pnl / (shares * entry_price) * 100 if entry_price > 0 else 0.0
            trade_records.append({
                "entry_date": entry_date,
                "exit_date": close.index[-1],
                "entry_price": round(entry_price, 2),
                "exit_price": round(last_price, 2),
                "pnl": round(pnl, 2),
                "return_pct": round(return_pct, 2),
            })
            equity.iloc[-1] = proceeds

        if len(equity) == 0 or float(equity.iloc[0]) == 0:
            return self._empty_result()

        daily_returns = equity.pct_change().dropna()
        total_return_pct = float((equity.iloc[-1] / equity.iloc[0] - 1) * 100)
        sharpe = self._sharpe(daily_returns)
        max_dd = self._max_drawdown(equity)
        monthly_returns = equity.resample("ME").last().pct_change().dropna()

        trade_log = pd.DataFrame(trade_records)
        total_trades = len(trade_log)
        win_rate_pct = 0.0
        if total_trades > 0:
            win_rate_pct = float((trade_log["pnl"] > 0).mean() * 100)

        n_years = len(close) / 252
        annualised = float(((1 + total_return_pct / 100) ** (1 / max(n_years, 1e-9)) - 1) * 100)

        return BacktestResult(
            total_return_pct=total_return_pct,
            sharpe_ratio=sharpe,
            max_drawdown_pct=max_dd,
            win_rate_pct=win_rate_pct,
            total_trades=total_trades,
            annualised_return_pct=annualised,
            equity_curve=equity,
            monthly_returns=monthly_returns,
            trade_log=trade_log,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_close(prices: pd.DataFrame) -> pd.Series:
        if isinstance(prices, pd.Series):
            return prices
        for col in prices.columns:
            if col.lower() == "close":
                return prices[col]
        numeric_cols = prices.select_dtypes(include=[np.number]).columns
        if len(numeric_cols) > 0:
            return prices[numeric_cols[0]]
        raise ValueError("prices DataFrame has no numeric columns to use as close price")

    @staticmethod
    def _sharpe(daily_returns: pd.Series) -> float:
        if daily_returns.std() == 0 or len(daily_returns) < 2:
            return 0.0
        return float(daily_returns.mean() / daily_returns.std() * np.sqrt(252))

    @staticmethod
    def _max_drawdown(equity: pd.Series) -> float:
        dd = (equity - equity.cummax()) / equity.cummax() * 100
        return float(dd.min())

    def _empty_result(self) -> BacktestResult:
        idx = pd.DatetimeIndex([])
        return BacktestResult(
            total_return_pct=0.0,
            sharpe_ratio=0.0,
            max_drawdown_pct=0.0,
            win_rate_pct=0.0,
            total_trades=0,
            annualised_return_pct=0.0,
            equity_curve=pd.Series(dtype=float),
            monthly_returns=pd.Series(dtype=float),
            trade_log=pd.DataFrame(),
        )
