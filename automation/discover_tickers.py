"""
Ticker Discovery Module

Parses YouTube video data to discover new stock recommendations,
compares with currently tracked stocks, and adds new ones to the tracking list.
"""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Set, Tuple

# Import historical price fetcher
try:
    from tools.historical_prices import get_historical_price
except ImportError:
    # Fallback if run from different directory
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    from tools.historical_prices import get_historical_price

# Paths
SCRIPT_DIR = Path(__file__).parent
YOUTUBE_DATA_FILE = SCRIPT_DIR / "output" / "youtube_videos.json"
STOCKS_FILE = SCRIPT_DIR.parent / "data" / "stocks.json"
OUTPUT_STOCKS_FILE = SCRIPT_DIR / "output" / "stocks.json"


def load_youtube_videos() -> List[Dict]:
    """Load the fetched YouTube video data."""
    try:
        with open(YOUTUBE_DATA_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"YouTube data not found: {YOUTUBE_DATA_FILE}")
        return []


def load_current_stocks() -> List[Dict]:
    """Load the currently tracked stocks."""
    try:
        with open(STOCKS_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Stocks file not found: {STOCKS_FILE}")
        return []


def get_tracked_tickers(stocks: List[Dict]) -> Set[str]:
    """Get set of currently tracked ticker|source combinations."""
    tracked = set()
    for s in stocks:
        ticker = s.get('ticker', '').upper()
        source = s.get('source', 'Unknown')
        if ticker:
            tracked.add(f"{ticker}|{source}")
    return tracked


def extract_recommendations_from_videos(videos: List[Dict]) -> Dict[str, Dict]:
    """
    Extract all recommended/bought tickers from videos.
    Now returns per-channel entries: ticker|channel as key.
    
    Returns dict of "ticker|channel" -> {
        'ticker': ticker symbol,
        'channel': channel name,
        'firstMentioned': date string,
        'videos': [list of video titles],
        'isBought': bool,
        'isRecommended': bool,
        'mentionCount': int
    }
    """
    recommendations = {}
    
    for video in videos:
        channel_id = video.get('channelId', 'unknown')
        channel_name = video.get('channelName', 'Unknown Channel')
        video_date = video.get('publishedAt', datetime.now().strftime('%Y-%m-%d'))
        video_title = video.get('title', '')
        
        # Get tickers that were bought or recommended
        bought = set(video.get('tickersBought', []))
        recommended = set(video.get('tickersRecommended', []))
        
        # Combine - bought tickers are also considered recommended
        all_recommended = bought | recommended
        
        for ticker in all_recommended:
            ticker = ticker.upper()
            # Use ticker|channel as unique key
            rec_key = f"{ticker}|{channel_name}"
            
            if rec_key not in recommendations:
                recommendations[rec_key] = {
                    'ticker': ticker,
                    'channel': channel_name,
                    'channelId': channel_id,
                    'firstMentioned': video_date,
                    'videos': [],
                    'isBought': False,
                    'isRecommended': False,
                    'mentionCount': 0
                }
            
            rec = recommendations[rec_key]
            
            # Track videos
            if video_title not in rec['videos']:
                rec['videos'].append(video_title)
            
            # Update flags
            if ticker in bought:
                rec['isBought'] = True
            if ticker in recommended:
                rec['isRecommended'] = True
            
            # Track earliest mention
            if video_date < rec['firstMentioned']:
                rec['firstMentioned'] = video_date
            
            rec['mentionCount'] += 1
    
    return recommendations


def discover_new_tickers(
    videos: List[Dict] = None,
    current_stocks: List[Dict] = None
) -> Tuple[List[Dict], List[Dict]]:
    """
    Discover new tickers from YouTube videos that aren't currently tracked.
    
    Returns:
        (new_tickers, existing_updates)
        - new_tickers: List of new ticker recommendations to add
        - existing_updates: List of existing stocks with new source info
    """
    if videos is None:
        videos = load_youtube_videos()
    if current_stocks is None:
        current_stocks = load_current_stocks()
    
    tracked = get_tracked_tickers(current_stocks)  # Now returns ticker|source keys
    recommendations = extract_recommendations_from_videos(videos)
    
    new_tickers = []
    existing_updates = []
    
    for rec_key, rec in recommendations.items():
        if rec_key in tracked:
            # Already tracking this ticker+channel combo
            existing_updates.append(rec)
        else:
            # New ticker+channel combo - should we add it?
            # Only add if it was explicitly recommended or bought
            if rec['isBought'] or rec['isRecommended']:
                new_tickers.append(rec)
    
    # Sort by mention count (most mentioned first)
    new_tickers.sort(key=lambda x: x['mentionCount'], reverse=True)
    
    return new_tickers, existing_updates


def create_new_stock_entry(ticker_rec: Dict, fetch_historical: bool = True) -> Dict:
    """
    Create a new stock entry from a ticker recommendation.
    Uses placeholder values that will be filled by the analysis crew.
    Now creates one entry per channel (not combined).
    
    Args:
        ticker_rec: Ticker recommendation dict with ticker, channel, firstMentioned
        fetch_historical: If True, fetch historical price for recommendedDate
    """
    today = datetime.now().strftime('%Y-%m-%d')
    
    # Determine category based on common patterns
    # Most YouTube stock picks are growth stocks
    category = "Growth"
    
    # Source is now single channel (not combined)
    ticker = ticker_rec['ticker']
    source = ticker_rec.get('channel', 'Unknown')
    recommended_date = ticker_rec.get('firstMentioned', today)
    
    # Fetch historical price for the recommendation date
    initial_price = None
    if fetch_historical and recommended_date:
        print(f"    Fetching historical price for {ticker} on {recommended_date}...")
        initial_price = get_historical_price(ticker, recommended_date)
        if initial_price:
            print(f"    → ${initial_price}")
        else:
            print(f"    → Could not fetch, will use current price later")
        time.sleep(0.3)  # Rate limit
    
    return {
        "category": category,
        "ticker": ticker,
        "name": f"{ticker} (pending analysis)",  # Will be updated by crew
        "price": 0.0,  # Will be fetched by crew
        "initialPrice": initial_price,  # Historical price from recommendation date
        "recommendedDate": recommended_date,  # When this channel first recommended
        "dcf": {
            "conservative": "0-0",
            "base": "0-0",
            "aggressive": "0-0"
        },
        "fcfQuality": 3,
        "roicStrength": 3,
        "revenueDurability": 3,
        "balanceSheetStrength": 3,
        "insiderActivity": 3,
        "valueRank": 3,
        "expectedReturn": 3,
        "lastUpdated": today,
        "source": source,
        "sourceDetails": {
            "channelId": ticker_rec.get('channelId', ''),
            "firstMentioned": recommended_date,
            "videos": ticker_rec.get('videos', [])[:3],  # Keep first 3 videos
            "isBought": ticker_rec.get('isBought', False),
            "addedOn": today
        }
    }


def add_new_tickers_to_stocks(
    new_tickers: List[Dict],
    current_stocks: List[Dict] = None,
    max_to_add: int = 5
) -> Tuple[List[Dict], List[str]]:
    """
    Add new tickers to the stocks list.
    
    Args:
        new_tickers: List of new ticker recommendations
        current_stocks: Current stocks list (loaded if None)
        max_to_add: Maximum number of new stocks to add at once
    
    Returns:
        (updated_stocks, added_tickers)
    """
    if current_stocks is None:
        current_stocks = load_current_stocks()
    
    added_tickers = []
    
    for rec in new_tickers[:max_to_add]:
        new_stock = create_new_stock_entry(rec)
        current_stocks.append(new_stock)
        added_tickers.append(rec['ticker'])
    
    return current_stocks, added_tickers


def get_tickers_to_analyze(stocks: List[Dict] = None) -> List[str]:
    """
    Get list of all ticker symbols to analyze.
    """
    if stocks is None:
        stocks = load_current_stocks()
    
    return [s.get('ticker', '').upper() for s in stocks if s.get('ticker')]


def print_discovery_summary(new_tickers: List[Dict], existing_updates: List[Dict]):
    """Print a summary of discovered tickers."""
    print("\n" + "=" * 60)
    print("  Ticker Discovery Summary")
    print("=" * 60)
    
    if new_tickers:
        print(f"\n📈 NEW TICKER+CHANNEL COMBOS FOUND: {len(new_tickers)}")
        for rec in new_tickers:
            status = "🛒 BOUGHT" if rec['isBought'] else "👍 Recommended"
            channel = rec.get('channel', 'Unknown')
            print(f"  {rec['ticker']:6} @ {channel} - {status}")
            print(f"           First mentioned: {rec['firstMentioned']}")
    else:
        print("\n✅ No new ticker+channel combos found - all already tracked")
    
    if existing_updates:
        print(f"\n📊 EXISTING COMBOS MENTIONED: {len(existing_updates)}")
        for rec in existing_updates[:10]:  # Show top 10
            channel = rec.get('channel', 'Unknown')
            print(f"  {rec['ticker']:6} @ {channel} - {rec['mentionCount']}x")
    
    print()


def main():
    """Run ticker discovery as standalone script."""
    print("=" * 60)
    print("  Ticker Discovery - Finding New Stock Recommendations")
    print("=" * 60)
    
    # Load data
    videos = load_youtube_videos()
    current_stocks = load_current_stocks()
    
    if not videos:
        print("\nNo YouTube video data found. Run fetch_youtube_videos.py first.")
        return
    
    print(f"\nAnalyzing {len(videos)} videos...")
    print(f"Currently tracking {len(current_stocks)} stock entries (ticker+channel combos)")
    
    # Discover new tickers
    new_tickers, existing_updates = discover_new_tickers(videos, current_stocks)
    
    # Print summary
    print_discovery_summary(new_tickers, existing_updates)
    
    # Ask if we should add new tickers
    if new_tickers:
        print(f"Would add these {len(new_tickers)} new ticker+channel combo(s) to tracking:")
        for rec in new_tickers:
            print(f"  - {rec['ticker']} @ {rec.get('channel', 'Unknown')}")
        
        # In automated mode, we'll add them
        # For manual mode, you could add input() here
        updated_stocks, added = add_new_tickers_to_stocks(new_tickers, current_stocks)
        
        if added:
            # Save updated stocks
            OUTPUT_STOCKS_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(OUTPUT_STOCKS_FILE, 'w') as f:
                json.dump(updated_stocks, f, indent=2)
            print(f"\n✅ Added {len(added)} new entries: {', '.join(added)}")
            print(f"   Saved to: {OUTPUT_STOCKS_FILE}")
            print("\n   Run the full crew analysis to fetch prices and metrics.")


if __name__ == "__main__":
    main()
