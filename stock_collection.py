import logging
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import requests
from fuzzywuzzy import process

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# Technical Analysis Parameters
TA_CONFIG = {
    'rsi_window': 14,
    'macd_fast': 12,
    'macd_slow': 26,
    'macd_signal': 9,
    'bollinger_window': 20,
    'sma_windows': [20, 50, 200],
    'ema_windows': [12, 26],
    'volatility_window': 30
}

def calculate_technical_indicators(history):
    """Calculate various technical indicators from historical price data"""
    ta_results = {}

    # RSI
    delta = history['Close'].diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)

    avg_gain = gain.rolling(TA_CONFIG['rsi_window']).mean()
    avg_loss = loss.rolling(TA_CONFIG['rsi_window']).mean()
    rs = avg_gain / avg_loss
    ta_results['rsi'] = 100 - (100 / (1 + rs)).iloc[-1]

    # MACD
    ema_fast = history['Close'].ewm(span=TA_CONFIG['macd_fast'], adjust=False).mean()
    ema_slow = history['Close'].ewm(span=TA_CONFIG['macd_slow'], adjust=False).mean()
    macd = ema_fast - ema_slow
    signal = macd.ewm(span=TA_CONFIG['macd_signal'], adjust=False).mean()
    ta_results['macd'] = macd.iloc[-1]
    ta_results['macd_signal'] = signal.iloc[-1]

    # Bollinger Bands
    sma = history['Close'].rolling(TA_CONFIG['bollinger_window']).mean()
    std = history['Close'].rolling(TA_CONFIG['bollinger_window']).std()
    ta_results['bollinger_upper'] = (sma + 2 * std).iloc[-1]
    ta_results['bollinger_lower'] = (sma - 2 * std).iloc[-1]

    # Moving Averages
    for window in TA_CONFIG['sma_windows']:
        ta_results[f'sma_{window}'] = history['Close'].rolling(window).mean().iloc[-1]
    for window in TA_CONFIG['ema_windows']:
        ta_results[f'ema_{window}'] = history['Close'].ewm(span=window, adjust=False).mean().iloc[-1]

    # Volatility
    returns = history['Close'].pct_change().dropna()
    ta_results['volatility_30d'] = returns.rolling(TA_CONFIG['volatility_window']).std().iloc[-1] * np.sqrt(252)

    return ta_results

def resolve_ticker_symbol(query: str) -> str:
    """
    Convert company names/partial symbols to valid Yahoo Finance tickers.
    Example: "Kalyan Jewellers" → "KALYANKJIL.NS"
    """
    url = "https://query2.finance.yahoo.com/v1/finance/search"
    headers = {"User-Agent": "Mozilla/5.0"}  # Avoid blocking
    params = {"q": query, "quotesCount": 5, "country": "India"}

    response = requests.get(url, headers=headers, params=params)
    data = response.json()

    if not data.get("quotes"):
        raise ValueError(f"No ticker found for: {query}")

    # Extract quotes data
    quotes = data["quotes"]
    tickers = [quote["symbol"] for quote in quotes]
    names = [quote.get("longname") or quote.get("shortname", "") for quote in quotes]

    # Fuzzy match the query with company names
    best_match, score = process.extractOne(query, names)
    if not best_match:
        raise ValueError(f"No matching ticker found for: {query}")

    index = names.index(best_match)
    best_quote = quotes[index]
    resolved_ticker = best_quote["symbol"]
    exchange_code = best_quote.get("exchange", "").upper()

    # Map exchange codes to suffixes
    exchange_suffix_map = {
        "NSI": ".NS",  # NSE
        "BOM": ".BO",  # BSE
        "BSE": ".BO",
        "NSE": ".NS",
    }
    suffix = exchange_suffix_map.get(exchange_code, ".NS")  # Default to NSE

    # Append suffix only if not already present
    if not resolved_ticker.endswith(suffix):
        resolved_ticker += suffix

    return resolved_ticker

def fetch_yfinance_data(ticker):
    """Enhanced Yahoo Finance data fetching with technical analysis"""
    try:
        logging.info(f"Fetching Yahoo Finance data for: {ticker}")
        stock = yf.Ticker(ticker)
        history = stock.history(period="1y", interval="1d")

        if history.empty:
            logging.error(f"No data found for {ticker}")
            return {"error": f"No data found for {ticker}"}

        # Calculate technical indicators
        ta_data = calculate_technical_indicators(history)

        # Current price data
        current_price = history['Close'].iloc[-1]
        prev_close = history['Close'].iloc[-2] if len(history) > 1 else 0
        price_change = current_price - prev_close
        percent_change = (price_change / prev_close) * 100 if prev_close != 0 else 0

        return {
            'current_price': current_price,
            'price_change': price_change,
            'percent_change': percent_change,
            'technical_indicators': ta_data,
            'fundamentals': stock.info
        }

    except Exception as e:
        logging.error(f"Error fetching Yahoo Finance data for {ticker}: {str(e)}")
        return {"error": f"Failed to fetch data for {ticker}: {str(e)}"}
