"""
Market data tools built on yfinance for fetching stock prices and fundamentals.
"""

import yfinance as yf
from typing import Dict, Any
from crewai.tools import BaseTool


class StockPriceFetcher(BaseTool):
    name: str = "Stock Price Fetcher"
    description: str = (
        "Fetches current stock prices for a list of tickers. "
        "Input should be a comma-separated list of stock tickers. "
        "Returns a dictionary with tickers as keys and prices as values."
    )

    def _run(self, tickers: str) -> Dict[str, float]:
        """
        Fetch real-time stock prices using yfinance.
        """
        ticker_list = [t.strip() for t in tickers.split(',')]
        prices = {}

        print(f"Fetching prices for tickers: {ticker_list}")

        for ticker_symbol in ticker_list:
            try:
                ticker = yf.Ticker(ticker_symbol)
                info = ticker.info

                price = (
                    info.get('currentPrice') or
                    info.get('regularMarketPrice') or
                    info.get('previousClose')
                )

                if price:
                    prices[ticker_symbol] = round(float(price), 2)
                    print(f"  ✓ {ticker_symbol}: ${price}")
                else:
                    print(f"  ✗ {ticker_symbol}: No price found")
                    prices[ticker_symbol] = None

            except Exception as e:
                print(f"  ✗ {ticker_symbol}: Error - {str(e)}")
                prices[ticker_symbol] = None

        return prices


class FinancialDataScraper(BaseTool):
    name: str = "Financial Data Scraper"
    description: str = (
        "Fetches detailed financial data and metrics for a given stock ticker. "
        "Input should be a single stock ticker. "
        "Returns financial metrics like revenue, FCF, debt, market cap, etc."
    )

    def _run(self, ticker: str) -> Dict[str, Any]:
        """
        Fetch comprehensive financial data using yfinance.
        """
        print(f"Fetching financial data for: {ticker}")

        try:
            stock = yf.Ticker(ticker)
            info = stock.info

            data = {
                "ticker": ticker,
                "name": info.get('longName', ticker),
                "sector": info.get('sector', 'Unknown'),
                "industry": info.get('industry', 'Unknown'),
                "marketCap": info.get('marketCap'),
                "enterpriseValue": info.get('enterpriseValue'),
                "priceToBook": info.get('priceToBook'),
                "forwardPE": info.get('forwardPE'),
                "trailingPE": info.get('trailingPE'),
                "revenueGrowth": info.get('revenueGrowth'),
                "profitMargins": info.get('profitMargins'),
                "operatingMargins": info.get('operatingMargins'),
                "returnOnEquity": info.get('returnOnEquity'),
                "returnOnAssets": info.get('returnOnAssets'),
                "freeCashflow": info.get('freeCashflow'),
                "operatingCashflow": info.get('operatingCashflow'),
                "totalCash": info.get('totalCash'),
                "totalDebt": info.get('totalDebt'),
                "debtToEquity": info.get('debtToEquity'),
                "currentRatio": info.get('currentRatio'),
                "quickRatio": info.get('quickRatio'),
                "dividendYield": info.get('dividendYield'),
                "dividendRate": info.get('dividendRate'),
                "payoutRatio": info.get('payoutRatio'),
                "fiveYearAvgDividendYield": info.get('fiveYearAvgDividendYield'),
                "52WeekHigh": info.get('fiftyTwoWeekHigh'),
                "52WeekLow": info.get('fiftyTwoWeekLow'),
                "beta": info.get('beta'),
                "sharesOutstanding": info.get('sharesOutstanding'),
            }

            print(f"  ✓ {ticker}: Retrieved {len([v for v in data.values() if v is not None])} metrics")
            return data

        except Exception as e:
            print(f"  ✗ {ticker}: Error - {str(e)}")
            return {
                "ticker": ticker,
                "error": str(e)
            }


def get_financial_tools():
    """Returns a list of financial data tools for Crew.ai agents."""
    return [
        StockPriceFetcher(),
        FinancialDataScraper(),
    ]
