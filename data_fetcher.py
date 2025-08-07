from pycoingecko import CoinGeckoAPI
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any

import time
import pytz

def calculate_percentage(old: Optional[float], new: Optional[float]) -> float:
"""Calculate percentage change with null safety."""
@@ -12,44 +13,58 @@ def calculate_percentage(old: Optional[float], new: Optional[float]) -> float:
except Exception:
return 0.0

def safe_cg_fetch(cg, func, *args, max_retries=3, delay=1, **kwargs):
    """Wrapper with retry logic for CoinGecko API"""
    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            time.sleep(delay)
    return None

def get_coin_ytd_price(cg: CoinGeckoAPI, coin_id: str) -> Optional[float]:
"""Fetch the Jan 1 price of the current year for a given coin in ZAR."""
try:
year = datetime.now(timezone.utc).year
start = datetime(year, 1, 1, tzinfo=timezone.utc)
        end = start + timedelta(days=1)
        history = cg.get_coin_market_chart_range_by_id(
            coin_id, "zar",
            int(start.timestamp()), int(end.timestamp())
        )
        prices = history.get('prices', [])
        return prices[0][1] if prices else None
        end = start + timedelta(days=2)  # 2-day window for reliability
        history = safe_cg_fetch(cg, cg.get_coin_market_chart_range_by_id,
                              coin_id, "zar",
                              int(start.timestamp()), int(end.timestamp()))
        
        if not history or not history.get('prices'):
            return None
            
        # Get first valid price in the year
        return next((p[1] for p in history['prices'] 
                   if datetime.fromtimestamp(p[0]/1000, tz=timezone.utc).date() >= start.date()), None)
except Exception as e:
print(f"⚠️ YTD error for {coin_id}: {e}")
return None


def fetch_coin_historical(cg: CoinGeckoAPI, coin_id: str, days: int) -> Optional[float]:
    """Fetch historical coin price in ZAR for a given number of days ago."""
    """Fetch historical coin price in ZAR with 3-day window for reliability."""
try:
        target = datetime.now(timezone.utc) - timedelta(days=days)
        window = timedelta(hours=12)
        history = cg.get_coin_market_chart_range_by_id(
            coin_id, "zar",
            int((target - window).timestamp()), int((target + window).timestamp())
        )
        prices = history.get("prices", [])
        if not prices:
        target_date = (datetime.now(timezone.utc) - timedelta(days=days)).date()
        start = datetime.combine(target_date - timedelta(days=1), datetime.min.time()).replace(tzinfo=timezone.utc)
        end = datetime.combine(target_date + timedelta(days=1), datetime.max.time()).replace(tzinfo=timezone.utc)
        
        history = safe_cg_fetch(cg, cg.get_coin_market_chart_range_by_id,
                              coin_id, "zar",
                              int(start.timestamp()), int(end.timestamp()))
        
        if not history or not history.get("prices"):
return None
        target_ts = target.timestamp() * 1000
        closest = min(prices, key=lambda x: abs(x[0] - target_ts))
        return closest[1]
            
        # Find closest price to target date
        target_ts = datetime.combine(target_date, datetime.min.time()).replace(tzinfo=timezone.utc).timestamp() * 1000
        return min(history['prices'], key=lambda x: abs(x[0] - target_ts))[1]
except Exception as e:
print(f"⚠️ Historical error for {coin_id} at {days} days: {e}")
return None


def fetch_market_data() -> Optional[Dict[str, Any]]:
"""Fetch top-10 cryptocurrencies in ZAR with Today, 1d, 30d and YTD metrics."""
cg = CoinGeckoAPI()
@@ -65,35 +80,66 @@ def fetch_market_data() -> Optional[Dict[str, Any]]:
"tron": "TRX",
"litecoin": "LTC",
}
    
try:
        # Current prices
        prices = cg.get_price(ids=','.join(crypto_ids.keys()), vs_currencies="zar")
        # Current prices with retry logic
        prices = safe_cg_fetch(cg, cg.get_price, 
                             ids=','.join(crypto_ids.keys()), 
                             vs_currencies="zar")
        if not prices:
            raise ValueError("No price data received")

        result: Dict[str, Any] = {"timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")}
        result: Dict[str, Any] = {
            "timestamp": datetime.now(pytz.timezone("Africa/Johannesburg")).strftime("%d %b %Y, %H:%M"),
            "data_status": {}
        }
        
for coin_id, symbol in crypto_ids.items():
            today = prices.get(coin_id, {}).get("zar")
            day_hist = fetch_coin_historical(cg, coin_id, 1)
            month_hist = fetch_coin_historical(cg, coin_id, 30)
            ytd_hist = get_coin_ytd_price(cg, coin_id)

            result[f"{symbol}ZAR"] = {
                "Today":    today,
                "Change":   calculate_percentage(day_hist, today),
                "Monthly":  calculate_percentage(month_hist, today),
                "YTD":      calculate_percentage(ytd_hist, today)
            }
            try:
                today = prices.get(coin_id, {}).get("zar")
                if not today:
                    raise ValueError(f"No current price for {coin_id}")
                
                day_hist = fetch_coin_historical(cg, coin_id, 1)
                month_hist = fetch_coin_historical(cg, coin_id, 30)
                ytd_hist = get_coin_ytd_price(cg, coin_id)
                
                # Validate data quality
                if not all(isinstance(x, (float, int)) for x in [today, day_hist, month_hist, ytd_hist] if x is not None):
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
                result["data_status"][symbol] = f"failed: {str(e)}"

return result

except Exception as e:
print(f"❌ Critical error in fetch_market_data: {e}")
return None


if __name__ == "__main__":
data = fetch_market_data()
if data:
print("🚀 Crypto data fetched successfully:")
        print(data)
        print(f"Timestamp: {data['timestamp']}")
        for coin in ["BTC", "ETH", "BNB", "XRP", "ADA", "SOL", "DOGE", "DOT", "TRX", "LTC"]:
            if f"{coin}ZAR" in data:
                print(f"{coin}: {data[f'{coin}ZAR']}")
        print(f"Data Status: {data.get('data_status', 'unknown')}")
else:
print("❌ Failed to fetch crypto data")
