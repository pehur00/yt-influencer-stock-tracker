"""
Fetch recent videos from multiple YouTube channels.
This script uses yt-dlp Python API to get real video IDs and metadata,
then analyzes the content to extract stock tickers.

Supports multiple channels configured in config/channels.json
"""

import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

try:
    import yt_dlp
except ImportError:
    print("yt-dlp not installed. Install with: pip install yt-dlp")
    sys.exit(1)

# Paths
SCRIPT_DIR = Path(__file__).parent
CONFIG_FILE = SCRIPT_DIR / "config" / "channels.json"
OUTPUT_FILE = SCRIPT_DIR / "output" / "youtube_videos.json"
DATA_FILE = SCRIPT_DIR.parent / "data" / "youtube_videos.json"

# Common stock tickers to look for
KNOWN_TICKERS = {
    'AAPL', 'MSFT', 'GOOGL', 'GOOG', 'AMZN', 'META', 'NVDA', 'TSLA',
    'JPM', 'V', 'MA', 'JNJ', 'UNH', 'HD', 'PG', 'KO', 'PEP', 'MCD',
    'DIS', 'NFLX', 'ADBE', 'CRM', 'PYPL', 'INTC', 'AMD', 'QCOM',
    'T', 'VZ', 'CMCSA', 'NKE', 'SBUX', 'WMT', 'COST', 'TGT',
    'BA', 'CAT', 'GE', 'MMM', 'IBM', 'ORCL', 'CSCO', 'TXN',
    'O', 'SCHD', 'VTI', 'VOO', 'SPY', 'QQQ', 'VYM', 'JEPI',
    'SPGI', 'EFX', 'ASML', 'MELI', 'CMG', 'DUOL', 'CRWV',
    'BRK.A', 'BRK.B', 'WFC', 'BAC', 'GS', 'MS', 'C',
    'XOM', 'CVX', 'COP', 'SLB', 'EOG', 'MPC', 'PSX', 'VLO',
    'LMT', 'RTX', 'NOC', 'GD',
    'ABBV', 'MRK', 'PFE', 'LLY', 'BMY', 'GILD', 'AMGN',
    'NEE', 'DUK', 'SO', 'D', 'AEP', 'EXC', 'SRE',
    'AMT', 'PLD', 'CCI', 'EQIX', 'SPG', 'PSA', 'DLR',
    'NOW', 'SNOW', 'PLTR', 'DDOG', 'ZS', 'CRWD', 'NET',
}


def load_channel_config():
    """Load channel configuration from JSON file."""
    try:
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
            return config
    except FileNotFoundError:
        print(f"Config file not found: {CONFIG_FILE}")
        # Return default config with a sample channel
        return {
            "channels": [{
                "id": "joseph-carlson",
                "name": "The Joseph Carlson Show",
                "handle": "@josephcarlsonshow",
                "url": "https://www.youtube.com/@josephcarlsonshow/videos",
                "enabled": True
            }],
            "settings": {
                "maxVideosPerChannel": 5,
                "fetchDetails": True
            }
        }


def extract_tickers_from_text(text):
    """Extract stock tickers from text."""
    if not text:
        return []
    
    text_upper = text.upper()
    found = []
    
    # Look for known tickers
    for ticker in KNOWN_TICKERS:
        pattern = r'\b' + re.escape(ticker) + r'\b'
        if re.search(pattern, text_upper):
            found.append(ticker)
    
    # Also look for $TICKER patterns
    dollar_tickers = re.findall(r'\$([A-Z]{1,5})\b', text_upper)
    for t in dollar_tickers:
        if t not in found and len(t) >= 2:
            found.append(t)
    
    return list(set(found))


def analyze_title_for_buying(title):
    """
    Analyze title to determine if host explicitly says they're buying.
    This is a conservative check - only for explicit buying language.
    CrewAI transcript analysis will do the full sentiment analysis.
    """
    title_lower = title.lower()
    buying_keywords = ['buying', 'bought', "i'm buying", 'i bought', 'adding', 'added']
    return any(kw in title_lower for kw in buying_keywords)


