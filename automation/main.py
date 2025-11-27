#!/usr/bin/env python3
"""
Main entry point for Stock Tracker automation.
Supports multiple YouTube channels and automatic ticker discovery.

Workflow:
1. Fetch latest videos from configured YouTube channels
2. Discover new stock recommendations from videos  
3. Add new tickers to tracking list
4. Run CrewAI analysis on all tracked stocks
5. Update website data files
"""

import os
import sys
import json
import shutil
import time
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Import historical price fetcher
try:
    from tools.historical_prices import get_historical_price
except ImportError:
    from automation.tools.historical_prices import get_historical_price

from fetch_youtube_videos import fetch_all_channels
from discover_tickers import (
    discover_new_tickers,
    add_new_tickers_to_stocks,
    print_discovery_summary,
    load_current_stocks,
    get_tickers_to_analyze
)
from crew_config import create_stock_tracker_crew

SCRIPT_DIR = Path(__file__).parent
OUTPUT_DIR = SCRIPT_DIR / "output"
DATA_DIR = SCRIPT_DIR.parent / "data"


def step_1_fetch_videos():
    """Step 1: Fetch videos from all enabled YouTube channels."""
    print("\n" + "=" * 70)
    print("  STEP 1: Fetching YouTube Videos")
    print("=" * 70)
    
    videos = fetch_all_channels()
    
    if videos:
        output_file = OUTPUT_DIR / "youtube_videos.json"
        output_file.parent.mkdir(exist_ok=True)
        with open(output_file, "w") as f:
            json.dump(videos, f, indent=2)
        
        data_file = DATA_DIR / "youtube_videos.json"
        data_file.parent.mkdir(exist_ok=True)
        with open(data_file, "w") as f:
            json.dump(videos, f, indent=2)
        
        by_channel = {}
        for v in videos:
            ch = v.get('channelName', 'Unknown')
            if ch not in by_channel:
                by_channel[ch] = []
            by_channel[ch].append(v)
        
        print(f"\n  Fetched {len(videos)} videos from {len(by_channel)} channel(s)")
        return videos
    else:
        print("  Warning: Could not fetch YouTube videos")
        return []


def step_2_discover_tickers(videos):
    """Step 2: Discover new stock recommendations from videos."""
    print("\n" + "=" * 70)
    print("  STEP 2: Discovering New Stock Recommendations")
    print("=" * 70)
    
    current_stocks = load_current_stocks()
    new_tickers, existing_updates = discover_new_tickers(videos, current_stocks)
    print_discovery_summary(new_tickers, existing_updates)
    return new_tickers, current_stocks


def step_3_add_new_tickers(new_tickers, current_stocks):
    """Step 3: Add new tickers to tracking list."""
    print("\n" + "=" * 70)
    print("  STEP 3: Adding New Tickers to Tracking")
    print("=" * 70)
    
    if not new_tickers:
        print("\n  No new tickers to add.")
        return current_stocks, []
    
    updated_stocks, added = add_new_tickers_to_stocks(new_tickers, current_stocks, max_to_add=5)
    
    if added:
        print(f"\n  Added {len(added)} new ticker(s): {', '.join(added)}")
        output_file = OUTPUT_DIR / "stocks.json"
        output_file.parent.mkdir(exist_ok=True)
        with open(output_file, "w") as f:
            json.dump(updated_stocks, f, indent=2)
        print(f"  Saved to: {output_file}")
    else:
        print("\n  No tickers added.")
    
    return updated_stocks, added


def step_4_run_analysis(stocks):
    """Step 4: Run CrewAI analysis on all tracked stocks."""
    print("\n" + "=" * 70)
    print("  STEP 4: Running Stock Analysis")
    print("=" * 70)
    
    tickers = get_tickers_to_analyze(stocks)
    
    if not tickers:
        print("\n  No stocks to analyze.")
        return False
    
    print(f"\n  Analyzing {len(tickers)} stocks: {', '.join(tickers[:10])}...")
    os.environ['CREW_TICKERS'] = ','.join(tickers)
    
    api_key = os.getenv('OPENROUTER_API_KEY', '')
    print(f"\n  Configuration:")
    print(f"    API Key: {'*' * 10 + api_key[-4:] if api_key else 'NOT SET'}")
    print(f"    Model: {os.getenv('CREW_MODEL', 'default')}")
    
    crew = create_stock_tracker_crew()
    crew.kickoff()
    return True


