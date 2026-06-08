"""Run a single backtest and pull out the numbers we care about.

This is a thin wrapper around backtesting.py's `Backtest` object. It exists so
that main.py and the tests have one simple function to call.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from backtesting import Backtest

from . import config
from .strategies import BuyAndHold, DonchianBreakout, SmaCross

# The strategies we compare, in the order they'll appear in the table.
# (Buy & Hold last, as the benchmark the others are measured against.)
STRATEGIES: dict[str, type] = {
    "SMA Cross": SmaCross,
    "Donchian Breakout": DonchianBreakout,
    "Buy & Hold": BuyAndHold,
}

# The subset of backtesting.py's many stats we surface in the comparison table.
# (The exact strings must match backtesting.py's output index.)
METRICS: list[str] = [
    "Return [%]",              # total % growth of the portfolio
    "Buy & Hold Return [%]",   # what simply holding the coin returned (benchmark)
    "Return (Ann.) [%]",       # annualised return (CAGR)
    "Volatility (Ann.) [%]",   # annualised std-dev of returns (a risk measure)
    "Sharpe Ratio",            # return per unit of risk; higher is better
    "Max. Drawdown [%]",       # worst peak-to-trough drop; how much it hurt
    "Win Rate [%]",            # % of trades that were profitable
    "# Trades",                # how often it traded (fees scale with this)
    "Exposure Time [%]",       # % of the period actually invested (vs in cash)
]


def run_backtest(
    price_df: pd.DataFrame,
    strategy_cls: type,
    *,
    cash: float | None = None,
    commission: float | None = None,
    plot_path: str | Path | None = None,
    params: dict | None = None,
) -> tuple[Backtest, pd.Series]:
    """Backtest one strategy on one coin. Returns (Backtest, stats Series).

    Pass `params` to override strategy attributes for this run without editing
    config.py, e.g. ``params={"fast": 50, "slow": 200}``. backtesting.py copies
    each key onto the strategy, which is what enables parameter sweeps and
    walk-forward testing in a single process.

    If `plot_path` is given, an interactive HTML chart is written there.
    """
    bt = Backtest(
        price_df,
        strategy_cls,
        cash=config.CASH if cash is None else cash,
        commission=config.COMMISSION if commission is None else commission,
        finalize_trades=True,  # close any still-open trade at the end, for fair stats
    )
    stats = bt.run(**(params or {}))

    if plot_path is not None:
        # Plotting is a "nice to have" -- never let a chart failure kill the run.
        try:
            bt.plot(filename=str(plot_path), open_browser=False)
        except Exception as exc:  # pragma: no cover - depends on plotting backend
            print(f"    (could not render chart {Path(plot_path).name}: {exc})")

    return bt, stats


def stats_to_row(coin: str, strategy_name: str, stats: pd.Series) -> dict:
    """Flatten a stats Series into one tidy row for the comparison table."""
    row: dict[str, object] = {"Coin": coin, "Strategy": strategy_name}
    for metric in METRICS:
        row[metric] = float(stats[metric])
    return row
