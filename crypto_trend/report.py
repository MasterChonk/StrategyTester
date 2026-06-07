"""Turn the collected backtest rows into a readable table + a saved CSV."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from . import config


def build_table(rows: list[dict]) -> pd.DataFrame:
    """Assemble the per-(coin, strategy) rows into one tidy DataFrame."""
    df = pd.DataFrame(rows)

    # Round the numeric columns for readability; keep # Trades as a whole number.
    numeric = [c for c in df.columns if c not in ("Coin", "Strategy")]
    df[numeric] = df[numeric].round(2)
    if "# Trades" in df.columns:
        df["# Trades"] = df["# Trades"].astype(int)
    return df


def save_and_print(df: pd.DataFrame, path: str | Path | None = None) -> Path:
    """Save the table to results/comparison.csv and print it to the console."""
    config.RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out = Path(path) if path is not None else config.RESULTS_DIR / "comparison.csv"
    df.to_csv(out, index=False)

    # Print a clean, aligned, ASCII-only table (safe for every terminal).
    print("\n" + "=" * 80)
    print("STRATEGY COMPARISON  (per coin: two trend strategies vs. buy & hold)")
    print("=" * 80)
    with pd.option_context(
        "display.max_columns", None,
        "display.width", 1000,
        "display.float_format", lambda x: f"{x:,.2f}",
    ):
        print(df.to_string(index=False))
    return out
