"""Offline sanity tests -- no network required.

These guard the two things most likely to break silently:
  1. position sizing (the engine must actually place trades, even at high prices)
  2. data cleaning (yfinance's MultiIndex / odd-case columns must normalise)

Run with:  uv run pytest
"""

from __future__ import annotations

import numpy as np
import pandas as pd

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
