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
        description=f"""Analyze YouTube videos from finance influencers using their ACTUAL TRANSCRIPT CONTENT.

        IMPORTANT: Video titles are often clickbait! Do NOT rely on titles to determine sentiment.
        You MUST use YoutubeVideoSearchTool to analyze what the creator ACTUALLY SAYS in the video.

        PRE-FETCHED VIDEO DATA (titles may be misleading - verify with transcript):
        {video_list}

        For EACH video, use YoutubeVideoSearchTool to search the transcript:
        
        1. SENTIMENT ANALYSIS (most important):
           - Search for: "I'm buying", "I bought", "adding to position", "great opportunity"
           - Search for: "I'm selling", "sold", "avoid", "stay away", "overvalued"
           - Search for: "be careful", "wait for pullback", "not buying yet"
           - Determine the creator's ACTUAL stance from what they SAY, not the title
           
        2. STOCK CLASSIFICATION (based on transcript, not title):
           - tickersBought: ONLY stocks they explicitly say "I bought" or "I'm buying"
           - tickersRecommended: Stocks they say viewers should "consider", "look at", "is undervalued"
           - tickersMentioned: All stocks discussed (even negatively)
           - tickersCautioned: Stocks they warn against or suggest selling
           
        3. SENTIMENT FIELD:
           - "bullish" = creator is positive, buying, recommending
           - "bearish" = creator is warning, selling, suggesting to avoid
           - "neutral" = just analyzing without strong recommendation
           
        Example: A video titled "Time to SELL AMD?" might actually have the creator saying 
        "I'm still holding AMD and think it's a great long-term buy" - the TRANSCRIPT matters!

        Return for each video:
        - videoId (KEEP EXACTLY AS PROVIDED)
        - title (keep as provided) 
        - sentiment (bullish/bearish/neutral based on TRANSCRIPT)
        - tickersMentioned (all stocks discussed)
        - tickersBought (ONLY if they explicitly say they bought)
        - tickersRecommended (ONLY if they actually recommend buying)
        - tickersCautioned (stocks they warn against)
        - summary (2-3 sentences about their ACTUAL stance from the video)
        - keyInsights (actionable takeaways from what they SAID)""",
        agent=youtube_researcher,
        expected_output="Transcript-based analysis with accurate sentiment and stock classifications"
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
            "channelId": "channel-id",
            "channelName": "Channel Name",
            "sentiment": "bullish|bearish|neutral",
            "tickersMentioned": ["AAPL", "MSFT"],
            "tickersBought": ["AAPL"],
            "tickersRecommended": ["MSFT"],
            "tickersCautioned": [],
            "summary": "Brief 2-3 sentence summary based on ACTUAL video content",
            "keyInsights": ["Insight 1", "Insight 2"]
          }}
        ]

        VIDEO REFERENCE (use these exact video IDs):
{video_reference}

        CRITICAL REQUIREMENTS:
        - Use the EXACT videoId values listed above - do NOT change them
        - sentiment MUST be based on transcript analysis, NOT the clickbait title
        - tickersRecommended should ONLY include stocks the creator explicitly recommends
        - tickersBought should ONLY include stocks they say they bought
        - tickersCautioned should include stocks they warn against
        - If sentiment is "bearish", tickersRecommended should typically be empty
        - thumbnail URL format: https://img.youtube.com/vi/VIDEO_ID/maxresdefault.jpg
        - All ticker symbols should be uppercase (e.g., AAPL, GOOGL, NVDA)
        - Output ONLY valid JSON array, no commentary or markdown

        Save the output to output/youtube_videos.json""",
        agent=formatter,
        expected_output="Valid JSON array saved to output/youtube_videos.json with correct video IDs and transcript-based sentiment",
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
             • Each range must be a proper range with low and high values that DIFFER by 5-10%
               WRONG: "250-250" | CORRECT: "240-260"
             • Always work in the SAME share units as the fetched price. If the company recently split, divide historical per-share values by the split ratio.
             • conservative high <= base low, aggressive low >= base high
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
        - DCF ranges MUST be strings in format "low-high" where low and high are DIFFERENT numbers
          * WRONG: "250-250" (same number twice)
          * CORRECT: "240-260" (proper range with ~5-10% spread)
          * The spread between low and high should be approximately 5-10% of the midpoint
          * Example: for a $500 stock, conservative might be "420-480", base "480-520", aggressive "520-580"
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
