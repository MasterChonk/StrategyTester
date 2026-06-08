"""Download and cache daily crypto price data from Yahoo Finance (via yfinance).

The rest of the project only ever calls `get_prices(ticker)`. It returns a clean
pandas DataFrame that backtesting.py can consume directly:

    - a DatetimeIndex (one row per day), sorted oldest -> newest
    - columns named exactly: Open, High, Low, Close, Volume  (capitalised!)
    - numeric dtypes, with any missing rows dropped

Caching strategy
----------------
We download the *full* available history once (HISTORY_START -> today) and cache
that superset to data/<ticker>.csv. Every call then slices the cache down to the
requested ``[start, end]`` window. So changing START/END in config.py takes effect
on the very next run -- you do NOT need to delete the CSV. Pass ``refresh=True``
(or delete the CSV) only when you want to pull *newer* bars from Yahoo.
"""

from __future__ import annotations

import datetime as dt
import os
import tempfile
from pathlib import Path

import pandas as pd
import yfinance as yf

from . import config

# backtesting.py REQUIRES these exact (capitalised) column names.
_OHLCV = ["Open", "High", "Low", "Close", "Volume"]

# If the newest cached bar is older than this (and END is open-ended), print a
# gentle "data may be stale" hint. Kept generous so normal use stays quiet --
# we never silently hit the network; refreshing is always your explicit choice.
_STALE_AFTER_DAYS = 3


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
      * the same date can occasionally appear twice; we keep the latest.
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

    # Yahoo sometimes repeats a date (e.g. a re-stated last bar); keep the latest.
    df = df[~df.index.duplicated(keep="last")]
    return df


def _drop_incomplete_last_bar(df: pd.DataFrame) -> pd.DataFrame:
    """Crypto trades 24/7, so 'today's' daily bar is still forming -- its OHLC
    keeps changing until 00:00 UTC. Drop it so we never backtest a partial bar."""
    if df.empty:
        return df
    today_utc = pd.Timestamp(dt.datetime.now(dt.timezone.utc).date())
    if df.index[-1].normalize() >= today_utc:
        return df.iloc[:-1]
    return df


def _slice(df: pd.DataFrame, start: str | None, end: str | None) -> pd.DataFrame:
    """Restrict to the [start, end] window (inclusive). None means open-ended."""
    if start is not None:
        df = df[df.index >= pd.to_datetime(start)]
    if end is not None:
        df = df[df.index <= pd.to_datetime(end)]
    return df


def _warn_if_stale(df: pd.DataFrame, ticker: str, end: str | None) -> None:
    """If END is open-ended but the cache is old, nudge the user to refresh."""
    if end is not None or df.empty:
        return
    last = df.index[-1].normalize()
    today = pd.Timestamp(dt.datetime.now(dt.timezone.utc).date())
    age = (today - last).days
    if age > _STALE_AFTER_DAYS:
        print(
            f"  (note: cached {ticker} ends {last.date()} -- {age} days old; "
            f"pass refresh=True or delete data/{ticker}.csv to pull newer bars)"
        )


def _atomic_write_csv(df: pd.DataFrame, path: Path) -> None:
    """Write the CSV via a temp file + rename, so a crash mid-write can't leave a
    half-written (corrupt) cache behind."""
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    os.close(fd)
    try:
        df.to_csv(tmp)
        os.replace(tmp, path)  # atomic on the same filesystem
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def get_prices(
    ticker: str,
    start: str | None = None,
    end: str | None = None,
    refresh: bool = False,
) -> pd.DataFrame:
    """Return clean daily OHLCV for `ticker`, sliced to the requested window.

    The full history is cached to data/<ticker>.csv; we slice that cache to
    ``[start, end]`` on every call. So changing START/END in config.py takes
    effect on the next run with no need to delete the cache. Defaults come from
    config.START / config.END. Pass ``refresh=True`` to re-download newer bars.
    """
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = config.DATA_DIR / f"{ticker}.csv"

    start = config.START if start is None else start
    end = config.END if end is None else end

    if refresh or not path.exists():
        # Always cache the FULL history so future START/END tweaks need no re-download.
        full = _drop_incomplete_last_bar(_clean(_download(ticker, config.HISTORY_START, None)))
        _atomic_write_csv(full, path)
    else:
        full = _drop_incomplete_last_bar(
            _clean(pd.read_csv(path, index_col=0, parse_dates=True))
        )

    _warn_if_stale(full, ticker, end)
    return _slice(full, start, end)
