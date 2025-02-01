import logging
import requests
from fuzzywuzzy import process
from GoogleNews import GoogleNews

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

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

def fetch_articles(query):
    try:
        logging.info(f"Fetching articles for query: '{query}'")
        googlenews = GoogleNews(lang="en")
        googlenews.search(query)
        articles = googlenews.result()
        logging.info(f"Fetched {len(articles)} articles")
        return articles
    except Exception as e:
        logging.error(
            f"Error while searching articles for query: '{query}'. Error: {e}"
        )
        raise ValueError(
            f"Unable to search articles for query: '{query}'. Try again later..."
        )
