# NSE/BSE Swing Trading Bot

A rule-based decision-support bot for **swing trading Indian equities (NSE/BSE)**.
It pulls daily price data from Yahoo Finance, applies a documented technical
rule set, and outputs **BUY / SELL / HOLD / AVOID** signals with an entry
price, stop-loss, target, and position size — plus the exact reasons behind
each call.

> **Disclaimer:** This is an educational/decision-support tool, not financial
> advice, and it does **not** place real orders. Free Yahoo Finance data is
> delayed (~15 min) and not licensed for commercial use. Always verify with
> your broker's live feed before acting, and consult a SEBI-registered
> advisor for real trading decisions.

---

## 1. Exchange & style

- **Exchange:** NSE / BSE (Indian equities / shares)
- **Style:** Swing trading — daily candles, holding period from a few days to
  a few weeks (not intraday, not scalping)

## 2. Data sources

**Historical daily candles (used for all indicators/rules):**
[Yahoo Finance](https://finance.yahoo.com) via the `yfinance` Python library.
NSE tickers use a `.NS` suffix (e.g. `RELIANCE.NS`), BSE tickers use `.BO`.

**Live ticker price (used for the terminal's top strip):**
The app tries **NSE India's own official website API** first (`nse_data.py`)
— genuinely live, exchange-sourced, with only a few seconds of delay — and
automatically falls back to Yahoo Finance if NSE blocks or errors out
(NSE occasionally rate-limits or changes its API). You'll see which source
is live in the terminal's status line.

Both sources are fetched **server-side by `app.py`**, not by your browser
directly — this matters because neither Yahoo nor NSE send the CORS headers
a browser needs to call them directly (unlike crypto exchanges such as
Binance, which do allow direct browser calls). Fetching server-side and
serving the page from the same local server avoids that problem entirely.

## 3. The trading rules

### Trend filter (mandatory context)
| Condition | Meaning |
|---|---|
| Close > EMA50 > EMA200 | Uptrend — only long setups allowed |
| Close < EMA50 < EMA200 | Downtrend — bot marks `AVOID`, no fresh buys |

### BUY — requires uptrend **and** at least 2 of these 4 confirmations
1. RSI(14) between 45–65, or just crossed above 50
2. MACD line crossed above the signal line within the last 3 candles
3. Volume today > 1.2× the 20-day average volume
4. Price breaking above the 20-day high, **or** bouncing off EMA20 support

A BUY is only confirmed if the resulting **Reward:Risk ≥ 2:1** (configurable).

### SELL — any one of these fires an exit signal
- RSI(14) > 70 and turning down (overbought reversal)
- MACD bearish crossover (MACD crosses below signal line)
- Close breaks below EMA20 (short-term trend break)
- Price reaches the pre-computed target

### HOLD
No trigger fired; if you're in a position, stay in it and keep watching
the stop-loss/target.

### Stop-loss & risk management
- **Initial stop-loss** = the tighter of: (a) the 10-day swing low, or
  (b) Entry − 1.5 × ATR(14)
- **Trailing stop:** once price moves 1R (one risk-unit) in your favor, move
  the stop to breakeven; after that, trail using EMA20
- **Position size** = (Capital × Risk% ) ÷ (Entry − Stop-loss)
- Default risk per trade: **1% of capital** (adjustable in the dashboard/CLI)
- Minimum Reward:Risk enforced: **2:1** (adjustable)

## 4. Files

| File | Purpose |
|---|---|
| `strategy.py` | Indicators (EMA, RSI, MACD, ATR) + the rule engine (`generate_signal`) |
| `data_feed.py` | Fetches OHLCV history from Yahoo Finance for NSE/BSE tickers |
| `nse_data.py` | Fetches the LIVE quote directly from NSE India's own API (with Yahoo fallback) |
| `swing_bot.py` | Command-line bot: one-shot scan or a live monitoring loop |
| `dashboard.py` | Interactive Streamlit web dashboard with charts |
| `app.py` + `templates/index.html` | Dark "live terminal" web UI (Flask backend + browser front-end) |
| `requirements.txt` | Python dependencies |

### Why the live terminal needs a small Python server (`app.py`)
A pure HTML page that calls Yahoo Finance or NSE directly from the browser will fail with a
CORS error — Yahoo/NSE don't send the headers browsers require for cross-origin requests
(unlike crypto exchanges such as Binance, which do). `app.py` fetches the data server-side
(where CORS doesn't apply) and serves the terminal page from the same origin, so the browser
only ever talks to your own local server. This is the standard fix for this exact problem.

## 5. Setup

```bash
pip install -r requirements.txt
```

## 6. Usage

### Option A — Command line
```bash
# One-time scan of a watchlist
python swing_bot.py --tickers RELIANCE,TCS,INFY,HDFCBANK --exchange NSE

# Live monitoring during market hours, refreshing every 15 minutes
python swing_bot.py --tickers RELIANCE,TCS --exchange NSE --live --interval 15

# Custom capital and risk settings
python swing_bot.py --tickers RELIANCE --capital 200000 --risk 1.5 --min-rr 2.5
```

### Option B — Interactive Streamlit dashboard
```bash
streamlit run dashboard.py
```
This opens a browser dashboard where you can:
- Enter a watchlist (comma-separated tickers)
- Set capital, risk %, and minimum reward:risk
- See a color-coded signal table (green=BUY, red=SELL, tan=HOLD, orange=AVOID)
- Click into any ticker for the reasoning, EMA/RSI/MACD charts, entry/SL/target

### Option C — Dark "live terminal" web UI (recommended for a demo/submission)
```bash
python app.py
```
Then open **http://127.0.0.1:5000** in your browser. This gives you a dark trading-terminal
style page: a live ticker strip, price chart with EMA overlays, RSI/MACD panels, the current
BUY/SELL/HOLD/AVOID signal with reasoning, the trade plan (entry/stop/target/qty), and an
event log. Click "Scan ticker", then "Start live monitor" to have it poll for price updates
every 10s and re-check the signal every 60s.

## 7. How to extend for the assignment

Ideas you can add on top to strengthen the submission:
- **Backtesting**: loop the rule engine over historical data and compute
  win-rate, average R multiple, max drawdown
- **Paper-trading ledger**: log signals to a CSV and track hypothetical P&L
- **Alerts**: send a Telegram/WhatsApp/email message when a new BUY fires
- **Sector/Nifty50 scanner**: run the bot across the whole Nifty 50 list
  automatically instead of a manual watchlist
- **AI commentary layer**: pass the signal + reasons into an LLM (e.g. the
  Anthropic API) to generate a plain-English trade rationale for each call

## 8. Limitations to disclose in your report

- Yahoo Finance free data can lag or occasionally miss corporate actions
- The rule set is a *trend-following momentum* strategy — it will
  underperform in sideways/choppy markets (a known limitation to mention)
- No slippage/brokerage/tax modeling is included
- Not a substitute for professional/registered investment advice
