"""Download and cache daily crypto price data from Yahoo Finance (via yfinance).

The rest of the project only ever calls `get_prices(ticker)`. It returns a clean
pandas DataFrame that backtesting.py can consume directly:

    - a DatetimeIndex (one row per day), sorted oldest -> newest
    - columns named exactly: Open, High, Low, Close, Volume  (capitalised!)
    - numeric dtypes, with any missing rows dropped

Data is cached to data/<ticker>.csv on first download so later runs are instant
and work offline.
"""

from __future__ import annotations

import pandas as pd
import yfinance as yf

from . import config

# backtesting.py REQUIRES these exact (capitalised) column names.
_OHLCV = ["Open", "High", "Low", "Close", "Volume"]


def _download(ticker: str, start: str, end: str | None) -> pd.DataFrame:
    """Fetch raw daily OHLCV from Yahoo Finance. Network call."""
    raw = yf.download(
        ticker,
        start=start,
        end=end,
        interval="1d",
        auto_adjust=True,   # adjusted prices (irrelevant for crypto, but tidy)
        progress=False,     # no progress bar in the console
    )
    if raw is None or raw.empty:
        raise ValueError(
            f"No data returned for '{ticker}'. Check the ticker spelling "
            f"(Yahoo uses e.g. 'BTC-USD') and your internet connection."
        )
    return raw


def _clean(df: pd.DataFrame) -> pd.DataFrame:
    """Normalise a raw frame into the strict shape backtesting.py expects.

    Handles a couple of yfinance quirks:
      * recent yfinance can return *MultiIndex* columns like ('Close','BTC-USD');
        we flatten those down to just the price type ('Close').
      * column case can vary; we Title-Case them so 'close' -> 'Close'.
    """
    df = df.copy()

    # Flatten MultiIndex columns -> keep the top level ('Open', 'High', ...).
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    # Normalise capitalisation, then keep only the OHLCV columns we need.
    df = df.rename(columns=str.title)
    df = df[[c for c in _OHLCV if c in df.columns]]

    # Ensure a clean, sorted DatetimeIndex and numeric values.
    df.index = pd.to_datetime(df.index)
    df = df.sort_index()
    df = df.apply(pd.to_numeric, errors="coerce")

    # A row is useless without OHLC; drop any such gaps.
    df = df.dropna(subset=["Open", "High", "Low", "Close"])
    return df


def get_prices(
    ticker: str,
    start: str | None = None,
    end: str | None = None,
    refresh: bool = False,
) -> pd.DataFrame:
    """Return clean daily OHLCV for `ticker`, using a local CSV cache.

    Pass refresh=True to force a fresh download (e.g. to pull the latest bars).
    """
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = config.DATA_DIR / f"{ticker}.csv"

    if path.exists() and not refresh:
        cached = pd.read_csv(path, index_col=0, parse_dates=True)
        return _clean(cached)

    fresh = _clean(_download(ticker, start or config.START, end or config.END))
    fresh.to_csv(path)  # cache the cleaned data for next time
    return fresh
