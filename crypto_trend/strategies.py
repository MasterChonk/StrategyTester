"""The trading strategies, written as backtesting.py `Strategy` classes.

A `Strategy` has two methods the engine calls for you:

    init() : runs once. Pre-compute indicators here with `self.I(func, ...)`.
    next() : runs once per day, walking forward through history one bar at a time.
             Inside next() you can ONLY see data up to "today" -- the engine makes
             lookahead bias (peeking at the future) impossible.

When you place an order in next(), backtesting.py fills it at the NEXT bar's open
price. That's realistic: you decide based on today's close, you trade tomorrow.

All three strategies below are "long-or-cash": they are either fully invested in
the coin or sitting in cash. No shorting, no leverage -- the simplest, most
realistic setup for someone buying spot crypto.

Every tunable lives on the class as a plain attribute (``fast``, ``slow``,
``entry``, ``exit``, ``size``), defaulting to the values in config.py. Because
backtesting.py copies any keyword you pass to ``Backtest.run(...)`` onto the
strategy, you can override them per run without editing config -- e.g.
``run_backtest(prices, SmaCross, params={"fast": 50, "slow": 200})``. That's what
makes parameter sweeps and walk-forward testing possible in a single process.
"""

from __future__ import annotations

import pandas as pd
from backtesting import Strategy
from backtesting.lib import crossover

from . import config


# --- Indicator helpers ------------------------------------------------------
# Each takes a price array and returns a pandas Series the same length as the
# data (with NaNs during the initial warm-up period, which the engine ignores).

def _sma(values, n: int) -> pd.Series:
    """Simple Moving Average: the rolling mean of the last `n` values."""
    return pd.Series(values).rolling(int(n)).mean()


def _rolling_high(values, n: int) -> pd.Series:
    """Highest value over the last `n` bars (the top of a Donchian channel)."""
    return pd.Series(values).rolling(int(n)).max()


def _rolling_low(values, n: int) -> pd.Series:
    """Lowest value over the last `n` bars (the bottom of a Donchian channel)."""
    return pd.Series(values).rolling(int(n)).min()


# --- Strategy 1: Moving-Average crossover -----------------------------------

class SmaCross(Strategy):
    """Buy when a fast moving average crosses ABOVE a slow one (uptrend forming);
    sell back to cash when it crosses below (uptrend breaking down)."""

    fast = config.SMA_FAST
    slow = config.SMA_SLOW
    size = config.SIZE

    def init(self):
        price = self.data.Close
        self.ma_fast = self.I(_sma, price, self.fast, name=f"SMA{self.fast}")
        self.ma_slow = self.I(_sma, price, self.slow, name=f"SMA{self.slow}")

    def next(self):
        # crossover(a, b) is True only on the bar where `a` rises above `b`.
        if crossover(self.ma_fast, self.ma_slow):
            if not self.position:           # only buy if we're currently in cash
                self.buy(size=self.size)
        elif crossover(self.ma_slow, self.ma_fast):
            self.position.close()           # exit to cash on the down-cross


# --- Strategy 2: Donchian-channel breakout ("Turtle" style) -----------------

class DonchianBreakout(Strategy):
    """Buy when price breaks ABOVE the highest high of the last `entry` days;
    exit to cash when it breaks BELOW the lowest low of the last `exit` days."""

    entry = config.DONCHIAN_ENTRY
    exit = config.DONCHIAN_EXIT
    size = config.SIZE

    def init(self):
        # Channels are built from High/Low. We compare today's price to the
        # channel value at the PREVIOUS bar (index -2) so that today's own bar
        # is excluded -- a genuine breakout past prior history, not a tautology.
        self.hh = self.I(_rolling_high, self.data.High, self.entry,
                         name=f"High{self.entry}")
        self.ll = self.I(_rolling_low, self.data.Low, self.exit,
                         name=f"Low{self.exit}")

    def next(self):
        price = self.data.Close[-1]
        if not self.position and price > self.hh[-2]:
            self.buy(size=self.size)
        elif self.position and price < self.ll[-2]:
            self.position.close()


# --- Benchmark: Buy & Hold --------------------------------------------------

class BuyAndHold(Strategy):
    """Buy on the very first day and hold forever. The yardstick every active
    strategy must beat to justify its trading (and its fees)."""

    size = config.SIZE

    def init(self):
        pass  # no indicators needed

    def next(self):
        if not self.position:
            self.buy(size=self.size)
