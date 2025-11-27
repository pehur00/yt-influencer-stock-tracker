"""
Crew Configuration for YouTube Influencer Stock Tracker
Orchestrates agents to fetch, analyze, and format stock data from multiple channels.
"""

import os
import json
from datetime import datetime
from crewai import Crew, Task, Process, LLM
from agents.data_fetcher_agent import create_data_fetcher_agent
from agents.analyst_agent import create_analyst_agent
from agents.formatter_agent import create_formatter_agent
from agents.youtube_agent import create_youtube_agent
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def load_prefetched_youtube_data():
    """Load pre-fetched YouTube video data from file with full details."""
    try:
        with open("output/youtube_videos.json", "r") as f:
            videos = json.load(f)
            # Enrich with URLs
            for v in videos:
                v['url'] = f"https://www.youtube.com/watch?v={v.get('videoId', '')}"
            return videos
    except Exception as e:
        print(f"Warning: Could not load pre-fetched YouTube data: {e}")
        return None


# Default tickers (fallback if none provided)
DEFAULT_TICKERS = [
    "DUOL", "CMG", "ADBE", "MELI", "CRWV",
    "CRM", "SPGI", "EFX", "NFLX", "ASML", "MA"
]


def get_tickers():
    """Get tickers to analyze - reads from environment at call time."""
    tickers_env = os.getenv("CREW_TICKERS", os.getenv("TICKERS"))
    if tickers_env:
        parsed = [t.strip().upper() for t in tickers_env.split(",") if t.strip()]
        return parsed or DEFAULT_TICKERS
    return DEFAULT_TICKERS