def generate_summary_from_title(title, tickers, channel_name):
    """Generate a summary based on the video title and found tickers."""
    title_lower = title.lower()
    host = channel_name.split()[0] if channel_name else "The host"
    
    if 'buying' in title_lower or 'bought' in title_lower:
        if tickers:
            return f"{host} discusses stocks being bought, mentioning {', '.join(tickers[:3])}. Investment thesis and portfolio strategy shared."
        return f"{host} shares which stocks are being bought and the reasoning behind these investment decisions."
    
    if 'overvalued' in title_lower:
        return f"{host} analyzes current market valuations and discusses how to find value in an overvalued market."
    
    if 'portfolio' in title_lower:
        return f"{host} provides a portfolio update, discussing recent buys, sells, and overall investment strategy."
    
    if 'ai' in title_lower or 'artificial intelligence' in title_lower:
        return f"{host} covers AI-related investment opportunities and which companies may benefit from AI growth."
    
    if 'dividend' in title_lower:
        return f"{host} discusses dividend investing strategies and income-generating stocks."
    
    if tickers:
        return f"{host} analyzes {', '.join(tickers[:3])} and shares investment perspectives on these companies."
    
    return f"{host} shares market analysis and investment insights in this episode."


def fetch_video_details(video_id):
    """Fetch detailed info for a single video including description and upload date."""
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
        'ignoreerrors': True,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)
            if info:
                upload_date = info.get('upload_date', '')
                # Validate date format (YYYYMMDD)
                if upload_date and len(upload_date) == 8 and upload_date.isdigit():
                    # Sanity check: year should be 2020-2030
                    year = int(upload_date[:4])
                    if year < 2020 or year > 2030:
                        print(f"    Warning: suspicious date {upload_date} for {video_id}, will retry")
                        upload_date = ''
                
                return {
                    'description': info.get('description', ''),
                    'upload_date': upload_date,
                    'duration': info.get('duration', 0),
                    'channel': info.get('channel', ''),
                }
    except Exception as e:
        print(f"    Could not fetch details for {video_id}: {e}")
    
    return None


def fetch_channel_videos(channel, max_videos=5, fetch_details=True):
    """Fetch recent videos from a single YouTube channel."""
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': True,
        'playlistend': max_videos,
        'ignoreerrors': True,
    }

    channel_url = channel.get('url', '')
    channel_id = channel.get('id', 'unknown')
    channel_name = channel.get('name', 'Unknown Channel')

    if not channel_url:
        print(f"  No URL for channel: {channel_name}")
        return []

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(channel_url, download=False)

            if not info or 'entries' not in info:
                print(f"  Could not fetch video list from {channel_name}")
                return []

            videos = []
            for entry in info['entries'][:max_videos]:
                if entry:
                    video_id = entry.get('id', '')
                    title = entry.get('title', '')
                    
                    # Start with tickers from title
                    tickers_from_title = extract_tickers_from_text(title)
                    all_tickers = tickers_from_title.copy()
                    upload_date = None  # Will be set from video details
                    
                    # Always fetch details to get accurate upload date
                    if video_id:
                        print(f"    Fetching: {title[:45]}...")
                        details = fetch_video_details(video_id)
                        if details:
                            # Extract tickers from description
                            description = details.get('description', '')
                            desc_tickers = extract_tickers_from_text(description)
                            all_tickers = list(set(all_tickers + desc_tickers))
                            
                            # Parse upload date (format: YYYYMMDD -> YYYY-MM-DD)
                            ud = details.get('upload_date', '')
                            if ud and len(ud) == 8 and ud.isdigit():
                                upload_date = f"{ud[:4]}-{ud[4:6]}-{ud[6:8]}"
                                print(f"      Date: {upload_date}")
                    
                    # Fallback to today if no date found (shouldn't happen)
                    if not upload_date:
                        upload_date = datetime.now().strftime("%Y-%m-%d")
                        print(f"      Warning: Could not get upload date, using today")
                    
                    # Initial fetch: Don't make assumptions about sentiment from clickbait titles
                    # CrewAI will analyze the actual transcript to determine sentiment
                    is_buying = analyze_title_for_buying(title)
                    
                    # For initial fetch, be conservative:
                    # - Only mark as bought if title explicitly says "buying/bought"
                    # - Don't mark anything as recommended until CrewAI analyzes transcript
                    # - Set sentiment to "pending" for CrewAI to determine
                    tickers_bought = all_tickers[:2] if is_buying else []
                    
                    # Generate summary placeholder
                    summary = generate_summary_from_title(title, all_tickers, channel_name)
                    
                    # Generate insights
                    insights = []
                    if is_buying and tickers_bought:
                        insights.append(f"Title suggests buying {', '.join(tickers_bought)}")
                    if all_tickers:
                        insights.append(f"Stocks mentioned: {', '.join(all_tickers[:5])}")
                    insights.append("⏳ Awaiting transcript analysis for accurate sentiment")
                    
                    videos.append({
                        "videoId": video_id,
                        "title": title,
                        "publishedAt": upload_date,
                        "thumbnail": f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg",
                        "channelId": channel_id,
                        "channelName": channel_name,
                        "tickersMentioned": all_tickers,
                        "tickersBought": tickers_bought,
                        # Don't pre-populate recommended - let CrewAI determine from transcript
                        "tickersRecommended": [],
                        "tickersCautioned": [],
                        # Sentiment pending CrewAI transcript analysis
                        "sentiment": "pending",
                        "summary": summary,
                        "keyInsights": insights if insights else ["Watch for full analysis"]
                    })

            return videos

    except Exception as e:
        print(f"  Error fetching from {channel_name}: {e}")
        return []


