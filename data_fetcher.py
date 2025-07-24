from pycoingecko import CoinGeckoAPI
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any


def calculate_percentage(old: Optional[float], new: Optional[float]) -> float:
    """Calculate percentage change with null safety."""
    if None in (old, new) or old == 0:
        return 0.0
    try:
        return ((new - old) / old) * 100
    except Exception:
        return 0.0


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
    except Exception as e:
        print(f"⚠️ YTD error for {coin_id}: {e}")
        return None


def fetch_coin_historical(cg: CoinGeckoAPI, coin_id: str, days: int) -> Optional[float]:
    """Fetch historical coin price in ZAR for a given number of days ago."""
    try:
        target = datetime.now(timezone.utc) - timedelta(days=days)
        window = timedelta(hours=12)
        history = cg.get_coin_market_chart_range_by_id(
            coin_id, "zar",
            int((target - window).timestamp()), int((target + window).timestamp())
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
        # Current prices
        prices = cg.get_price(ids=','.join(crypto_ids.keys()), vs_currencies="zar")

        result: Dict[str, Any] = {"timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")}
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

        return result

    except Exception as e:
        print(f"❌ Critical error in fetch_market_data: {e}")
        return None


if __name__ == "__main__":
    data = fetch_market_data()
    if data:
        print("🚀 Crypto data fetched successfully:")
        print(data)
    else:
        print("❌ Failed to fetch crypto data")
