"""
YouTube Researcher Agent
Analyzes videos from YouTube finance influencers to extract stock tickers.
Uses YoutubeVideoSearchTool to analyze specific video content via RAG.
"""

from crewai import Agent

try:
    from crewai_tools import YoutubeVideoSearchTool
    YOUTUBE_TOOLS_AVAILABLE = True
except ImportError:
    YOUTUBE_TOOLS_AVAILABLE = False
    YoutubeVideoSearchTool = None


def create_youtube_agent(llm):
    """Creates a YouTube researcher agent that analyzes finance influencer videos."""

    tools = []
    if YOUTUBE_TOOLS_AVAILABLE and YoutubeVideoSearchTool:
        try:
            # Video search tool for analyzing specific videos by URL
            # This uses RAG to search within video transcripts
            yt_video_tool = YoutubeVideoSearchTool()
            tools.append(yt_video_tool)
            print("YoutubeVideoSearchTool initialized successfully")
        except Exception as e:
            print(f"Warning: Could not initialize YouTube tools: {e}")

    if not tools:
        print("Warning: No YouTube tools available. Agent will work with limited capabilities.")

    return Agent(
        role='YouTube Stock Researcher',
        goal='Analyze video transcripts from YouTube finance influencers to identify stocks they discuss, recommend, or have bought',
        backstory=f"""You are an expert at analyzing investment content from YouTube videos.
        You specialize in extracting stock information from various finance channels.
        
        You will be given specific YouTube video URLs to analyze. Use your YoutubeVideoSearchTool
        to search within each video's transcript for stock-related information.
        
        For each video, search for:
        - Stock tickers mentioned (e.g., "AAPL", "GOOGL", "NVDA")
        - Stocks the creator says they "bought" or are "buying"  
        - Stocks they recommend viewers consider
        - Key investment insights and reasoning
        
        Be meticulous about distinguishing between:
        - Stocks they merely discuss or analyze
        - Stocks they recommend viewers consider buying  
        - Stocks they have personally bought or are buying
        
        Use your YoutubeVideoSearchTool with search queries like:
        - "stocks bought buying purchased"
        - "recommend buy consider"
        - "portfolio added position"
        - Specific ticker symbols""",
        tools=tools,
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )
