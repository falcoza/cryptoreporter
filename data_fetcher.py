import yfinance as yf
from pycoingecko import CoinGeckoAPI
from datetime import datetime, timezone, timedelta
ing import pytz
from typing import Optional, Dict, Any

def calculate_percentage(old: Optional[float], new: Optional[float]) -> float:
    """Calculate percentage change with null safety and type hints."""
    if None in (old, new) or old == 0:
        return 0.0
    try:
        return ((new - old) / old) * 100
    except (TypeError, ZeroDivisionError):
        return 0.0

# ---- Generic crypto helper functions ----
def get_coin_ytd_price(cg: CoinGeckoAPI, coin_id: str) -> Optional[float]:
    """Fetch the price on Jan 1 of the current year for any coin via CoinGecko."""
    try:
        year = datetime.now(timezone.utc).year
        start = datetime(year, 1, 1, tzinfo=timezone.utc)
        end = start + timedelta(days=1)
        history = cg.get_coin_market_chart_range_by_id(
            coin_id, "zar",
            int(start.timestamp()),
            int(end.timestamp())
        )
        return history.get('prices', [[None, None]])[0][1]
    except Exception as e:
        print(f"⚠️ YTD error for {coin_id}: {e}")
        return None


def fetch_coin_historical(cg: CoinGeckoAPI, coin_id: str, days: int) -> Optional[float]:
    """Fetch historical coin price in ZAR for given days ago."""
    try:
        now = datetime.now(timezone.utc)
        target = now - timedelta(days=days)
        window = timedelta(hours=12)
        history = cg.get_coin_market_chart_range_by_id(
            coin_id, "zar",
            int((target - window).timestamp()),
            int((target + window).timestamp())
        )
        prices = history.get("prices", [])
        if not prices:
            return None
        target_ts = target.timestamp() * 1000
        closest = min(prices, key=lambda x: abs(x[0] - target_ts))
        return closest[1]
    except Exception as e:
        print(f"⚠️ Historical error for {coin_id} at {days} days: {e}")
        return None

