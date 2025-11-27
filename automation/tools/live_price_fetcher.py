"""
Multi-source Live Stock Price Fetcher

This module provides a robust method to fetch live stock prices
using multiple sources with fallback mechanisms.
"""

import os
import requests
import yfinance as yf
from typing import Dict, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class LivePriceFetcher:
    def __init__(self):
        # API keys from environment
        self.alpha_vantage_key = os.getenv('ALPHA_VANTAGE_API_KEY')
        self.financial_modeling_prep_key = os.getenv('FINANCIAL_MODELING_PREP_API_KEY')

    def fetch_prices_yfinance(self, tickers: list) -> Dict[str, Optional[float]]:
        """
        Fetch prices using yfinance as primary method
        """
        prices = {}
        for ticker in tickers:
            try:
                stock = yf.Ticker(ticker)
                price = (
                    stock.info.get('currentPrice') or
                    stock.info.get('regularMarketPrice') or
                    stock.info.get('previousClose')
                )
                prices[ticker] = round(float(price), 2) if price else None
            except Exception as e:
                print(f"yfinance error for {ticker}: {e}")
                prices[ticker] = None
        return prices

    def fetch_prices_alpha_vantage(self, tickers: list) -> Dict[str, Optional[float]]:
        """
        Fetch prices using Alpha Vantage as fallback
        """
        if not self.alpha_vantage_key:
            return {}

        prices = {}
        for ticker in tickers:
            try:
                url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={ticker}&apikey={self.alpha_vantage_key}"
                response = requests.get(url)
                data = response.json()

                # Extract price from Alpha Vantage response
                quote = data.get('Global Quote', {})
                price = quote.get('05. price')

                prices[ticker] = round(float(price), 2) if price else None
            except Exception as e:
                print(f"Alpha Vantage error for {ticker}: {e}")
                prices[ticker] = None
        return prices

    def fetch_prices_financial_modeling_prep(self, tickers: list) -> Dict[str, Optional[float]]:
        """
        Fetch prices using Financial Modeling Prep as fallback
        """
        if not self.financial_modeling_prep_key:
            return {}

        prices = {}
        try:
            # Batch quote retrieval
            symbols = ','.join(tickers)
            url = f"https://financialmodelingprep.com/api/v3/quote/{symbols}?apikey={self.financial_modeling_prep_key}"
            response = requests.get(url)
            data = response.json()

            for quote in data:
                ticker = quote.get('symbol')
                price = quote.get('price')
                prices[ticker] = round(float(price), 2) if price else None
        except Exception as e:
            print(f"Financial Modeling Prep error: {e}")

        return prices

    def fetch_live_prices(self, tickers: list) -> Dict[str, Optional[float]]:
        """
        Main method to fetch live prices with fallback mechanisms
        """
        # Priority: yfinance -> Alpha Vantage -> Financial Modeling Prep
        prices = self.fetch_prices_yfinance(tickers)

        # If yfinance fails for any ticker, try Alpha Vantage
        missing_tickers = [ticker for ticker, price in prices.items() if price is None]
        if missing_tickers:
            alpha_prices = self.fetch_prices_alpha_vantage(missing_tickers)
            prices.update(alpha_prices)

        # If Alpha Vantage fails, try Financial Modeling Prep
        missing_tickers = [ticker for ticker, price in prices.items() if price is None]
        if missing_tickers:
            fmp_prices = self.fetch_prices_financial_modeling_prep(missing_tickers)
            prices.update(fmp_prices)

        return prices

# Example usage
if __name__ == "__main__":
    fetcher = LivePriceFetcher()
    tickers = ["DUOL", "CMG", "ADBE", "MELI", "CRWV", "CRM", "SPGI", "EFX", "NFLX", "ASML", "MA"]
    live_prices = fetcher.fetch_live_prices(tickers)
    print("Live Prices:", live_prices)