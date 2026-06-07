"""All the knobs in one place.

This is the ONLY file you need to edit to experiment: change the coins, the date
range, the fees, or the strategy parameters and re-run `python main.py`.
"""

from __future__ import annotations

import pathlib

# ---------------------------------------------------------------------------
# Universe & time period
# ---------------------------------------------------------------------------
# yfinance tickers. Crypto pairs are quoted against USD, e.g. "BTC-USD".
# Add more (e.g. "SOL-USD", "BNB-USD") and they'll be included automatically.
COINS: list[str] = ["BTC-USD", "ETH-USD"]

# Backtest window. END = None means "up to today".
# (BTC history on Yahoo goes back to 2014; ETH only to late 2017, so 2017 is a
#  sensible common start that gives every coin a long, multi-cycle history.)
START: str = "2017-01-01"
END: str | None = None

# ---------------------------------------------------------------------------
# Backtest / trading settings
# ---------------------------------------------------------------------------
# CASH is a *nominal* starting balance. We use a deliberately large number.
# Why? backtesting.py buys whole units of an asset. If your cash is smaller than
# one unit's price (e.g. cash=$10k but 1 BTC = $100k) it can buy ZERO units and
# silently make no trades. A large balance means we can always buy a near-exact
# fraction of equity at any price. All the headline metrics (return %, Sharpe,
# drawdown) are ratios, so the absolute cash amount does not affect them.
CASH: float = 100_000_000.0

# Trading fee charged on every buy and every sell, as a fraction.
# 0.001 = 0.1%, a typical crypto-exchange taker fee.
COMMISSION: float = 0.001

# Fraction of available equity to put into each trade (0 < SIZE < 1).
# 0.99 = "go ~all-in" while leaving a 1% buffer to cover the commission.
SIZE: float = 0.99

# ---------------------------------------------------------------------------
# Strategy parameters (days, since we use daily candles)
# ---------------------------------------------------------------------------
# Moving-Average crossover: buy when the fast average crosses above the slow one.
SMA_FAST: int = 20
SMA_SLOW: int = 100

# Donchian breakout: buy on a new ENTRY-day high, sell on a new EXIT-day low.
DONCHIAN_ENTRY: int = 20
DONCHIAN_EXIT: int = 10

# ---------------------------------------------------------------------------
# Paths (don't usually need to touch these)
# ---------------------------------------------------------------------------
ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"        # cached price CSVs live here
RESULTS_DIR = ROOT / "results"  # comparison.csv + HTML charts land here
