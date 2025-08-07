from pycoingecko import CoinGeckoAPI
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any
import time
import pytz

def calculate_percentage(old: Optional[float], new: Optional[float]) -> float:
    """Calculate percentage change with null safety."""
    try:
        if old is None or new is None or old == 0:
            return 0.0
        return ((new - old) / abs(old)) * 100.0
    except Exception:
        return 0.0

def safe_cg_fetch(cg: CoinGeckoAPI, func, *args, max_retries: int = 3, delay: float = 1.0, **kwargs):
    """Wrapper with retry logic for CoinGecko API."""
    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)
        except Exception:
            if attempt == max_retries - 1:
                raise
            time.sleep(delay)
    return None

def get_coin_ytd_price(cg: CoinGeckoAPI, coin_id: str) -> Optional[float]:
    """Fetch the Jan 1 price of the current year for a given coin in ZAR."""
    try:
        year = datetime.now(timezone.utc).year
        start = datetime(year, 1, 1, tzinfo=timezone.utc)
        end = start + timedelta(days=2)  # 2-day window for reliability
        history = safe_cg_fetch(
            cg,
            cg.get_coin_market_chart_range_by_id,
            coin_id,
            "zar",
            int(start.timestamp()),
            int(end.timestamp())
        )
        prices = history.get("prices", []) if history else []
        # Get first valid price on or after Jan 1
        return next(
            (p[1] for p in prices
             if datetime.fromtimestamp(p[0] / 1000, tz=timezone.utc).date() >= start.date()),
            None
        )
    except Exception as e:
        print(f"⚠️ YTD error for {coin_id}: {e}")
        return None

def fetch_coin_historical(cg: CoinGeckoAPI, coin_id: str, days: int) -> Optional[float]:
    """Fetch historical coin price in ZAR for a given number of days ago."""
    try:
        target = datetime.now(timezone.utc) - timedelta(days=days)
        window = timedelta(hours=12)
        history = cg.get_coin_market_chart_range_by_id(
            coin_id,
            "zar",
            int((target - window).timestamp()),
            int((target + window).timestamp())
        )
        prices = history.get("prices", [])
        if prices:
            # Find price closest to target timestamp
            target_ts = target.timestamp() * 1000
            closest = min(prices, key=lambda x: abs(x[0] - target_ts))
            return closest[1]
        # fallback 3-day window
        target_date = target.date()
        start = datetime.combine(target_date - timedelta(days=1), datetime.min.time()).replace(tzinfo=timezone.utc)
        end = datetime.combine(target_date + timedelta(days=1), datetime.max.time()).replace(tzinfo=timezone.utc)
        history = safe_cg_fetch(
            cg,
            cg.get_coin_market_chart_range_by_id,
            coin_id,
            "zar",
            int(start.timestamp()),
            int(end.timestamp())
        )
        prices = history.get("prices", []) if history else []
        if not prices:
            return None
        target_ts = datetime.combine(target_date, datetime.min.time()).replace(tzinfo=timezone.utc).timestamp() * 1000
        return min(prices, key=lambda x: abs(x[0] - target_ts))[1]
    except Exception as e:
        print(f"⚠️ Historical error for {coin_id} at {days} days: {e}")
        return None

def fetch_market_data() -> Optional[Dict[str, Any]]:
    """Fetch top-10 cryptocurrencies in ZAR with Today, 1d, 30d and YTD metrics."""
    cg = CoinGeckoAPI()
    crypto_ids = {
        "bitcoin": "BTC",
        "ethereum": "ETH",
        "binancecoin": "BNB",
        "ripple": "XRP",
        "cardano": "ADA",
        "solana": "SOL",
        "dogecoin": "DOGE",
        "polkadot": "DOT",
        "tron": "TRX",
        "litecoin": "LTC",
    }

    try:
        prices = safe_cg_fetch(
            cg,
            cg.get_price,
            ids=",".join(crypto_ids.keys()),
            vs_currencies="zar"
        )
        if not prices:
            raise ValueError("No price data received")

        timestamp = datetime.now(pytz.timezone("Africa/Johannesburg")).strftime("%d %b %Y, %H:%M")
        result: Dict[str, Any] = {
            "timestamp": timestamp,
            "data_status": {}
        }

        for coin_id, symbol in crypto_ids.items():
            try:
                today = prices.get(coin_id, {}).get("zar")
                if today is None:
                    raise ValueError(f"No current price for {coin_id}")

                day_hist = fetch_coin_historical(cg, coin_id, 1)
                month_hist = fetch_coin_historical(cg, coin_id, 30)
                ytd_hist = get_coin_ytd_price(cg, coin_id)

                if not all(
                    isinstance(x, (float, int))
                    for x in [today, day_hist, month_hist, ytd_hist]
                    if x is not None
                ):
                    raise ValueError("Invalid price data type")

                result[f"{symbol}ZAR"] = {
                    "Today": float(today),
                    "Change": calculate_percentage(day_hist, today),
                    "Monthly": calculate_percentage(month_hist, today),
                    "YTD": calculate_percentage(ytd_hist, today) if ytd_hist else 0.0
                }
                result["data_status"][symbol] = "success"

            except Exception as e:
                print(f"⚠️ Error processing {coin_id}: {e}")
                result[f"{symbol}ZAR"] = {
                    "Today": 0.0,
                    "Change": 0.0,
                    "Monthly": 0.0,
                    "YTD": 0.0
                }
                result["data_status"][symbol] = f"failed: {e}"

        return result

    except Exception as e:
        print(f"❌ Critical error in fetch_market_data: {e}")
        return None

if __name__ == "__main__":
    data = fetch_market_data()
    if data:
        print("🚀 Crypto data fetched successfully:")
        print(f"Timestamp: {data['timestamp']}")
        for coin in ["BTC", "ETH", "BNB", "XRP", "ADA", "SOL", "DOGE", "DOT", "TRX", "LTC"]:
            if f"{coin}ZAR" in data:
                print(f"{coin}: {data[f'{coin}ZAR']}")
        print(f"Data Status: {data.get('data_status', 'unknown')}")
    else:
        print("❌ Failed to fetch crypto data")