# ---- Existing helpers for equities, FX, commodities ----
def fetch_historical(ticker: str, days: int) -> Optional[float]:
    try:
        buffer_days = max(5, days // 5)
        stock = yf.Ticker(ticker)
        df = stock.history(period=f"{days + buffer_days}d", interval="1d")
        if not df.empty and len(df) >= days + 1:
            return df['Close'].iloc[-days-1]
        return None
    except Exception as e:
        print(f"⚠️ Historical data error for {ticker}: {e}")
        return None

def get_ytd_reference_price(ticker: str) -> Optional[float]:
    try:
        stock = yf.Ticker(ticker)
        tz = pytz.timezone('Africa/Johannesburg')
        now = datetime.now(tz)
        start = tz.localize(datetime(now.year, 1, 1))
        end = start + timedelta(days=30)
        buffer_start = start - timedelta(days=14)

        df = stock.history(start=buffer_start, end=end, interval="1d")
        if not df.empty:
            df.index = df.index.tz_convert(tz)
            ytd = df[df.index >= start]
            if not ytd.empty:
                return ytd['Close'].iloc[0]
        return None
    except Exception as e:
        print(f"⚠️ YTD reference error for {ticker}: {e}")
        return None

def get_latest_price(ticker: str) -> Optional[float]:
    try:
        stock = yf.Ticker(ticker)
        fast = getattr(stock, "fast_info", {})
        last = fast.get("last_price")
        if last is not None:
            return last
        info_price = stock.info.get("regularMarketPrice")
        if info_price is not None:
            return info_price
        df = stock.history(period="7d", interval="1d", auto_adjust=False)
        if not df.empty:
            return df["Close"].iloc[-1]
        print(f"⚠️ No price data available for {ticker}")
        return None
    except Exception as e:
        print(f"⚠️ Price fetch error for {ticker}: {e}")
        return None

# ---- Main data fetching ----
def fetch_market_data() -> Optional[Dict[str, Any]]:
    cg = CoinGeckoAPI()
    utc_now = datetime.now(timezone.utc)
    sast_time = utc_now.astimezone(timezone(timedelta(hours=2)))

    if utc_now.hour == 3:
        report_time = sast_time.replace(hour=5, minute=0)
    elif utc_now.hour == 15:
        report_time = sast_time.replace(hour=17, minute=0)
    else:
        report_time = sast_time

    try:
        # Equity / FX / Commodities as before
        jse = None
        for tk in ["^J203.JO"]:
            price = get_latest_price(tk)
            if price:
                jse = price
                break
        if jse is None:
            print("⚠️ Could not fetch JSE All‑Share Index")
            return None

        zarusd = get_latest_price("ZAR=X")
        eurzar = get_latest_price("EURZAR=X")
        gbpzar = get_latest_price("GBPZAR=X")
        brent  = get_latest_price("BZ=F")
        gold   = get_latest_price("GC=F")
        sp500  = get_latest_price("^GSPC")

        # Prepare result structure
        result: Dict[str, Any] = {
            "timestamp": report_time.strftime("%Y-%m-%d %H:%M"),
            "JSEALSHARE": {
                "Today": jse,
                "Change": calculate_percentage(fetch_historical("^J203.JO",1), jse),
                "Monthly": calculate_percentage(fetch_historical("^J203.JO",30), jse),
                "YTD": calculate_percentage(get_ytd_reference_price("^J203.JO"), jse)
            },
            "USDZAR": {
                "Today": zarusd,
                "Change": calculate_percentage(fetch_historical("ZAR=X",1), zarusd),
                "Monthly": calculate_percentage(fetch_historical("ZAR=X",30), zarusd),
                "YTD": calculate_percentage(get_ytd_reference_price("ZAR=X"), zarusd)
            },
            "EURZAR": {
                "Today": eurzar,
                "Change": calculate_percentage(fetch_historical("EURZAR=X",1), eurzar),
                "Monthly": calculate_percentage(fetch_historical("EURZAR=X",30), eurzar),
                "YTD": calculate_percentage(get_ytd_reference_price("EURZAR=X"), eurzar)
            },
            "GBPZAR": {
                "Today": gbpzar,
                "Change": calculate_percentage(fetch_historical("GBPZAR=X",1), gbpzar),
                "Monthly": calculate_percentage(fetch_historical("GBPZAR=X",30), gbpzar),
                "YTD": calculate_percentage(get_ytd_reference_price("GBPZAR=X"), gbpzar)
            },
            "BRENT": {
                "Today": brent,
                "Change": calculate_percentage(fetch_historical("BZ=F",1), brent),
                "Monthly": calculate_percentage(fetch_historical("BZ=F",30), brent),
                "YTD": calculate_percentage(get_ytd_reference_price("BZ=F"), brent)
            },
            "GOLD": {
                "Today": gold,
                "Change": calculate_percentage(fetch_historical("GC=F",1), gold),
                "Monthly": calculate_percentage(fetch_historical("GC=F",30), gold),
                "YTD": calculate_percentage(get_ytd_reference_price("GC=F"), gold)
            },
            "SP500": {
                "Today": sp500,
                "Change": calculate_percentage(fetch_historical("^GSPC",1), sp500),
                "Monthly": calculate_percentage(fetch_historical("^GSPC",30), sp500),
                "YTD": calculate_percentage(get_ytd_reference_price("^GSPC"), sp500)
            }
        }

        # ---- Top 10 Cryptocurrencies ----
        crypto_ids = [
            "bitcoin", "ethereum", "binancecoin", "ripple", "cardano",
            "solana", "dogecoin", "polkadot", "tron", "litecoin"
        ]
        symbol_map = {
            "bitcoin": "BTC",  "ethereum": "ETH",  "binancecoin": "BNB",
            "ripple": "XRP",   "cardano": "ADA",   "solana": "SOL",
            "dogecoin": "DOGE","polkadot": "DOT","tron": "TRX",
            "litecoin": "LTC"
        }

        prices = cg.get_price(ids=','.join(crypto_ids), vs_currencies="zar")
        for coin in crypto_ids:
            name = symbol_map.get(coin, coin).upper()
            today = prices.get(coin, {}).get("zar")
            day_hist   = fetch_coin_historical(cg, coin, 1)
            month_hist = fetch_coin_historical(cg, coin, 30)
            ytd_hist   = get_coin_ytd_price(cg, coin)

            result[f"{name}ZAR"] = {
                "Today":   today,
                "Change":  calculate_percentage(day_hist, today),
                "Monthly": calculate_percentage(month_hist, today),
                "YTD":     calculate_percentage(ytd_hist, today)
            }

        return result

    except Exception as e:
        print(f"❌ Critical error in fetch_market_data: {e}")
        return None

if __name__ == "__main__":
    data = fetch_market_data()
    if data:
        print("🚀 Market data fetched successfully:")
        print(data)
    else:
        print("❌ Failed to fetch market data")
