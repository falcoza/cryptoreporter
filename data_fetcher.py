from pycoingecko import CoinGeckoAPI
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any
import time
import concurrent.futures
import signal
from functools import partial

# Configuration
REQUEST_TIMEOUT = 15  # seconds per API call
TOTAL_TIMEOUT = 60  # seconds for entire operation
MAX_RETRIES = 3
RETRY_DELAY = 1
MAX_WORKERS = 4  # concurrent API calls

class TimeoutError(Exception):
    pass

def timeout_handler(signum, frame):
    raise TimeoutError("Operation timed out")

def with_retry(max_retries=MAX_RETRIES, delay=RETRY_DELAY):
    """Decorator for retry logic with exponential backoff"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    if attempt < max_retries - 1:
                        time.sleep(delay * (attempt + 1))
            raise last_error
        return wrapper
    return decorator

def calculate_percentage(old: Optional[float], new: Optional[float]) -> float:
    """Safely calculate percentage change with absolute denominator."""
    try:
        if None in (old, new) or old == 0:
            return 0.0
        return ((new - old) / abs(old)) * 100
    except Exception:
        return 0.0

@with_retry()
def get_coin_ytd_price(cg: CoinGeckoAPI, coin_id: str) -> Optional[float]:
    """Fetch YTD price with wider window and validation."""
    try:
        year = datetime.now(timezone.utc).year
        start = datetime(year, 1, 1, tzinfo=timezone.utc)
        end = start + timedelta(days=2)  # 2-day window
        history = cg.get_coin_market_chart_range_by_id(
            coin_id, "zar",
            int(start.timestamp()), int(end.timestamp()),
            timeout=REQUEST_TIMEOUT
        )
        prices = history.get('prices', [])
        return next((p[1] for p in prices 
                   if datetime.fromtimestamp(p[0]/1000).date() >= start.date()), None)
    except Exception as e:
        print(f"⚠️ YTD error for {coin_id}: {str(e)[:100]}")
        return None

@with_retry()
def fetch_coin_historical(cg: CoinGeckoAPI, coin_id: str, days: int) -> Optional[float]:
    """Fetch historical price with adaptive time windows."""
    try:
        target = datetime.now(timezone.utc) - timedelta(days=days)
        window = timedelta(minutes=30) if days == 1 else timedelta(hours=12)
        
        history = cg.get_coin_market_chart_range_by_id(
            coin_id, "zar",
            int((target - window).timestamp()),
            int((target + window).timestamp()),
            timeout=REQUEST_TIMEOUT
        )
        
        if not history:
            return None
            
        prices = history.get("prices", [])
        if not prices:
            return None
            
        target_ts = target.timestamp() * 1000
        closest = min(prices, key=lambda x: abs(x[0] - target_ts))
        return closest[1]
    except Exception as e:
        print(f"⚠️ Historical error for {coin_id} at {days}d: {str(e)[:100]}")
        return None

def fetch_coin_data(cg: CoinGeckoAPI, coin_id: str, symbol: str, prices: Dict) -> Dict:
    """Process a single coin's data with timeout protection."""
    try:
        today = prices.get(coin_id, {}).get("zar")
        if today is None:
            raise ValueError("Missing current price")
            
        day_hist = fetch_coin_historical(cg, coin_id, 1)
        month_hist = fetch_coin_historical(cg, coin_id, 30)
        ytd_hist = get_coin_ytd_price(cg, coin_id)

        return {
            "symbol": symbol,
            "data": {
                "Today": float(today),
                "Change": calculate_percentage(day_hist, today),
                "Monthly": calculate_percentage(month_hist, today),
                "YTD": calculate_percentage(ytd_hist, today) if ytd_hist else 0.0
            },
            "status": "success"
        }
    except Exception as e:
        print(f"⚠️ Processing error for {symbol}: {str(e)[:100]}")
        return {
            "symbol": symbol,
            "data": {
                "Today": 0.0,
                "Change": 0.0,
                "Monthly": 0.0,
                "YTD": 0.0
            },
            "status": f"error: {str(e)[:100]}"
        }

def fetch_market_data() -> Optional[Dict[str, Any]]:
    """Main function with complete timeout protection."""
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(TOTAL_TIMEOUT)
    
    try:
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

        # Get current prices with retry
        prices = None
        for attempt in range(MAX_RETRIES):
            try:
                prices = cg.get_price(
                    ids=','.join(crypto_ids.keys()),
                    vs_currencies="zar",
                    timeout=REQUEST_TIMEOUT
                )
                if prices:
                    break
            except Exception as e:
                if attempt == MAX_RETRIES - 1:
                    raise
                time.sleep(RETRY_DELAY * (attempt + 1))

        if not prices:
            raise ValueError("Failed to fetch prices after retries")

        result = {
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
            "data_status": {}
        }

        # Process coins in parallel with thread pool
        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = [
                executor.submit(
                    partial(fetch_coin_data, cg, coin_id, symbol, prices)
                )
                for coin_id, symbol in crypto_ids.items()
            ]
            
            for future in concurrent.futures.as_completed(futures, timeout=TOTAL_TIMEOUT):
                coin_result = future.result()
                result[f"{coin_result['symbol']}ZAR"] = coin_result["data"]
                result["data_status"][coin_result["symbol"]] = coin_result["status"]

        return result

    except TimeoutError:
        print(f"⏱️ Operation timed out after {TOTAL_TIMEOUT}s")
        return None
    except Exception as e:
        print(f"❌ Critical error: {str(e)[:100]}")
        return None
    finally:
        signal.alarm(0)  # Disable alarm

if __name__ == "__main__":
    print("🚀 Starting crypto data fetch...")
    start_time = time.time()
    
    data = fetch_market_data()
    
    if data:
        print(f"✅ Success in {time.time()-start_time:.1f}s")
        print(f"Timestamp: {data['timestamp']}")
        for coin in ["BTC", "ETH", "BNB"]:  # Show major coins
            if f"{coin}ZAR" in data:
                print(f"{coin}: {data[f'{coin}ZAR']}")
    else:
        print("❌ Failed to fetch data")
