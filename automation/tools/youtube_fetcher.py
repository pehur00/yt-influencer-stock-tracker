"""
YouTube Video Fetcher Tool
Fetches recent videos from YouTube channels using the YouTube Data API or web scraping.
"""

import os
import re
import json
import requests
from typing import Optional, List, Dict, Any
from datetime import datetime

try:
    from crewai.tools import tool
    CREWAI_AVAILABLE = True
except ImportError:
    CREWAI_AVAILABLE = False
    def tool(name):
        def decorator(func):
            return func
        return decorator


# Default channel for backwards compatibility
DEFAULT_CHANNEL_HANDLE = "@josephcarlsonshow"


def get_channel_videos_via_api(channel_id: str, max_results: int = 5) -> List[Dict[str, Any]]:
    """Fetch videos using YouTube Data API v3 (requires API key)."""
    api_key = os.getenv("YOUTUBE_API_KEY")
    if not api_key:
        return []
    
    # First get the uploads playlist ID
    channel_url = f"https://www.googleapis.com/youtube/v3/channels?part=contentDetails&id={channel_id}&key={api_key}"
    
    try:
        response = requests.get(channel_url, timeout=10)
        if response.status_code != 200:
            print(f"YouTube API error: {response.status_code}")
            return []
        
        data = response.json()
        if not data.get("items"):
            return []
        
        uploads_playlist_id = data["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
        
        # Get videos from uploads playlist
        videos_url = f"https://www.googleapis.com/youtube/v3/playlistItems?part=snippet&playlistId={uploads_playlist_id}&maxResults={max_results}&key={api_key}"
        
        response = requests.get(videos_url, timeout=10)
        if response.status_code != 200:
            return []
        
        videos_data = response.json()
        videos = []
        
        for item in videos_data.get("items", []):
            snippet = item.get("snippet", {})
            video_id = snippet.get("resourceId", {}).get("videoId", "")
            
            if video_id:
                videos.append({
                    "videoId": video_id,
                    "title": snippet.get("title", ""),
                    "publishedAt": snippet.get("publishedAt", "")[:10],  # YYYY-MM-DD
                    "thumbnail": f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg",
                    "description": snippet.get("description", "")[:500]
                })
        
        return videos
    except Exception as e:
        print(f"Error fetching from YouTube API: {e}")
        return []


def get_channel_videos_via_scraping(channel_handle: str, max_results: int = 5) -> List[Dict[str, Any]]:
    """Fetch videos by scraping the channel page (fallback method)."""
    try:
        # Try to get the channel videos page
        url = f"https://www.youtube.com/{channel_handle}/videos"
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9"
        }
        
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code != 200:
            print(f"Failed to fetch channel page: {response.status_code}")
            return []
        
        html = response.text
        
        # Extract video IDs from the page
        # YouTube embeds video data in a JSON structure
        video_id_pattern = r'"videoId":"([a-zA-Z0-9_-]{11})"'
        title_pattern = r'"title":\s*\{"runs":\s*\[\{"text":\s*"([^"]+)"\}'
        
        video_ids = re.findall(video_id_pattern, html)
        titles = re.findall(title_pattern, html)
        
        # Remove duplicates while preserving order
        seen_ids = set()
        unique_videos = []
        
        for vid_id in video_ids:
            if vid_id not in seen_ids and len(unique_videos) < max_results:
                seen_ids.add(vid_id)
                # Try to find a matching title
                title = titles[len(unique_videos)] if len(unique_videos) < len(titles) else f"Video {vid_id}"
                unique_videos.append({
                    "videoId": vid_id,
                    "title": title,
                    "publishedAt": datetime.now().strftime("%Y-%m-%d"),  # Approximate
                    "thumbnail": f"https://img.youtube.com/vi/{vid_id}/maxresdefault.jpg",
                    "description": ""
                })
        
        return unique_videos
    except Exception as e:
        print(f"Error scraping channel: {e}")
        return []


@tool("fetch_youtube_videos")
def fetch_youtube_videos(channel_handle: str = None, max_results: int = 5) -> str:
    """
    Fetches the most recent videos from a YouTube finance channel.
    Returns a JSON string with video IDs, titles, thumbnails, and descriptions.
    
    Args:
        channel_handle: YouTube channel handle (e.g., "@josephcarlsonshow"). Defaults to Joseph Carlson.
        max_results: Maximum number of videos to fetch (default 5)
    
    Returns:
        JSON string containing video metadata including real video IDs
    """
    if not channel_handle:
        channel_handle = DEFAULT_CHANNEL_HANDLE
    
    videos = []
    
    # Try scraping first (most reliable without API key)
    print(f"Fetching videos from {channel_handle}...")
    videos = get_channel_videos_via_scraping(channel_handle, max_results)
    
    if not videos:
        return json.dumps({
            "error": f"Could not fetch videos from {channel_handle}. Please check the channel handle.",
            "videos": []
        })
    
    return json.dumps({"videos": videos}, indent=2)


def get_video_tools():
    """Returns a list of YouTube video fetching tools."""
    if CREWAI_AVAILABLE:
        return [fetch_youtube_videos]
    return []


# For standalone testing
if __name__ == "__main__":
    print("Testing YouTube video fetcher...")
    result = fetch_youtube_videos(DEFAULT_CHANNEL_HANDLE, 5)
    print(result)
