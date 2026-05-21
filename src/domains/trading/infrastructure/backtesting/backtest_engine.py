"""
Backtesting engine for IDX swing trading signals using vectorbt.

Transaction costs (realistic for Indonesian retail brokerage):
  buy_fee:   0.15% (commission to broker)
  sell_fee:  0.25% (commission + 0.1% government levy)
  slippage:  0.20% per trade (market impact for liquid IDX stocks)

Note: vectorbt Portfolio.from_signals applies `fees` to each trade's value.
We use the average one-way cost (buy+sell)/2 so the round-trip cost is
approximately buy_fee + sell_fee as expected.
"""
from __future__ import annotations

import logging
from typing import Dict, Optional

import numpy as np
import pandas as pd
import vectorbt as vbt

logger = logging.getLogger(__name__)

# IDX realistic costs
_BUY_FEE = 0.0015
_SELL_FEE = 0.0025
_SLIPPAGE = 0.002


class BacktestEngine:
    """
    Runs vectorbt backtests with IDX-appropriate transaction costs.

    Parameters
    ----------
    buy_fee : float
        Buy-side commission fraction (default 0.0015 = 0.15%).
    sell_fee : float
        Sell-side commission fraction (default 0.0025 = 0.25%).
    slippage : float
        One-way slippage fraction (default 0.002 = 0.2%).
    init_cash : float
        Starting portfolio value in IDR (default 100_000_000 = 100M IDR).
    """

    def __init__(
        self,
        buy_fee: float = _BUY_FEE,
        sell_fee: float = _SELL_FEE,
        slippage: float = _SLIPPAGE,
        init_cash: float = 100_000_000.0,
    ) -> None:
        self.buy_fee = buy_fee
        self.sell_fee = sell_fee
        self.slippage = slippage
        self.init_cash = init_cash

    def run(
        self,
        prices: pd.DataFrame,
        signals: pd.DataFrame,
        meta_probs: Optional[pd.DataFrame] = None,
        min_meta_prob: float = 0.6,
    ) -> Dict:
        """
        Run a vectorised backtest.

        Parameters
        ----------
        prices : DataFrame
            Close prices indexed by date, one column per stock.
        signals : DataFrame
            Signal values: +1 = enter long, -1 = exit long, 0 = hold.
            Same index and columns as prices.
        meta_probs : DataFrame, optional
            MetaLabeler bet-size output (0–1 per bar per stock).
            If provided, entry signals where meta_prob < min_meta_prob are suppressed.
        min_meta_prob : float
            Minimum meta-probability to allow an entry (default 0.6).

        Returns
        -------
        dict with: total_return, sharpe_ratio, max_drawdown, win_rate,
                   profit_factor, n_trades, equity_curve (pd.Series)
        """
        entries = signals == 1.0
        exits = signals == -1.0

        # Apply meta-labeler filter to entries only
        if meta_probs is not None:
            entries = entries & (meta_probs >= min_meta_prob)

        n_entries = int(entries.values.sum())
        if n_entries == 0:
            return self._empty_result()

        # Average one-way fee — applied to both entry and exit by vectorbt
        avg_fee = (self.buy_fee + self.sell_fee) / 2

        try:
            portfolio = vbt.Portfolio.from_signals(
                close=prices,
                entries=entries,
                exits=exits,
                fees=avg_fee,
                slippage=self.slippage,
                init_cash=self.init_cash,
                freq="1D",
            )
        except Exception as exc:
            logger.error("vectorbt portfolio construction failed: %s", exc)
            return self._empty_result()

        return self._extract_metrics(portfolio)

    # ------------------------------------------------------------------ #
    # Internal
    # ------------------------------------------------------------------ #

    def _extract_metrics(self, portfolio) -> Dict:
        try:
            stats = portfolio.stats()
            equity = portfolio.value()
            if isinstance(equity, pd.DataFrame):
                equity = equity.sum(axis=1)

            total_return = float(stats.get("Total Return [%]", 0.0)) / 100
            sharpe = float(stats.get("Sharpe Ratio", float("nan")))
            # max_drawdown from stats is positive percentage; negate to be ≤ 0
            max_dd_pct = stats.get("Max Drawdown [%]", 0.0)
            max_dd = -abs(float(max_dd_pct)) / 100
            n_trades = int(stats.get("Total Trades", 0))
            win_rate_pct = stats.get("Win Rate [%]", float("nan"))
            win_rate = float(win_rate_pct) / 100 if not pd.isna(win_rate_pct) else float("nan")

            # Profit factor: gross profit / gross loss
            profit_factor = float("nan")
            try:
                trades = portfolio.trades.records_readable
                if len(trades) > 0:
                    pos_pnl = trades.loc[trades["PnL"] > 0, "PnL"].sum()
                    neg_pnl = abs(trades.loc[trades["PnL"] < 0, "PnL"].sum())
                    profit_factor = pos_pnl / neg_pnl if neg_pnl > 0 else float("inf")
            except Exception:
                pass

            return {
                "total_return": total_return,
                "sharpe_ratio": sharpe,
                "max_drawdown": max_dd,
                "win_rate": win_rate,
                "profit_factor": profit_factor,
                "n_trades": n_trades,
                "equity_curve": equity,
            }

        except Exception as exc:
            logger.error("Failed to extract backtest metrics: %s", exc)
            return self._empty_result()

    @staticmethod
    def _empty_result() -> Dict:
        return {
            "total_return": 0.0,
            "sharpe_ratio": float("nan"),
            "max_drawdown": 0.0,
            "win_rate": float("nan"),
            "profit_factor": float("nan"),
            "n_trades": 0,
            "equity_curve": pd.Series(dtype=float),
        }
