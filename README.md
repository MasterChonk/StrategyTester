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
| **Donchian breakout** (Turtle-style) | the daily **close** tops the **prior** 20-day high | the close drops below the **prior** 10-day low |

Both are **long-or-cash**: you're either fully in the coin or fully in cash. No
shorting, no leverage — the simplest realistic setup for spot crypto.

> **A note on the Donchian rule:** this project uses a *close-confirmation*
> variant — it acts when the daily **close** clears a channel built only from
> **prior** bars (today's own bar excluded). That differs slightly from the
> classic Turtle stop, which fires the instant price *touches* a new high
> intraday. The close-based version trades a little less and sidesteps intrabar
> whipsaw.

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

Data is cached in `data/*.csv` (the **full** history), so re-runs are instant and
work offline. Changing `START`/`END` in `config.py` re-slices that cache
automatically — **no need to delete anything**. Delete the CSVs (or call
`get_prices(ticker, refresh=True)`) only to pull *newer* bars.

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

Below is a real run over **2017-01-01 → 2026-06-06** (your numbers will differ as
new price history accrues). The column that matters is **`Excess %`** — a
strategy's return *minus its own same-row buy & hold*, which is the fair
same-window scorecard (see [the warm-up note](#a-subtlety-warm-up-windows)).
Positive means it beat simply holding.

| Coin | Strategy | Return % | Buy&Hold % | Excess % | Ann. % | Sharpe | Max DD % | Win % | Trades |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| BTC | SMA Cross | 827 | 5,021 | **-4,194** | 26.6 | 0.48 | **-58.6** | 43.8 | 16 |
| BTC | **Donchian** | **7,371** | 6,692 | **+679** | 58.0 | **0.81** | **-55.5** | 46.0 | 50 |
| BTC | Buy & Hold | 5,804 | 5,990 | -186 | 54.1 | 0.46 | -83.4 | 100 | 1 |
| ETH | SMA Cross | 777 | 65 | **+712** | 28.8 | 0.35 | **-72.2** | 46.7 | 15 |
| ETH | **Donchian** | **1,396** | 230 | **+1,166** | 37.1 | **0.47** | **-61.0** | 51.2 | 43 |
| ETH | Buy & Hold | 425 | 386 | +38 | 21.3 | 0.17 | -93.8 | 100 | 1 |

**What this particular run shows — and why even this needs a skeptical eye:**

- **Drawdowns shrank a lot.** Buy & hold suffered an ~**-83%** (BTC) and ~**-94%**
  (ETH) peak-to-trough crash. Both trend strategies cut that to roughly **-55% to
  -72%**. That smaller pain is the core selling point of trend following.
- **Donchian beat its same-window benchmark on both coins** (Excess **+679** BTC,
  **+1,166** ETH) *and* on risk — higher Sharpe, lower drawdown. That's the
  textbook trend-following win.
- **Read `Excess`, but don't trust it blindly.** ETH's SMA shows a fat **+712** —
  yet that's largely a *warm-up artifact*: a 100-day average can't trade until
  ~100 days in, which here lands near ETH's early-2018 peak, so its B&H yardstick
  (just 65%) is depressed. The strategy isn't brilliant; the benchmark is
  crippled. The *same* SMA rule lagged BTC by **-4,194**. The specific rule,
  parameters, **and even the start date** matter enormously.
- **Higher Sharpe = better risk-adjusted return** — but with a 0% risk-free
  assumption and only ~15–50 trades, treat the 0.81-vs-0.46 gap as suggestive,
  not proven.

Don't over-read these exact figures — see the [caveats](#caveats-read-this-before-you-trust-any-number).

---

## 5. How to read every column

| Column | Plain English |
|---|---|
| **Return [%]** | Total growth of the portfolio over the whole window. |
| **Buy & Hold Return [%]** | What just holding the coin returned over *the same window* — the benchmark to beat. |
| **Excess vs B&H [%]** | `Return − Buy & Hold Return` on the same row — the fair, same-window scorecard. Positive = it beat holding. |
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
- `START` / `END` — test a single bull or bear market in isolation (re-slices the cache instantly; no deletion needed).

---

## 7. Caveats (read this before you trust any number)

Backtests lie in predictable ways. The big ones:

1. **Overfitting / curve-fitting.** If you try 100 parameter combinations and keep
   the best, you've probably just fit noise. It will *not* repeat live. Pick
   parameters for a *reason*, and test on data you didn't tune on.
2. **Tiny, correlated sample.** Each strategy makes only ~15–50 trades, and BTC
   and ETH move together (~0.8 correlation) — so this is closer to *one* noisy
   experiment than six independent ones. A 0.81-vs-0.46 Sharpe gap sits well
   inside that noise. There are no confidence intervals here; don't read a
   ranking as a verdict.
3. **Past ≠ future.** Crypto's 2017–2021 era of giant trends may never recur.
4. **Survivorship bias.** We picked BTC and ETH — coins that *survived and won*.
   Thousands of dead coins would have wrecked these returns. Real selection is hard.
5. **Costs & slippage.** We model a 0.1% fee but **not slippage** (the gap between
   the price you see and the price you get), funding, or spreads. Real costs are higher.
6. **Data quality.** Prices come from Yahoo Finance, whose crypto "Open" is a
   00:00-UTC snapshot of a 24/7 market and whose history has occasional gaps and
   glitches. Because fills happen at the next day's open, that one number matters;
   a real system would use exchange data (e.g. [`ccxt`](https://github.com/ccxt/ccxt)).
7. **Regime dependence.** Trend following shines in trending markets and bleeds in
   choppy ones. A great backtest can hide years of painful sideways grind.
8. **Annualization & Sharpe are approximate.** Crypto trades 365 days/yr but the
   engine annualizes on a calendar basis, and Sharpe assumes a **0% risk-free
   rate** (real T-bills were ~5%, so every Sharpe here is flattering). Treat the
   annualized and risk-adjusted figures as ballpark, not gospel.
9. **Lookahead bias — handled here.** Signals are computed on a day's *close* and
   orders fill at the *next* day's open. You can't trade on information you
   wouldn't have had yet. (This is the #1 mistake beginners make; this project
   avoids it by design, and a test asserts it.)

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
  settings also work (fragile peaks are overfit). Sweep without editing config by
  passing overrides: `run_backtest(prices, SmaCross, params={"fast": 50, "slow": 200})`.
- **Walk-forward testing** — tune on 2017–2020 (`get_prices("BTC-USD", end="2020-12-31")`),
  then test untouched on 2021 onward. The cache slices to any window instantly.
- **More coins / a portfolio** — combine signals across assets and size by volatility.
- **Add shorting** — go short on down-trends (needs a derivatives venue in reality).
- **Intraday data** — swap yfinance for [`ccxt`](https://github.com/ccxt/ccxt) to
  pull hourly/4h candles straight from exchanges.

---

## 10. Requirements

- Python ≥ 3.13 (managed by uv)
- `yfinance`, `backtesting`, `pandas`, `numpy` (installed via `uv sync`)
