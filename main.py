"""Entry point: pull data, run every (coin x strategy) backtest, report results.

Run it with:

    uv run python main.py

Outputs:
    results/comparison.csv          -- the summary table (also printed below)
    results/<COIN>_<STRATEGY>.html  -- an interactive chart for each run
"""

from __future__ import annotations

import sys

from crypto_trend import config
from crypto_trend.backtest import STRATEGIES, run_backtest, stats_to_row
from crypto_trend.data import get_prices
from crypto_trend.report import build_table, save_and_print


def _make_console_utf8() -> None:
    """Let the Windows console print any stray non-ASCII without crashing."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
        except Exception:
            pass


def main() -> None:
    _make_console_utf8()
    config.RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    rows: list[dict] = []
    for coin in config.COINS:
        print(f"\n--- {coin} ---")
        prices = get_prices(coin)
        print(
            f"  {len(prices):,} daily bars "
            f"({prices.index.min().date()} -> {prices.index.max().date()})"
        )

        for name, strategy_cls in STRATEGIES.items():
            safe = name.replace(" ", "").replace("&", "And")
            plot_path = config.RESULTS_DIR / f"{coin}_{safe}.html"
            _, stats = run_backtest(prices, strategy_cls, plot_path=plot_path)
            rows.append(stats_to_row(coin, name, stats))
            print(
                f"  {name:<18} "
                f"return={stats['Return [%]']:>9,.1f}%  "
                f"trades={int(stats['# Trades']):>4}  "
                f"maxDD={stats['Max. Drawdown [%]']:>7,.1f}%  "
                f"Sharpe={stats['Sharpe Ratio']:>5.2f}"
            )

    table = build_table(rows)
    out = save_and_print(table)

    print(f"\nSaved table  -> {out}")
    print(f"Saved charts -> {config.RESULTS_DIR}  (open the .html files in a browser)")
    print("\nWhat to look at: does either trend strategy beat 'Buy & Hold' on")
    print("return, and does it do so with a smaller Max. Drawdown? See README.md")
    print("for how to read every column and the caveats that matter.")


if __name__ == "__main__":
    main()
