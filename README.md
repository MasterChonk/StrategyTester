# Crypto Trend-Following Backtester

A small, beginner-friendly Python project that **downloads daily crypto prices**
and **backtests two classic trend-following strategies** against simply buying
and holding. The goal is to learn, hands-on, whether "ride the trend" rules would
actually have worked on Bitcoin and Ethereum — and to understand *how* to judge a
trading strategy honestly.

> ⚠️ **Not financial advice.** This is an educational backtesting toy. A strategy
> that looked good on past data routinely fails on future data. See
> [Caveats](#caveats-read-this-before-you-trust-any-number).

---

## 1. What is trend following?

> **Ride an asset while it's going up; step aside when it turns down.**

It's the opposite of "buy the dip." A trend follower doesn't try to predict tops
or bottoms — it reacts to price. The bet is that big moves persist long enough to
catch a chunk of them. The trade-off: in choppy, sideways markets you get
"whipsawed" (lots of small losing trades), but in a crash you're already in cash,
so you sidestep the worst of it. **Smaller drawdowns are the whole point.**

This project tests two of the most famous trend rules:

| Strategy | Buy when… | Sell to cash when… |
|---|---|---|
| **Moving-Average (MA) crossover** | the 20-day average crosses **above** the 100-day average | the 20-day crosses back **below** the 100-day |
| **Donchian breakout** ("Turtle" rule) | price makes a new **20-day high** | price makes a new **10-day low** |

Both are **long-or-cash**: you're either fully in the coin or fully in cash. No
shorting, no leverage — the simplest realistic setup for spot crypto.

---

## 2. Quickstart

This project uses [uv](https://docs.astral.sh/uv/) to manage Python and packages.

```powershell
uv sync                 # one-time: create the venv + install dependencies
uv run python main.py   # download data, run all backtests, write results/
uv run pytest           # run the offline sanity tests
```

After `main.py` finishes you'll have:

- `results/comparison.csv` — the summary table (also printed to the screen)
- `results/<COIN>_<STRATEGY>.html` — an **interactive chart** per run (open in a
  browser): price with buy/sell markers, the equity curve, and drawdowns.

Data is cached in `data/*.csv`, so re-runs are instant and work offline. To pull
fresh bars later, delete the CSVs (or call `get_prices(ticker, refresh=True)`).

---

## 3. How it works (the pipeline)

```
 yfinance          strategies          backtesting.py            report
  data.py    -->   strategies.py  -->   backtest.py      -->    report.py
 download &        turn prices         simulate trades         compare vs
  cache OHLCV      into buy/sell       day-by-day, apply       buy & hold,
                   signals             0.1% fees               save CSV + charts
```

Every file is small and commented. The one you'll edit is **`config.py`**.

| File | Responsibility |
|---|---|
| `crypto_trend/config.py` | All settings: coins, dates, fees, cash, strategy parameters. |
| `crypto_trend/data.py` | Download + cache daily OHLCV; hand back a clean DataFrame. |
| `crypto_trend/strategies.py` | The `SmaCross`, `DonchianBreakout`, and `BuyAndHold` rules. |
| `crypto_trend/backtest.py` | Run one backtest; list the metrics we report. |
| `crypto_trend/report.py` | Build the comparison table, save `comparison.csv`. |
| `main.py` | Glue it all together and print the summary. |
| `tests/test_smoke.py` | Offline sanity checks (no network). |

---

## 4. Example results

Below is a real run over **2017 → 2026** (your numbers will differ as new price
history accrues). Read each strategy's `Return [%]` against the
`Buy & Hold Return [%]` **on the same row** — that's the fair, same-window
benchmark (see [the warm-up note](#a-subtlety-warm-up-windows)).

| Coin | Strategy | Return % | Buy&Hold % | Ann. % | Sharpe | Max DD % | Win % | Trades |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| BTC | SMA Cross | 827 | 5,021 | 26.6 | 0.48 | **-58.6** | 43.8 | 16 |
| BTC | **Donchian** | **7,371** | 6,692 | 58.0 | **0.81** | **-55.5** | 46.0 | 50 |
| BTC | Buy & Hold | 5,804 | 5,990 | 54.1 | 0.46 | -83.4 | 100 | 1 |
| ETH | SMA Cross | 777 | 65 | 28.8 | 0.35 | **-72.2** | 46.7 | 15 |
| ETH | **Donchian** | **1,396** | 230 | 37.1 | **0.47** | **-61.0** | 51.2 | 43 |
| ETH | Buy & Hold | 425 | 386 | 21.3 | 0.17 | -93.8 | 100 | 1 |

**What this particular run shows (a textbook trend-following result):**

- **Drawdowns shrank a lot.** Buy & hold suffered an ~**-83%** (BTC) and ~**-94%**
  (ETH) peak-to-trough crash. Both trend strategies cut that to roughly **-55% to
  -72%**. That smaller pain is the core selling point of trend following.
- **Donchian beat buy & hold** on return *and* risk for both coins (higher Sharpe,
  lower drawdown). The MA crossover reduced drawdown but **lagged buy & hold on
  raw return** — a reminder that "less risk" often costs some upside, and that the
  *specific rule and parameters* matter enormously.
- **Higher Sharpe = better risk-adjusted return.** Donchian's 0.81 (BTC) vs buy &
  hold's 0.46 means it earned more per unit of stomach-churning volatility.

Don't over-read these exact figures — see the [caveats](#caveats-read-this-before-you-trust-any-number).

---

## 5. How to read every column

| Column | Plain English |
|---|---|
| **Return [%]** | Total growth of the portfolio over the whole window. |
| **Buy & Hold Return [%]** | What just holding the coin returned over *the same window* — the benchmark to beat. |
| **Return (Ann.) [%]** | The return expressed as a smoothed yearly rate (CAGR). |
| **Volatility (Ann.) [%]** | How much returns bounced around per year — a risk measure. |
| **Sharpe Ratio** | Return per unit of risk (higher = better). < 1 is common; > 1 is good. |
| **Max. Drawdown [%]** | The worst peak-to-trough fall. The "how bad did it hurt" number. |
| **Win Rate [%]** | Share of trades that made money. (Trend systems often win < 50% but win big when they do.) |
| **# Trades** | How often it traded. More trades = more fees paid. |
| **Exposure Time [%]** | Share of the period actually invested (the rest in cash). |

### A subtlety: warm-up windows

A 100-day moving average can't be computed until you have 100 days of data. So
`SMA Cross` only *starts trading* ~100 days in, while `Donchian` starts ~20 days
in and `Buy & Hold` starts on day 1. backtesting.py measures each strategy's
`Buy & Hold Return [%]` over **that strategy's own trading window**, which is why
the benchmark differs slightly between rows. Always compare a row's `Return [%]`
to the `Buy & Hold Return [%]` **on the same row** for the fairest read.

---

## 6. Experiment

Open **`crypto_trend/config.py`** and change things, then re-run `python main.py`:

- `COINS` — add `"SOL-USD"`, `"BNB-USD"`, etc.
- `SMA_FAST` / `SMA_SLOW` — try the famous 50/200 "golden cross", or a faster 10/30.
- `DONCHIAN_ENTRY` / `DONCHIAN_EXIT` — the classic Turtles also used 55/20.
- `COMMISSION` — see how higher fees punish the strategies that trade most.
- `START` / `END` — test a single bull or bear market in isolation.

---

## 7. Caveats (read this before you trust any number)

Backtests lie in predictable ways. The big ones:

1. **Overfitting / curve-fitting.** If you try 100 parameter combinations and keep
   the best, you've probably just fit noise. It will *not* repeat live. Pick
   parameters for a *reason*, and test on data you didn't tune on.
2. **Past ≠ future.** Crypto's 2017–2021 era of giant trends may never recur.
3. **Survivorship bias.** We picked BTC and ETH — coins that *survived and won*.
   Thousands of dead coins would have wrecked these returns. Real selection is hard.
4. **Costs & slippage.** We model a 0.1% fee but **not slippage** (the gap between
   the price you see and the price you get), funding, or spreads. Real costs are higher.
5. **Regime dependence.** Trend following shines in trending markets and bleeds in
   choppy ones. A great backtest can hide years of painful sideways grind.
6. **Annualization is approximate.** Crypto trades 365 days/yr; the engine's
   annualized figures assume a calendar — treat them as ballpark, not gospel.
7. **Lookahead bias — handled here.** Signals are computed on a day's *close* and
   orders fill at the *next* day's open. You can't trade on information you
   wouldn't have had yet. (This is the #1 mistake beginners make; this project
   avoids it by design.)

---

## 8. Implementation note: why such a large `CASH`?

backtesting.py buys **whole units** of an asset. If your cash is smaller than one
unit's price (cash = $100k but 1 BTC = $105k), it buys **zero** units and silently
makes no trades — a notorious crypto gotcha. We sidestep it by using a large
nominal `CASH` ($100M) and sizing each trade as ~99% of equity. Because every
headline metric (return %, Sharpe, drawdown) is a **ratio**, the absolute dollar
amount doesn't change the conclusions — it just guarantees trades always execute.
The smoke test asserts `# Trades > 0`, so this can't silently regress.

---

## 9. Where to go next

- **Parameter robustness** — instead of one best setting, check that *nearby*
  settings also work. Fragile peaks are overfit.
- **Walk-forward testing** — tune on 2017–2020, test untouched on 2021–2026.
- **More coins / a portfolio** — combine signals across assets and size by volatility.
- **Add shorting** — go short on down-trends (needs a derivatives venue in reality).
- **Intraday data** — swap yfinance for [`ccxt`](https://github.com/ccxt/ccxt) to
  pull hourly/4h candles straight from exchanges.

---

## 10. Requirements

- Python ≥ 3.13 (managed by uv)
- `yfinance`, `backtesting`, `pandas`, `numpy` (installed via `uv sync`)
