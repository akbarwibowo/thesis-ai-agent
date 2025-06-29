import requests
import logging

from dotenv import load_dotenv, find_dotenv
from os import getenv
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,  # Set to DEBUG to see debug messages too
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # This outputs to console/terminal
    ]
)

# Configure logger
logger = logging.getLogger(__name__)

load_dotenv(find_dotenv())

CRYPTO_PANIC_AUTH_TOKEN = getenv("CRYPTO_PANIC_AUTH_TOKEN")
COIN_DESK_API_KEY = getenv("COIN_DESK_API_KEY")

CRYPTO_PANIC_ENDPOINT = "https://cryptopanic.com/api/developer/v2/posts/"
COIN_DESK_ENDPOINT = "https://data-api.coindesk.com/news/v1/article/list"

"""
the format for the objects from API is:
{
    "title": "string",
    "description": "string",
    "source": "string",
    "published_at": "string"
}

the format for the objects from twitter is:
{
    "description": "string",
    "source": "twitter",
    "published_at": "string"
}
"""


def get_crypto_panic() -> list:
    """Fetches the latest crypto news from Crypto Panic API.

    Returns:
        list: A list of news articles formatted with title, description, source, and published_at fields.
              Returns empty list if request fails.
    
    Raises:
        requests.RequestException: If there's an error with the API request.
    """
    try:
        logger.info("Fetching crypto news from Crypto Panic API")
        response = requests.get(
            url=CRYPTO_PANIC_ENDPOINT,
            params={
                "auth_token": CRYPTO_PANIC_AUTH_TOKEN,
                "public": "true",
                "kind": "news",
            }
        )
        response.raise_for_status()  # Raise an error for bad responses

        data = response.json()
        results = data.get('results', [])
        final_results = []

        for result in results:
            date = datetime.fromisoformat(result.get("published_at", datetime.now().isoformat()))
            formatted_date = date.strftime("%Y-%m-%d")
            cleaned_object = {
                "title": result.get("title", ""),
                "description": result.get("description", ""),
                "source": "news",
                "published_at": formatted_date,
            }
            final_results.append(cleaned_object)

        logger.info(f"Successfully fetched {len(final_results)} articles from Crypto Panic")
        return final_results

    except requests.RequestException as e:
        error_msg = f"Error fetching Crypto Panic news: {e}"
        logger.error(error_msg)
        print(error_msg)
        return []


def get_coindesk() -> list:
    """Fetches the latest crypto news from CoinDesk API.

    Returns:
        list: A list of news articles formatted with title, description, source, and published_at fields.
              Returns empty list if request fails.
    
    Raises:
        requests.RequestException: If there's an error with the API request.
    """
    try:
        logger.info("Fetching crypto news from CoinDesk API")
        response = requests.get(
            url=COIN_DESK_ENDPOINT,
            params={"lang": "EN", "limit": 100, "to_ts": 1743444061},
            headers={
                "Content-type": "application/json; charset=UTF-8",
                "authorization": f"Apikey {COIN_DESK_API_KEY}"
            }
        )
        response.raise_for_status()  # Raise an error for bad responses

        data = response.json()
        results = data.get('Data', [])
        final_result = []

        for result in results:
            date = datetime.fromisoformat(result.get("PUBLISHED_ON", datetime.now().timestamp()))
            formatted_date = date.strftime("%Y-%m-%d")
            cleaned_object = {
                "title": result.get("TITLE", ""),
                "description": result.get("BODY", ""),
                "source": "news",
                "published_at": formatted_date,
            }
            final_result.append(cleaned_object)

        logger.info(f"Successfully fetched {len(final_result)} articles from CoinDesk")
        return final_result

    except requests.RequestException as e:
        error_msg = f"Error fetching CoinDesk news: {e}"
        logger.error(error_msg)
        print(error_msg)
        return []


def run_news_api() -> list:
    """Runs the data getter functions and aggregates their results.

    Returns:
        list: A combined list of news articles from both APIs.
    """
    crypto_panic_data = get_crypto_panic()
    coindesk_data = get_coindesk()
    # TODO add ID
    return crypto_panic_data + coindesk_data