def step_5_finalize():
    """Step 5: Finalize and merge data to website."""
    print("\n" + "=" * 70)
    print("  STEP 5: Finalizing Data")
    print("=" * 70)
    
    output_file = OUTPUT_DIR / "stocks.json"
    website_data_file = DATA_DIR / "stocks.json"
    
    if not output_file.exists():
        print("\n  WARNING: output/stocks.json was not created.")
        return False
    
    today = datetime.utcnow().strftime("%Y-%m-%d")
    
    try:
        # Read crew output
        raw_text = output_file.read_text(encoding="utf-8").strip()
        if raw_text.startswith("```"):
            raw_text = raw_text.split("\n", 1)[1] if "\n" in raw_text else ""
        if raw_text.endswith("```"):
            raw_text = raw_text.rsplit("\n", 1)[0]
        
        crew_data = json.loads(raw_text)
        
        # Read existing website data (if any) to preserve stocks not in this run
        existing_data = []
        if website_data_file.exists():
            try:
                existing_data = json.load(open(website_data_file))
            except:
                pass
        
        # Build a map of existing stocks by ticker|source (unique key)
        def get_stock_key(s):
            ticker = s.get('ticker', '').upper()
            source = s.get('source', 'Unknown')
            return f"{ticker}|{source}"
        
        existing_by_key = {get_stock_key(s): s for s in existing_data}
        
        # Merge: crew output updates existing stocks but preserves important fields
        if isinstance(crew_data, list):
            for entry in crew_data:
                if isinstance(entry, dict):
                    ticker = entry.get('ticker', '').upper()
                    source = entry.get('source', 'Unknown')
                    stock_key = f"{ticker}|{source}"
                    
                    if ticker:
                        existing_stock = existing_by_key.get(stock_key, {})
                        
                        # Preserve these fields from existing data
                        preserved_fields = ['initialPrice', 'source', 'recommendedDate']
                        for field in preserved_fields:
                            if field in existing_stock and field not in entry:
                                entry[field] = existing_stock[field]
                        
                        # If no initialPrice exists, fetch historical price
                        if not entry.get('initialPrice'):
                            rec_date = entry.get('recommendedDate') or existing_stock.get('recommendedDate')
                            if rec_date and rec_date < today:
                                print(f"    Fetching historical price for {ticker} @ {rec_date}...")
                                hist_price = get_historical_price(ticker, rec_date)
                                if hist_price:
                                    entry['initialPrice'] = hist_price
                                    print(f"    → ${hist_price}")
                                else:
                                    # Fallback to current price
                                    entry['initialPrice'] = entry.get('price')
                                    print(f"    → Using current price ${entry.get('price')}")
                                time.sleep(0.3)
                            elif entry.get('price'):
                                # No historical date, use current price
                                entry['initialPrice'] = entry['price']
                        
                        entry['lastUpdated'] = today
                        existing_by_key[stock_key] = entry
        
        # Convert back to list
        merged_data = list(existing_by_key.values())
        
        # Sort by ticker then source for consistency
        merged_data.sort(key=lambda x: (x.get('ticker', ''), x.get('source', '')))
        
        # Write merged output
        output_file.write_text(json.dumps(merged_data, indent=2) + "\n", encoding="utf-8")
        
        # Copy to website data folder
        website_data_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(output_file, website_data_file)
        print(f"  Merged and copied stocks.json to {website_data_file}")
        print(f"  Total stocks: {len(merged_data)}")
        return True
        
    except Exception as e:
        print(f"  ERROR: Could not finalize data ({e})")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main execution function."""
    load_dotenv()
    
    if not os.getenv("OPENROUTER_API_KEY"):
        print("ERROR: OPENROUTER_API_KEY not found.")
        print("Please set it in your .env file.")
        sys.exit(1)
    
    print("=" * 70)
    print("  Stock Tracker - Multi-Channel Automated Update")
    print("=" * 70)
    
    try:
        videos = step_1_fetch_videos()
        new_tickers, current_stocks = step_2_discover_tickers(videos)
        updated_stocks, added_tickers = step_3_add_new_tickers(new_tickers, current_stocks)
        step_4_run_analysis(updated_stocks)
        step_5_finalize()
        
        print("\n" + "=" * 70)
        print("  SUCCESS! Stock data has been updated.")
        print("=" * 70)
        
        if added_tickers:
            print(f"\nNew stocks added: {', '.join(added_tickers)}")
        
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
