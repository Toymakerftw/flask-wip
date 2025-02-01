from stock_collection import fetch_yfinance_data, resolve_ticker_symbol
from news import fetch_articles
import logging

def fetch_company_data(company_name):
    """Fetch both stock data and news for a company"""
    try:
        # Resolve company name to ticker
        ticker = resolve_ticker_symbol(company_name)

        # Fetch stock data
        stock_data = fetch_yfinance_data(ticker)

        # Fetch news articles
        news_data = fetch_articles(company_name)[:5]  # Limit to 5 latest articles

        return {
            'ticker': ticker,
            'stock_data': stock_data,
            'news': news_data,
            'error': None
        }
    except Exception as e:
        logging.error(f"Error fetching data for {company_name}: {str(e)}")
        return {
            'ticker': None,
            'stock_data': None,
            'news': None,
            'error': str(e)
        }
