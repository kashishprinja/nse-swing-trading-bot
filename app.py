"""
app.py
------
Local web server for the NSE/BSE Swing Trading Bot "live terminal".

Why a server at all, instead of a pure HTML page hitting Yahoo Finance
directly from the browser (like a crypto dashboard would hit Binance)?
--------------------------------------------------------------------
Binance's public API sends CORS headers, so a browser can call it directly.
Yahoo Finance and NSE India do NOT send CORS headers, so a browser calling
them directly gets blocked with a CORS error, on any computer, in any
browser. The fix is to fetch the data on the SERVER (Python, where CORS
doesn't apply) and have the browser only ever talk to this local server.

RUN:
    pip install -r requirements.txt
    python app.py
Then open the URL it prints (usually http://127.0.0.1:5000) in your browser.
"""

from flask import Flask, jsonify, request, render_template

from data_feed import fetch_daily, fetch_live_quote, normalize_ticker
from nse_data import get_live_quote_with_fallback
from strategy import add_indicators, generate_signal, position_size

app = Flask(__name__)

WATCHLIST_DEFAULT = ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ITC", "SBIN", "TATAMOTORS", "WIPRO"]


@app.route("/")
def index():
    return render_template("index.html", default_watchlist=WATCHLIST_DEFAULT)


@app.route("/api/quote")
def api_quote():
    """
    Latest snapshot price for the ticker strip. Polled every few seconds.
    Tries NSE India's own API first (more live), falls back to Yahoo
    Finance automatically if NSE blocks or errors out.
    """
    ticker = request.args.get("ticker", "RELIANCE")
    exchange = request.args.get("exchange", "NSE")
    try:
        if exchange.upper() == "NSE":
            q = get_live_quote_with_fallback(ticker, yahoo_fallback_fn=fetch_live_quote)
        else:
            q = fetch_live_quote(ticker, exchange)
            q["source"] = "Yahoo Finance"
        return jsonify({"ok": True, **q})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 502


@app.route("/api/scan")
def api_scan():
    """
    Full pull: history + indicators + rule-engine signal for one ticker.
    Polled less often (e.g. every 60s) since it's a daily-candle strategy.
    """
    ticker = request.args.get("ticker", "RELIANCE")
    exchange = request.args.get("exchange", "NSE")
    period = request.args.get("period", "2y")
    capital = float(request.args.get("capital", 100000))
    risk_pct = float(request.args.get("risk", 1.0))
    min_rr = float(request.args.get("min_rr", 2.0))

    try:
        df = fetch_daily(ticker, exchange, period=period)
        result = generate_signal(df, min_reward_risk=min_rr)
        result["qty"] = position_size(capital, risk_pct, result.get("entry"), result.get("stop_loss"))

        dfi = add_indicators(df).tail(180).reset_index()
        date_col = dfi.columns[0]
        candles = []
        for _, row in dfi.iterrows():
            candles.append({
                "date": str(row[date_col].date()) if hasattr(row[date_col], "date") else str(row[date_col]),
                "close": round(float(row["Close"]), 2),
                "ema20": round(float(row["EMA20"]), 2) if row["EMA20"] == row["EMA20"] else None,
                "ema50": round(float(row["EMA50"]), 2) if row["EMA50"] == row["EMA50"] else None,
                "ema200": round(float(row["EMA200"]), 2) if row["EMA200"] == row["EMA200"] else None,
                "rsi14": round(float(row["RSI14"]), 1) if row["RSI14"] == row["RSI14"] else None,
                "macd": round(float(row["MACD"]), 3) if row["MACD"] == row["MACD"] else None,
                "macd_signal": round(float(row["MACD_SIGNAL"]), 3) if row["MACD_SIGNAL"] == row["MACD_SIGNAL"] else None,
                "volume": int(row["Volume"]),
            })

        return jsonify({
            "ok": True,
            "symbol": normalize_ticker(ticker, exchange),
            "signal": result,
            "candles": candles,
        })
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 502


if __name__ == "__main__":
    app.run(debug=True, port=5000)
