import requests
import logging

from dotenv import load_dotenv, find_dotenv
from os import getenv


# Configure logger
logging.basicConfig(
    level=logging.INFO,  # Set to DEBUG to see debug messages too
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # This outputs to console/terminal
    ]
)
logger = logging.getLogger(__name__)

load_dotenv(find_dotenv())

COINGECKO_ENDPOINT = getenv("COINGECKO_ENDPOINT", "https://api.coingecko.com/api/v3/")
COINGECKO_API_KEY = getenv("COINGECKO_API_KEY")


def get_fundamental_data(token_id: str) -> dict:
    """Fetch fundamental data for a specific token from CoinGecko.

    Args:
        token_id (str): The ID of the token to fetch data for.

    Returns:
        dict: A dictionary containing the fundamental data of the token.
    """
    try:
        url = f"{COINGECKO_ENDPOINT}coins/{token_id}"
        response = requests.get(
        url=url,
        params={
            "localization": "false",
            "tickers": "false",
            "market_data": "true",
            "community_data": "true",
            "developer_data": "true",
            "sparkline": "false",

            },
        headers={
            "accept": "application/json",
            "x-cg-demo-api-key": COINGECKO_API_KEY
            }
        )

        if response.status_code != 200:
            logger.error(f"Failed to fetch categories: {response.status_code} - {response.text}")
            return {}
        
        data = response.json()

        developer_data = "Not Listed" if data.get("repos_url").get("github") == [] else data.get("developer_data", {})

        cleaned_data = {
            "name": data.get("name", ""),
            "categories": data.get("categories", []),
            "description": data.get("description", {}).get("en", ""),
            "whitepaper": data.get("links", {}).get("whitepaper", ""),
            "positive_sentiment": data.get("sentiment_votes_up_percentage", 0.0),
            "negative_sentiment": data.get("sentiment_votes_down_percentage", 0.0),
            "total_value_locked": data.get("market_data", {}).get("total_value_locked", 0.0),
            "market_cap": data.get("market_data", {}).get("market_cap", {}).get("usd", 0.0),
            "fully_diluted_valuation": data.get("market_data", {}).get("fully_diluted_valuation", {}).get("usd", 0.0),
            "total_supply": data.get("market_data", {}).get("total_supply", 0.0),
            "circulating_supply": data.get("market_data", {}).get("circulating_supply", 0.0),
            "max_supply": data.get("market_data", {}).get("max_supply", 0.0),
            "max_supply_infinite": data.get("max_supply", None),
            "developer_data": developer_data
        }

        return cleaned_data

    except requests.RequestException as e:
        logger.error(f"Error fetching fundamental data for {token_id}: {e}")
        return {}
