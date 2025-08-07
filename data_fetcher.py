from pycoingecko import CoinGeckoAPI
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any
import time
import requests
from functools import wraps

# Timeout configuration
REQUEST_TIMEOUT = 10  # seconds
MAX_RETRIES = 2
RETRY_DELAY = 1

def timeout_retry(max_retries=MAX_RETRIES, delay=RETRY_DELAY, timeout=REQUEST_TIMEOUT):
    """Decorator for API calls with timeout and retry logic."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(max_retries):
                try:
                    # Add timeout to requests
                    if 'timeout' not in kwargs:
                        kwargs['timeout'] = timeout
                    return func(*args, **kwargs)
                except (requests.exceptions.RequestException, Exception) as e:
                    last_error = e
                    if attempt < max_retries - 1:
                        time.sleep(delay)
            print(f"❌ Failed after {max_retries} attempts: {str(last_error)}")
            return None
        return wrapper
    return decorator

@timeout_retry()
def safe_cg_request(cg, method, *args, **kwargs):
    """Safe wrapper for CoinGecko API calls."""
    return method(*args, **kwargs)

def calculate_percentage(old: Optional[float], new: Optional[float]) -> float:
    """Calculate percentage change with null safety."""
    if None in (old, new) or old == 0:
        return 0.0
    try:
        return ((new - old) / old) * 100
    except Exception:
        return 0.0

@timeout_retry()
def get_coin_ytd_price(cg: CoinGeckoAPI, coin_id: str) -> Optional[float]:
    """Fetch the Jan 1 price of the current year for a given coin in ZAR."""
    try:
        year = datetime.now(timezone.utc).year
        start = datetime(year, 1, 1, tzinfo=timezone.utc)
        end = start + timedelta(days=1)
        history = safe_cg_request(cg, cg.get_coin_market_chart_range_by_id,
                                coin_id, "zar",
                                int(start.timestamp()), int(end.timestamp()))
        prices = history.get('prices', []) if history else []
        return prices[0][1] if prices else None
    except Exception as e:
        print(f"⚠️ YTD error for {coin_id}: {e}")
        return None

@timeout_retry()
def fetch_coin_historical(cg: CoinGeckoAPI, coin_id: str, days: int) -> Optional[float]:
    """Fetch historical coin price in ZAR with timeout."""
    try:
        target = datetime.now(timezone.utc) - timedelta(days=days)
        window = timedelta(hours=12)
        history = safe_cg_request(cg, cg.get_coin_market_chart_range_by_id,
                                coin_id, "zar",
                                int((target - window).timestamp()), 
                                int((target + window).timestamp()))
        if not history:
            return None
        prices = history.get("prices", [])
        if not prices:
            return None
        target_ts = target.timestamp() * 1000
        closest = min(prices, key=lambda x: abs(x[0] - target_ts))
        return closest[1]
    except Exception as e:
        print(f"⚠️ Historical error for {coin_id} at {days} days: {e}")
        return None

def fetch_market_data() -> Optional[Dict[str, Any]]:
    """Fetch crypto data with comprehensive timeout protection."""
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
        # Get current prices with timeout
        prices = safe_cg_request(cg, cg.get_price,
                               ids=','.join(crypto_ids.keys()),
                               vs_currencies="zar")
        if not prices:
            raise ValueError("No price data received")

        result: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
            "data_status": {}
        }

        for coin_id, symbol in crypto_ids.items():
            try:
                start_time = time.time()
                today = prices.get(coin_id, {}).get("zar")
                if today is None:
                    raise ValueError(f"No price for {symbol}")
                
                day_hist = fetch_coin_historical(cg, coin_id, 1)
                month_hist = fetch_coin_historical(cg, coin_id, 30)
                ytd_hist = get_coin_ytd_price(cg, coin_id)

                # Timeout check
                if time.time() - start_time > 30:  # 30s max per coin
                    raise TimeoutError(f"Timeout processing {symbol}")
                
                result[f"{symbol}ZAR"] = {
                    "Today": float(today),
                    "Change": calculate_percentage(day_hist, today),
                    "Monthly": calculate_percentage(month_hist, today),
                    "YTD": calculate_percentage(ytd_hist, today) if ytd_hist else 0.0
                }
                result["data_status"][symbol] = "success"

            except Exception as e:
                print(f"⚠️ Error processing {symbol}: {e}")
                result[f"{symbol}ZAR"] = {
                    "Today": 0.0,
                    "Change": 0.0,
                    "Monthly": 0.0,
                    "YTD": 0.0
                }
                result["data_status"][symbol] = f"error: {str(e)}"

        return result

    except Exception as e:
        print(f"❌ Critical error: {e}")
        return None

if __name__ == "__main__":
    start = time.time()
    print("⏳ Fetching crypto data...")
    
    data = fetch_market_data()
    
    if data:
        print(f"✅ Data fetched in {time.time()-start:.1f}s")
        print(f"Timestamp: {data['timestamp']}")
        for coin in ["BTC", "ETH", "BNB"]:  # Display only major coins
            if f"{coin}ZAR" in data:
                print(f"{coin}: {data[f'{coin}ZAR']}")
    else:
        print("❌ Failed to fetch data")
