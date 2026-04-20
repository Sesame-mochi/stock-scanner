"""
Stock Scanner Backend — Yahoo Finance
Run with: python server.py
Requires: pip install flask yfinance flask-cors
"""

from flask import Flask, jsonify
from flask_cors import CORS
import yfinance as yf

app = Flask(__name__)
CORS(app)  # Allow requests from your React frontend


def safe(val, default="N/A"):
    """Return a clean value or default if None/NaN."""
    try:
        if val is None:
            return default
        import math
        if isinstance(val, float) and math.isnan(val):
            return default
        return val
    except Exception:
        return default


@app.route("/stock/<ticker>")
def get_stock_data(ticker):
    try:
        t = ticker.upper().strip()
        stock = yf.Ticker(t)
        info = stock.info

        # --- Price & Volume ---
        current_price   = safe(info.get("currentPrice") or info.get("regularMarketPrice"))
        prev_close      = safe(info.get("previousClose"))
        day_high        = safe(info.get("dayHigh"))
        day_low         = safe(info.get("dayLow"))
        week_52_high    = safe(info.get("fiftyTwoWeekHigh"))
        week_52_low     = safe(info.get("fiftyTwoWeekLow"))
        volume          = safe(info.get("volume"))
        avg_volume      = safe(info.get("averageVolume"))
        market_cap      = safe(info.get("marketCap"))

        # Price change
        price_change_pct = "N/A"
        try:
            price_change_pct = round(
                ((float(current_price) - float(prev_close)) / float(prev_close)) * 100, 2
            )
        except Exception:
            pass

        # Volume vs average
        volume_ratio = "N/A"
        try:
            volume_ratio = round(float(volume) / float(avg_volume), 2)
        except Exception:
            pass

        # 52-week position
        week_52_position = "N/A"
        try:
            rng = float(week_52_high) - float(week_52_low)
            week_52_position = round(
                ((float(current_price) - float(week_52_low)) / rng) * 100, 1
            )
        except Exception:
            pass

        # --- Technicals (from history) ---
        hist = stock.history(period="6mo")

        sma_50 = sma_200 = rsi = "N/A"
        price_vs_sma50 = price_vs_sma200 = "N/A"

        try:
            if len(hist) >= 50:
                sma_50 = round(hist["Close"].tail(50).mean(), 2)
                price_vs_sma50 = round(
                    ((float(current_price) - sma_50) / sma_50) * 100, 2
                )
            if len(hist) >= 200:
                sma_200 = round(hist["Close"].tail(200).mean(), 2)
                price_vs_sma200 = round(
                    ((float(current_price) - sma_200) / sma_200) * 100, 2
                )
        except Exception:
            pass

        # RSI (14-period)
        try:
            closes = hist["Close"].tail(15)
            deltas = closes.diff().dropna()
            gains = deltas.clip(lower=0).mean()
            losses = (-deltas.clip(upper=0)).mean()
            if losses != 0:
                rs = gains / losses
                rsi = round(100 - (100 / (1 + rs)), 1)
            else:
                rsi = 100
        except Exception:
            pass

        # 1-month & 3-month returns
        ret_1m = ret_3m = "N/A"
        try:
            if len(hist) >= 21:
                ret_1m = round(
                    ((hist["Close"].iloc[-1] - hist["Close"].iloc[-21]) / hist["Close"].iloc[-21]) * 100, 2
                )
            if len(hist) >= 63:
                ret_3m = round(
                    ((hist["Close"].iloc[-1] - hist["Close"].iloc[-63]) / hist["Close"].iloc[-63]) * 100, 2
                )
        except Exception:
            pass

        # --- Fundamentals ---
        pe_ratio        = safe(info.get("trailingPE"))
        fwd_pe          = safe(info.get("forwardPE"))
        pb_ratio        = safe(info.get("priceToBook"))
        ps_ratio        = safe(info.get("priceToSalesTrailing12Months"))
        peg_ratio       = safe(info.get("pegRatio"))
        ev_ebitda       = safe(info.get("enterpriseToEbitda"))
        debt_to_equity  = safe(info.get("debtToEquity"))
        roe             = safe(info.get("returnOnEquity"))
        profit_margin   = safe(info.get("profitMargins"))
        revenue_growth  = safe(info.get("revenueGrowth"))
        earnings_growth = safe(info.get("earningsGrowth"))
        free_cash_flow  = safe(info.get("freeCashflow"))
        dividend_yield  = safe(info.get("dividendYield"))

        # --- Earnings ---
        eps_trailing    = safe(info.get("trailingEps"))
        eps_forward     = safe(info.get("forwardEps"))
        next_earnings   = safe(info.get("earningsDate") or info.get("nextEarningsDate"))

        # Analyst target
        analyst_target  = safe(info.get("targetMeanPrice"))
        upside_potential = "N/A"
        try:
            upside_potential = round(
                ((float(analyst_target) - float(current_price)) / float(current_price)) * 100, 1
            )
        except Exception:
            pass

        analyst_reco    = safe(info.get("recommendationKey", "").upper())
        num_analysts    = safe(info.get("numberOfAnalystOpinions"))

        # --- News headlines ---
        news_headlines = []
        try:
            news = stock.news or []
            news_headlines = [
                item.get("content", {}).get("title", item.get("title", ""))
                for item in news[:5]
                if item.get("content", {}).get("title") or item.get("title")
            ]
        except Exception:
            pass

        return jsonify({
            "ticker": t,
            "companyName": safe(info.get("longName", t)),
            "sector": safe(info.get("sector")),
            "industry": safe(info.get("industry")),
            "description": safe(info.get("longBusinessSummary", ""))[:300],

            "price": {
                "current": current_price,
                "previousClose": prev_close,
                "changePercent": price_change_pct,
                "dayHigh": day_high,
                "dayLow": day_low,
                "week52High": week_52_high,
                "week52Low": week_52_low,
                "week52Position": week_52_position,
                "marketCap": market_cap,
            },

            "volume": {
                "current": volume,
                "average": avg_volume,
                "ratio": volume_ratio,
            },

            "technicals": {
                "sma50": sma_50,
                "sma200": sma_200,
                "priceVsSMA50Pct": price_vs_sma50,
                "priceVsSMA200Pct": price_vs_sma200,
                "rsi14": rsi,
                "return1Month": ret_1m,
                "return3Month": ret_3m,
            },

            "fundamentals": {
                "peRatio": pe_ratio,
                "forwardPE": fwd_pe,
                "pbRatio": pb_ratio,
                "psRatio": ps_ratio,
                "pegRatio": peg_ratio,
                "evEbitda": ev_ebitda,
                "debtToEquity": debt_to_equity,
                "returnOnEquity": roe,
                "profitMargin": profit_margin,
                "revenueGrowth": revenue_growth,
                "earningsGrowth": earnings_growth,
                "freeCashflow": free_cash_flow,
                "dividendYield": dividend_yield,
            },

            "earnings": {
                "epsTrailing": eps_trailing,
                "epsForward": eps_forward,
                "nextEarningsDate": str(next_earnings),
            },

            "analyst": {
                "targetPrice": analyst_target,
                "upsidePotential": upside_potential,
                "recommendation": analyst_reco,
                "numberOfAnalysts": num_analysts,
            },

            "news": news_headlines,
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    print("🚀 Stock Scanner backend running at http://localhost:5000")
    app.run(debug=True, port=5000)
