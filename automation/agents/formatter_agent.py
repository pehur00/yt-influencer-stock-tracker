"""
Data Formatter Agent
Formats analyzed stock data into the required JSON structure.
"""

from crewai import Agent


def create_formatter_agent(llm):
    """Creates a data formatter agent that structures data for the website."""

    return Agent(
        role='Data Formatter',
        goal='Format stock analysis data into valid JSON for the YouTube Influencer Stock Tracker',
        backstory="""You are a meticulous data engineer who specializes in
        structuring and formatting data. You take raw financial analysis and
        transform it into clean, valid JSON that matches exact specifications.

        You categorize stocks as either "Dividend" or "Growth" based on their
        characteristics:
        - Dividend stocks: Mature companies with consistent dividend payments
        - Growth stocks: High-growth companies focused on expansion

        You ensure all required fields are present, data types are correct,
        and the JSON is valid with no trailing commas or syntax errors.
        You always include today's date in ISO format (YYYY-MM-DD) as lastUpdated.""",
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )
