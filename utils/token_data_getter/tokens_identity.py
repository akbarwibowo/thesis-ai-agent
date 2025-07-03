import requests
import logging
import os
import sys


from dotenv import load_dotenv, find_dotenv
from os import getenv

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.join(current_dir, '..', '..')
sys.path.insert(0, project_root)

from utils.databases.mongodb import insert_documents, retrieve_documents, delete_document, retrieve_document

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


def get_and_save_token_identities() -> bool:
    """Fetches all token identities from CoinGecko.

    Returns:
        bool: True if successful, False otherwise.
    """
    url = f"{COINGECKO_ENDPOINT}coins/list"
    try:
        response = requests.get(
        url=url,
        params={
            "include_platform": "false",
            },
        headers={
            "accept": "application/json",
            "x-cg-demo-api-key": COINGECKO_API_KEY
            }
        )
        if response.status_code != 200:
            logger.error(f"Failed to fetch token IDs: {response.status_code} - {response.text}")
            return False

        data = response.json()
        token_identities = []
        for token in data:
            token_identities.append({
                "id": token.get("id"),
                "symbol": token.get("symbol"),
                "name": token.get("name")
            })
        logger.info("Successfully retrieved token identities")

        save_documents = insert_documents(
            collection_name="token_identities",
            documents=token_identities
        )
        if not save_documents:
            logger.error("Failed to save token identities")
        return save_documents
    except requests.RequestException as e:
        logger.error(f"Error fetching token identities: {e}")
        return False


def get_token_identity(token_id: str, max_retries: int = 1) -> dict:
    """Fetches a single token identity by its ID with retry mechanism.

    Args:
        token_id (str): The ID of the token to fetch.
        max_retries (int): Maximum number of retries to fetch from API.

    Returns:
        dict: The token identity if found with keys "id", "symbol", "name", empty dict otherwise.
    """
    try:
        documents = retrieve_document(
            collection_name="token_identities",
            filter={"id": token_id},
        )
        if documents:
            return documents
        else:
            logger.warning(f"Token identity with ID {token_id} not found")
            logger.info("Getting token identity from CoinGecko API and save to DB")
            if max_retries > 0:
                logger.info("Getting token identity from CoinGecko API and save to DB")
                
                # Fetch and save all token identities
                if get_and_save_token_identities():
                    logger.info("Successfully updated token identities. Retrying search...")
                    # Recursively call with decremented retry count
                    return get_token_identity(token_id, max_retries - 1)
                else:
                    logger.error("Failed to fetch token identities from API")
                    return {}
            else:
                logger.error(f"Maximum retries exceeded for token ID: {token_id}")
                return {}
                
    except Exception as e:
        logger.error(f"Error retrieving token identity: {e}")
        return {}