def fetch_all_channels():
    """Fetch videos from all enabled channels."""
    config = load_channel_config()
    channels = config.get('channels', [])
    settings = config.get('settings', {})
    
    max_videos = settings.get('maxVideosPerChannel', 5)
    fetch_details = settings.get('fetchDetails', True)
    
    all_videos = []
    
    enabled_channels = [c for c in channels if c.get('enabled', False)]
    
    if not enabled_channels:
        print("No enabled channels found in config")
        return []
    
    print(f"Fetching from {len(enabled_channels)} channel(s)...")
    
    for channel in enabled_channels:
        channel_name = channel.get('name', 'Unknown')
        print(f"\n  [{channel_name}]")
        
        videos = fetch_channel_videos(channel, max_videos, fetch_details)
        
        if videos:
            print(f"    Found {len(videos)} videos")
            all_videos.extend(videos)
        else:
            print(f"    No videos found")
    
    # Sort by date (newest first)
    all_videos.sort(key=lambda v: v.get('publishedAt', ''), reverse=True)
    
    return all_videos


def fetch_recent_videos(max_videos=5, fetch_details=True):
    """
    Backward-compatible function for fetching videos.
    Uses the channel config to fetch from all enabled channels.
    """
    config = load_channel_config()
    settings = config.get('settings', {})
    settings['maxVideosPerChannel'] = max_videos
    settings['fetchDetails'] = fetch_details
    
    # Temporarily update settings
    config['settings'] = settings
    
    return fetch_all_channels()


def main():
    print("=" * 60)
    print("  YouTube Video Fetcher - Multi-Channel Support")
    print("=" * 60)
    
    videos = fetch_all_channels()

    if videos:
        print(f"\n{'=' * 60}")
        print(f"Total: {len(videos)} videos from all channels")
        print("=" * 60)
        
        # Group by channel for summary
        by_channel = {}
        for v in videos:
            ch = v.get('channelName', 'Unknown')
            if ch not in by_channel:
                by_channel[ch] = []
            by_channel[ch].append(v)
        
        for ch, vids in by_channel.items():
            print(f"\n{ch}:")
            for v in vids:
                print(f"  - {v['title'][:50]}... ({v['videoId']})")

        # Save to output file
        OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(OUTPUT_FILE, "w") as f:
            json.dump(videos, f, indent=2)
        print(f"\nSaved to {OUTPUT_FILE}")

        # Also copy to data folder
        DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(DATA_FILE, "w") as f:
            json.dump(videos, f, indent=2)
        print(f"Copied to {DATA_FILE}")
    else:
        print("\nNo videos found from any channel.")


if __name__ == "__main__":
    main()