def create_stock_tracker_crew():
    """Creates and configures the stock tracker crew."""

    # Initialize LLM using OpenRouter
    # Get API key and model from environment
    api_key = os.getenv("OPENROUTER_API_KEY")
    model = (
        os.getenv("CREW_MODEL")
        or os.getenv("OPENROUTER_MODEL")
        or "google/gemini-2.0-flash-001"
    )

    if not api_key:
        raise ValueError(
            "OPENROUTER_API_KEY not found in environment variables. "
            "Please set it in your .env file or environment."
        )

    # CrewAI's LLM wrapper needs an explicit provider prefix
    llm_model = model if model.startswith("openrouter/") else f"openrouter/{model}"

    llm = LLM(
        model=llm_model,
        api_key=api_key,
        api_base="https://openrouter.ai/api/v1",
        temperature=0.1,
    )

    # Create agents
    data_fetcher = create_data_fetcher_agent(llm)
    analyst = create_analyst_agent(llm)
    formatter = create_formatter_agent(llm)
    youtube_researcher = create_youtube_agent(llm)

    # Load pre-fetched YouTube video data with URLs
    prefetched_videos = load_prefetched_youtube_data()
    
    # Build detailed video info for the task - includes pre-extracted tickers
    if prefetched_videos:
        video_details = []
        for i, v in enumerate(prefetched_videos[:5]):
            video_details.append(f"""
Video {i+1}:
  Title: "{v.get('title', '')}"
  Video ID: {v.get('videoId', '')}
  URL: {v.get('url', '')}
  Date: {v.get('publishedAt', '')}
  Pre-extracted tickers: {', '.join(v.get('tickersMentioned', [])) or 'None found'}
  Pre-extracted bought: {', '.join(v.get('tickersBought', [])) or 'None found'}
  Initial summary: {v.get('summary', '')}
  Initial insights: {v.get('keyInsights', [])}""")
        video_list = "\n".join(video_details)
    else:
        video_list = "No pre-fetched videos available."

    # Define tasks
    youtube_task = Task(
        description=f"""Analyze the following YouTube videos from finance influencers.

        I've already extracted some initial data from video titles and descriptions.
        Your job is to use your YoutubeVideoSearchTool to search within each video's 
        actual transcript/content and ENHANCE the analysis with better summaries and 
        any additional tickers or insights.

        PRE-FETCHED VIDEO DATA:
        {video_list}

        For EACH video:
        1. Use YoutubeVideoSearchTool with the video URL to search for stock mentions
        2. Search queries to try: "bought buying", "recommend", ticker symbols
        3. Compare what you find with the pre-extracted data
        4. Create an enhanced summary that's more detailed and insightful
        5. Add any additional tickers or insights you discover

        Return for each video:
        - videoId (KEEP EXACTLY AS PROVIDED)
        - title (keep as provided)
        - tickersMentioned (combine pre-extracted + any new ones you find)
        - tickersBought (stocks he explicitly says he bought)
        - tickersRecommended (stocks he recommends)
        - summary (YOUR enhanced 2-3 sentence summary - make it more specific)
        - keyInsights (YOUR enhanced list of 2-3 actionable insights)

        Focus on making the summaries and insights more specific and valuable than 
        the generic pre-extracted ones.""",
        agent=youtube_researcher,
        expected_output="Enhanced analysis for each video with better summaries and complete ticker lists"
    )

    # Build video ID reference for formatter
    if prefetched_videos:
        video_id_list = ", ".join([v['videoId'] for v in prefetched_videos[:5]])
        video_reference = "\n".join([
            f"        Video {i+1}: videoId=\"{v['videoId']}\", title=\"{v['title']}\""
            for i, v in enumerate(prefetched_videos[:5])
        ])
    else:
        video_id_list = "unknown"
        video_reference = "No video reference available"

    youtube_format_task = Task(
        description=f"""Format the YouTube video analysis into a valid JSON array
        following this exact structure:

        [
          {{
            "videoId": "EXACT VIDEO ID - DO NOT CHANGE",
            "title": "Video Title",
            "publishedAt": "YYYY-MM-DD",
            "thumbnail": "https://img.youtube.com/vi/VIDEO_ID/maxresdefault.jpg",
            "tickersMentioned": ["AAPL", "MSFT"],
            "tickersBought": ["AAPL"],
            "tickersRecommended": ["MSFT"],
            "summary": "Brief 2-3 sentence summary of video content",
            "keyInsights": ["Insight 1", "Insight 2"]
          }}
        ]

        VIDEO REFERENCE (use these exact video IDs):
{video_reference}

        CRITICAL REQUIREMENTS:
        - Use the EXACT videoId values listed above - do NOT change them
        - thumbnail URL format: https://img.youtube.com/vi/VIDEO_ID/maxresdefault.jpg
        - All ticker symbols should be uppercase (e.g., AAPL, GOOGL, NVDA)
        - summary should be 2-3 sentences about the investment content
        - keyInsights should be actionable takeaways from the video
        - Output ONLY valid JSON array, no commentary or markdown

        Save the output to output/youtube_videos.json""",
        agent=formatter,
        expected_output="Valid JSON array saved to output/youtube_videos.json with correct video IDs",
        context=[youtube_task],
        output_file="output/youtube_videos.json"
    )

    # Get tickers dynamically at crew creation time
    tickers = get_tickers()

    fetch_task = Task(
        description=f"""Fetch the latest stock prices and basic financial metrics
        for the following tickers: {', '.join(tickers)}.

        For each ticker, gather:
        - Current stock price (in USD)
        - Recent trading activity
        - Basic financial metrics (revenue, FCF, debt, cash if available)

        Return the data in a clear, structured format.""",
        agent=data_fetcher,
        expected_output="A structured report with current prices and financial metrics for all tickers"
    )

    analysis_task = Task(
        description="""Using the fetched stock data, perform a comprehensive
        financial analysis for each stock. Always reference the exact price and
        fundamentals provided by the data fetcher—do NOT substitute your own.

        For each ticker you must:

        1. Calculate per-share DCF valuation ranges (USD, consistent with the fetched share price):
           - Conservative scenario (pessimistic assumptions)
           - Base case scenario (most likely assumptions)
           - Aggressive scenario (optimistic assumptions)
           * Requirements:
             • Always work in the SAME share units as the fetched price. If the company recently split, divide historical per-share values by the split ratio.
             • conservative high <= base low, aggressive low >= base high
             • Every range must have a non-zero spread (high-low >= 5% of price)
             • Each range must stay within ±200% of the fetched price unless you explicitly justify the deviation with fundamentals.
             • Tie each scenario back to the revenue/FCF/debt inputs you were given

        2. Assign factor scores (integers 1-5):
           - fcfQuality: Free cash flow consistency and growth
           - roicStrength: Return on invested capital vs. cost of capital
           - revenueDurability: Recurring revenue and competitive moat
           - balanceSheetStrength: Debt levels and financial flexibility
           - insiderActivity: Recent insider buying/selling patterns (use 1 for heavy net selling, 5 for sustained net buying)
           - valueRank: Overall cheapness vs. intrinsic value
           - expectedReturn: Potential upside from current price
           * Each score must be justified from the fetched metrics or reasonable recent trends.

        Provide concise reasoning for each scenario and score, explicitly citing at least
        two numeric data points per ticker (price, revenue growth, cash, debt, etc.).""",
        agent=analyst,
        expected_output="Detailed financial analysis with DCF ranges and factor scores for all stocks",
        context=[fetch_task]
    )

    format_task = Task(
        description=f"""Format the analyzed stock data into a valid JSON array
        following this exact structure:

        [
          {{
            "category": "Growth" or "Dividend",
            "ticker": "TICKER",
            "name": "Company Name",
            "price": 0.00,
            "dcf": {{
              "conservative": "low-high",
              "base": "low-high",
              "aggressive": "low-high"
            }},
            "fcfQuality": 1-5,
            "roicStrength": 1-5,
            "revenueDurability": 1-5,
            "balanceSheetStrength": 1-5,
            "insiderActivity": 1-5,
            "valueRank": 1-5,
            "expectedReturn": 1-5,
            "lastUpdated": "{datetime.now().strftime('%Y-%m-%d')}"
          }}
        ]

        Requirements:
        - All factor scores must be integers between 1 and 5
        - DCF ranges must be strings in format "low-high" (e.g., "450-500") with low < high
        - Use the exact price and company name supplied by the data fetcher; never zero them out
        - Category must be either "Dividend" or "Growth"
        - Output ONLY valid JSON, no commentary or extra text
        - No trailing commas
        - lastUpdated should be today's date in ISO format

        Save the output to output/stocks.json""",
        agent=formatter,
        expected_output="Valid JSON file saved to output/stocks.json",
        context=[analysis_task],
        output_file="output/stocks.json"
    )

    # Create and return the crew
    crew = Crew(
        agents=[data_fetcher, analyst, formatter, youtube_researcher],
        tasks=[youtube_task, youtube_format_task, fetch_task, analysis_task, format_task],
        process=Process.sequential,  # Tasks run in order
        verbose=True,
    )

    return crew


if __name__ == "__main__":
    print("Starting YouTube Influencer Stock Tracker Crew...")
    print(f"Analyzing tickers: {', '.join(get_tickers())}")
    print("-" * 60)

    crew = create_stock_tracker_crew()
    result = crew.kickoff()

    print("-" * 60)
    print("Crew execution completed!")
    print(f"Result: {result}")
