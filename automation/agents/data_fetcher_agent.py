"""
Data Fetcher Agent
Fetches current stock prices and basic financial data via Yahoo Finance tools.
"""

from crewai import Agent
from tools.market_data_tools import get_financial_tools


def create_data_fetcher_agent(llm):
    """Creates a data fetcher agent that gathers stock prices and data."""

    return Agent(
        role='Stock Data Fetcher',
        goal='Fetch the latest stock prices and basic financial metrics for tracked stocks',
        backstory="""You are an expert data gatherer who specializes in collecting
        real-time stock market data. You use reliable sources and web scraping tools
        to gather accurate, up-to-date information about stock prices, trading volumes,
        and basic financial metrics. You are thorough and always verify your data sources.""",
        tools=get_financial_tools(),
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )
