import requests
import logging
import os
import sys

from dotenv import load_dotenv, find_dotenv
from os import getenv
from datetime import datetime, timedelta

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.join(current_dir, '..', '..')
sys.path.insert(0, project_root)

from utils.databases.influxdb import save_price_data, get_price_data
from tokens_identity import get_token_identity

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


def _get_token_price_data(token_id: str) -> list[dict]:
    """
    Fetch historical price data for a specific token from the CoinGecko API.
    Args:
        token_id (str): The ID of the token to fetch price data for.
    Returns:
        dict: A dictionary containing the price and volume data with timestamps and values. the schema as follow:
            [
                {
                    "timestamp": "YYYY-MM-DD",
                    "price": float,
                    "volume": float
                },
            ]
            Returns an empty dictionary if the request fails or no data is found.
    """

    url = f"{COINGECKO_ENDPOINT}coins/{token_id}/market_chart"
    params = {
            "vs_currency": "usd",
            "days": "365",
            "interval": "daily",
            "precision": "4"
    }
    try:
        response = requests.get(url, params=params)
        if response.status_code != 200:
            logger.error(f"Failed to fetch price data for {token_id}: {response.status_code} - {response.text}")
            return []

        data = response.json()
        return_data = [
            {
                "timestamp": datetime.fromtimestamp(price[0] / 1000).strftime("%Y-%m-%d"),
                "price": price[1],
                "volume": volume[1]
            } for price, volume in zip(data.get("prices", []), data.get("total_volumes", []))
        ]

        logger.info(f"Successfully retrieved price data for {token_id}")
        return return_data
    except requests.RequestException as e:
        logger.error(f"Error fetching price data for {token_id}: {e}")
        return []


def get_price_data_of_tokens(token_ids: list[str]) -> list[dict]:
    """
    Fetch price data for a list of tokens.
    Args:
        token_ids (list[str]): A list of token IDs to fetch price data for.
    Returns:
        list[dict]: A list of dictionaries containing price data for each token.
            Each dictionary has the following structure:
            [
                {
                    "token_id": str,
                    "price_data": [
                        {
                            "timestamp": "YYYY-MM-DD",
                            "price": float,
                            "volume": float
                        },
                    ]
                },
            ]
    """
    try:
        all_data = []
        for token_id in token_ids:
            token_identity = get_token_identity(token_id)
            # check if data already exists in InfluxDB
            existing_data = get_price_data(token_name=token_identity['name'], token_symbol=token_identity['symbol'])
            if existing_data:
                existing_data_last_tick = existing_data[-1]['timestamp']
                existing_data_last_tick = datetime.fromisoformat(existing_data_last_tick) if isinstance(existing_data_last_tick, str) else existing_data_last_tick
                existing_data_last_tick = existing_data_last_tick.replace(tzinfo=None)
                current_time = datetime.now()
                # If the last tick is older than 7 days, we consider it stale
                if (current_time - existing_data_last_tick) < timedelta(days=7):
                    logger.info(f"Found existing data for {token_id} in InfluxDB")
                    all_data.append({
                        "token_id": token_id,
                        "price_data": existing_data
                    })
                    continue
            logger.info(f"No existing data found for {token_id} in InfluxDB")
            new_data = _get_token_price_data(token_id)
            if new_data:
                all_data.append({
                    "token_id": token_id,
                    "price_data": new_data
                })
        return all_data
    except Exception as e:
        logger.error(f"Error fetching price data for tokens: {e}")
        return []


def save_price_data_to_db(price_data: list) -> dict:
    """
    Save price data to the database.
    Args:
        price_data (list): A list of dictionaries containing price data for tokens.
            Each dictionary should have the following structure:
            [
                {
                    "token_id": str,
                    "price_data": [
                        {
                            "timestamp": "YYYY-MM-DD",
                            "price": float,
                            "volume": float
                        },
                    ]
                },
            ]
    Returns:
        dict: A dictionary with the status of the save operation for each token.
            The structure is as follows:
            {
                "token_id": "status message"
            }
    """

    try:
        return_status = {}
        for token in price_data:
            token_identity = get_token_identity(token["token_id"])
            price_data = token["price_data"]
            # Save each price data entry to the database
            save_price_data(
                token_name=token_identity['name'],
                token_symbol=token_identity['symbol'],
                price_data=price_data
            )
            logger.info(f"Successfully saved price data for {token_identity['name']} ({token_identity['symbol']}) to DB")
            return_status[token_identity['name']] = f"fundamental data for {token_identity['name']} saved successfully"
        return return_status
    except Exception as e:
        logger.error(f"Error saving price data to DB: {e}")
        return {"status": "error", "message": str(e)}
