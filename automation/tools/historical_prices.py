"""
Historical Price Fetcher

Fetches historical stock prices from Yahoo Finance for a given date.
Used to set accurate initialPrice when a stock is first recommended.
"""

import json
import urllib.request
import time
from datetime import datetime, timedelta
from typing import Optional


def get_historical_price(ticker: str, date_str: str, max_retries: int = 2) -> Optional[float]:
    """
    Fetch the closing price for a stock on a specific date.
    
    Args:
        ticker: Stock ticker symbol (e.g., 'COST', 'NVDA')
        date_str: Date in YYYY-MM-DD format
        max_retries: Number of retry attempts
        
    Returns:
        Closing price as float, or None if not found
    """
    for attempt in range(max_retries):
        try:
            # Parse date and create range (handle weekends/holidays)
            dt = datetime.strptime(date_str, '%Y-%m-%d')
            start = int((dt - timedelta(days=5)).timestamp())
            end = int((dt + timedelta(days=2)).timestamp())
            
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?period1={start}&period2={end}&interval=1d"
            headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'}
            req = urllib.request.Request(url, headers=headers)
            
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode())
            
            result = data.get('chart', {}).get('result', [])
            if not result:
                return None
                
            quotes = result[0].get('indicators', {}).get('quote', [])
            if not quotes:
                return None
                
            closes = quotes[0].get('close', [])
            timestamps = result[0].get('timestamp', [])
            
            if not timestamps or not closes:
                return None
            
            # Find the closest trading day to our target date
            target_ts = dt.timestamp()
            best_idx = None
            best_diff = float('inf')
            
            for i, ts in enumerate(timestamps):
                if closes[i] is not None:  # Only consider days with valid prices
                    diff = abs(ts - target_ts)
                    if diff < best_diff:
                        best_diff = diff
                        best_idx = i
            
            if best_idx is not None and closes[best_idx] is not None:
                return round(closes[best_idx], 2)
                
            return None
            
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(0.5)
            else:
                print(f"  Error fetching {ticker} for {date_str}: {e}")
                return None
    
    return None


def get_current_price(ticker: str) -> Optional[float]:
    """
    Fetch the current/latest price for a stock.
    
    Args:
        ticker: Stock ticker symbol
        
    Returns:
        Current price as float, or None if not found
    """
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d&range=1d"
        headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'}
        req = urllib.request.Request(url, headers=headers)
        
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())
        
        result = data.get('chart', {}).get('result', [])
        if result:
            meta = result[0].get('meta', {})
            price = meta.get('regularMarketPrice')
            if price:
                return round(price, 2)
        return None
        
    except Exception as e:
        print(f"  Error fetching current price for {ticker}: {e}")
        return None


def batch_get_historical_prices(ticker_dates: list, delay: float = 0.3) -> dict:
    """
    Fetch historical prices for multiple ticker/date combinations.
    
    Args:
        ticker_dates: List of (ticker, date_str) tuples
        delay: Delay between requests to avoid rate limiting
        
    Returns:
        Dict mapping (ticker, date) to price
    """
    results = {}
    
    for ticker, date_str in ticker_dates:
        price = get_historical_price(ticker, date_str)
        results[(ticker, date_str)] = price
        time.sleep(delay)
    
    return results


if __name__ == "__main__":
    # Test the module
    print("Testing historical price fetcher...")
    
    test_cases = [
        ("COST", "2025-09-19"),
        ("NVDA", "2025-11-26"),
        ("AMD", "2025-11-25"),
    ]
    
    for ticker, date in test_cases:
        price = get_historical_price(ticker, date)
        print(f"  {ticker} on {date}: ${price}")
