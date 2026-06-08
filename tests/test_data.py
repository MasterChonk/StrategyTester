"""Tests for the data/caching layer -- all fully offline.

The key guarantees here:
  1. START/END actually slice the cache (the bug this project used to have).
  2. A cache hit never touches the network.
  3. Duplicate dates from Yahoo are de-duplicated.

Run with:  uv run pytest
"""

from __future__ import annotations

import pandas as pd

from crypto_trend import config, data


def _write_cache(dir_, ticker: str, start: str = "2015-01-01", periods: int = 2000) -> None:
    """Write a synthetic full-history cache CSV in the shape get_prices reads."""
    idx = pd.date_range(start, periods=periods, freq="D")
    px = pd.Series(range(periods), index=idx, dtype=float) + 100.0
    df = pd.DataFrame(
        {"Open": px, "High": px + 1, "Low": px - 1, "Close": px, "Volume": 1},
        index=idx,
    )
    df.index.name = "Date"
    df.to_csv(dir_ / f"{ticker}.csv")


def test_get_prices_slices_to_start_end(tmp_path, monkeypatch):
    """Changing START/END must re-slice the cache -- no CSV deletion needed."""
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    _write_cache(tmp_path, "FAKE-USD")

    out = data.get_prices("FAKE-USD", start="2017-01-01", end="2017-06-30")

    assert len(out) > 0
    assert out.index.min() >= pd.Timestamp("2017-01-01")
    assert out.index.max() <= pd.Timestamp("2017-06-30")


def test_cache_hit_does_not_hit_the_network(tmp_path, monkeypatch):
    """With a cache present and refresh=False, yf.download must NOT be called."""
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    _write_cache(tmp_path, "FAKE-USD")

    def _boom(*args, **kwargs):
        raise AssertionError("network download must not run on a cache hit")

    monkeypatch.setattr(data.yf, "download", _boom)
    out = data.get_prices("FAKE-USD")  # would raise if it tried to download
    assert len(out) > 0


def test_clean_drops_duplicate_dates():
    """yfinance can repeat a date; _clean keeps the most recent row."""
    idx = pd.to_datetime(["2020-01-01", "2020-01-01", "2020-01-02"])
    raw = pd.DataFrame(
        {"Open": [1, 2, 3], "High": [1, 2, 3], "Low": [1, 2, 3],
         "Close": [1, 2, 3], "Volume": [1, 1, 1]},
        index=idx,
    )
    cleaned = data._clean(raw)
    assert cleaned.index.is_unique
    assert len(cleaned) == 2
    assert cleaned.loc["2020-01-01", "Close"] == 2  # keep="last"
