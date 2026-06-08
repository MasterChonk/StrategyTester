"""Offline sanity tests -- no network required.

These guard the two things most likely to break silently:
  1. position sizing (the engine must actually place trades, even at high prices)
  2. data cleaning (yfinance's MultiIndex / odd-case columns must normalise)

Run with:  uv run pytest
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from crypto_trend import data
from crypto_trend.backtest import run_backtest
from crypto_trend.strategies import BuyAndHold, DonchianBreakout, SmaCross


def _synthetic_prices(n: int = 500, start_price: float = 50_000.0) -> pd.DataFrame:
    """A noisy but clearly UP-then-DOWN-then-UP series at BTC-like prices.

    The regime changes guarantee the trend strategies generate real entries and
    exits, while the high price level exercises the 'expensive coin' sizing path.
    """
    rng = np.random.default_rng(42)
    # Three regimes so moving averages cross and channels break both ways.
    legs = [
        np.linspace(0.0, 0.8, n // 3),    # up ~ +80%
        np.linspace(0.8, 0.2, n // 3),    # down
        np.linspace(0.2, 1.2, n - 2 * (n // 3)),  # up again
    ]
    drift = np.concatenate(legs)
    noise = rng.normal(0, 0.01, len(drift)).cumsum()
    close = start_price * np.exp(drift + noise)
    idx = pd.date_range("2020-01-01", periods=len(close), freq="D")
    return pd.DataFrame(
        {
            "Open": close,
            "High": close * 1.01,
            "Low": close * 0.99,
            "Close": close,
            "Volume": rng.integers(1, 100, len(close)),
        },
        index=idx,
    )


def test_strategies_place_trades_and_return_finite_metrics():
    prices = _synthetic_prices()
    for strategy in (SmaCross, DonchianBreakout, BuyAndHold):
        _, stats = run_backtest(prices, strategy)
        # The sizing fix must hold: trades actually happen at $50k+ prices.
        assert stats["# Trades"] > 0, f"{strategy.__name__} placed no trades"
        # Headline numbers must be real (not NaN/inf), or the table is garbage.
        for metric in ("Return [%]", "Max. Drawdown [%]", "Equity Final [$]"):
            assert np.isfinite(stats[metric]), f"{strategy.__name__}: {metric} not finite"


def test_buy_and_hold_tracks_the_underlying():
    """Buy & Hold's return should land close to the coin's actual price change."""
    prices = _synthetic_prices()
    _, stats = run_backtest(prices, BuyAndHold)
    price_change_pct = (prices["Close"].iloc[-1] / prices["Close"].iloc[0] - 1) * 100
    # Within a few % (fees + the ~1% cash buffer from SIZE=0.99).
    assert abs(stats["Return [%]"] - price_change_pct) < 5


def test_orders_fill_at_next_open_not_the_signal_bar():
    """No lookahead: a signal computed on a bar's close must fill at the NEXT
    bar's OPEN, never on the signal bar itself. We build a flat series that breaks
    out on one bar and check exactly where the resulting trade entered."""
    n = 40
    o = np.full(n, 100.0)
    h = np.full(n, 100.0)
    low = np.full(n, 100.0)
    c = np.full(n, 100.0)

    sig = 30                       # the breakout signal fires on this bar's close
    c[sig] = 110.0                 # close pops above the prior 20-day high (=100)
    h[sig] = 110.0
    o[sig + 1] = 105.0             # the fill must land HERE: next bar's open
    # Keep prices elevated afterwards so the position stays open (no exit).
    for arr in (o, c, h):
        arr[sig + 1:] = np.maximum(arr[sig + 1:], 105.0)
    low[sig + 1:] = 104.0

    idx = pd.date_range("2020-01-01", periods=n, freq="D")
    df = pd.DataFrame({"Open": o, "High": h, "Low": low, "Close": c, "Volume": 1}, index=idx)

    _, stats = run_backtest(df, DonchianBreakout)
    trades = stats["_trades"]
    assert len(trades) >= 1, "expected the breakout to open a trade"
    entry = trades.iloc[0]
    assert int(entry["EntryBar"]) == sig + 1          # the bar AFTER the signal
    assert entry["EntryPrice"] == pytest.approx(105.0)  # that bar's OPEN, not 110


def test_strategy_params_are_overridable_per_run():
    """run_backtest(..., params=...) must change behaviour without touching config.
    Faster moving averages cross more often, so they should trade more."""
    prices = _synthetic_prices()
    _, base = run_backtest(prices, SmaCross)                              # 20/100
    _, fast = run_backtest(prices, SmaCross, params={"fast": 5, "slow": 10})
    assert fast["# Trades"] != base["# Trades"]


def test_clean_flattens_multiindex_and_fixes_case():
    """data._clean must cope with yfinance's MultiIndex / mixed-case columns."""
    idx = pd.date_range("2021-01-01", periods=3, freq="D")
    raw = pd.DataFrame(
        {
            ("Open", "BTC-USD"): [1.0, 2.0, 3.0],
            ("High", "BTC-USD"): [1.0, 2.0, 3.0],
            ("Low", "BTC-USD"): [1.0, 2.0, 3.0],
            ("Close", "BTC-USD"): [1.0, 2.0, 3.0],
            ("Volume", "BTC-USD"): [10, 20, 30],
        },
        index=idx,
    )
    raw.columns = pd.MultiIndex.from_tuples(raw.columns)

    cleaned = data._clean(raw)
    assert list(cleaned.columns) == ["Open", "High", "Low", "Close", "Volume"]
    assert isinstance(cleaned.index, pd.DatetimeIndex)
    assert cleaned["Close"].dtype.kind == "f"  # numeric
    assert not cleaned[["Open", "High", "Low", "Close"]].isna().any().any()
