"""Tests for the comparison-table builder."""

from __future__ import annotations

from crypto_trend.report import build_table


def test_build_table_adds_excess_after_bh_and_keeps_trades_int():
    rows = [
        {
            "Coin": "X", "Strategy": "S",
            "Return [%]": 150.0, "Buy & Hold Return [%]": 100.0,
            "Sharpe Ratio": 1.5, "# Trades": 7.0,
        }
    ]
    df = build_table(rows)
    cols = list(df.columns)

    # Excess column exists and sits immediately after Buy & Hold Return.
    assert "Excess vs B&H [%]" in cols
    assert cols[cols.index("Buy & Hold Return [%]") + 1] == "Excess vs B&H [%]"

    # It is exactly Return - Buy & Hold Return, and # Trades stays a whole number.
    assert df.loc[0, "Excess vs B&H [%]"] == 50.0
    assert df["# Trades"].dtype.kind in "iu"
