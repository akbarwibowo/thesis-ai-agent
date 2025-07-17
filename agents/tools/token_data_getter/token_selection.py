import requests
import logging
import re
from collections import Counter
import math

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


def _preprocess_text(text):
    """Preprocess text for similarity comparison.
    
    Args:
        text (str): Input text to preprocess.
        
    Returns:
        list: List of lowercase words.
    """
    # Convert to lowercase and split into words
    text = text.lower()
    # Remove special characters and split
    words = re.findall(r'\b\w+\b', text)
    return words


def _calculate_cosine_similarity(text1, text2):
    """Calculate cosine similarity between two texts.
    
    Args:
        text1 (str): First text.
        text2 (str): Second text.
        
    Returns:
        float: Cosine similarity score between 0 and 1.
    """
    # Preprocess texts
    words1 = _preprocess_text(text1)
    words2 = _preprocess_text(text2)

    # Create word frequency vectors
    all_words = set(words1 + words2)
    
    if not all_words:
        return 0.0
    
    # Create frequency vectors
    vector1 = [words1.count(word) for word in all_words]
    vector2 = [words2.count(word) for word in all_words]
    
    # Calculate cosine similarity
    dot_product = sum(a * b for a, b in zip(vector1, vector2))
    magnitude1 = math.sqrt(sum(a * a for a in vector1))
    magnitude2 = math.sqrt(sum(a * a for a in vector2))
    
    if magnitude1 == 0 or magnitude2 == 0:
        return 0.0
    
    return dot_product / (magnitude1 * magnitude2)


def _find_best_category_match(input_category, available_categories, threshold=0.1):
    """Find the best matching category using cosine similarity.
    
    Args:
        input_category (str): The input category name to match.
        available_categories (list): List of available category dictionaries.
        threshold (float): Minimum similarity threshold. Defaults to 0.1.
        
    Returns:
        dict or None: Best matching category dictionary or None if no match found.
    """
    best_match = None
    best_score = 0.0
    
    for category in available_categories:
        category_name = category.get("name", "")
        similarity = _calculate_cosine_similarity(input_category, category_name)

        logger.debug(f"Similarity between '{input_category}' and '{category_name}': {similarity:.3f}")
        
        if similarity > best_score and similarity >= threshold:
            best_score = similarity
            best_match = category
    
    if best_match:
        logger.info(f"Best match for '{input_category}': '{best_match['name']}' (score: {best_score:.3f})")
    else:
        logger.warning(f"No match found for '{input_category}' above threshold {threshold}")
    
    return best_match


def _get_categories_with_tokens() -> list[dict]:
    """
    Fetch categories from CoinGecko API along with their top 3 tokens.
    Returns:
        list: A list of dictionaries, each containing category id, name, and top 3 tokens.
        Each dictionary has the format:
            {
                "id": "category_id",
                "name": "category_name",
                "tokens": ["token_id_1", "token_id_2", "token_id_3"]
            }
    """
    url = f"{COINGECKO_ENDPOINT}coins/categories"
    response = requests.get(
        url=url,
        params={
            "order": "market_cap_desc",
        },
        headers={
            "accept": "application/json",
            "x-cg-demo-api-key": COINGECKO_API_KEY
        }
    )

    if response.status_code != 200:
        logger.error(f"Failed to fetch categories: {response.status_code} - {response.text}")
        return []
    logger.info(f"Successfully fetched {len(response.json())} categories with tokens")

    final_data = []
    for obj in response.json():
        final_data.append({
            "id": obj.get("id", ""),
            "name": obj.get("name", ""),
            "tokens": obj.get("top_3_coins_id", [])
        })

    return final_data


def categories_selector(categories: list[str], similarity_threshold=0.2) -> list[dict]:
    """Select categories based on similarity to input category names using cosine similarity.
    
    Args:
        categories (list[str]): List of category names to search for.
        similarity_threshold (float): Minimum similarity threshold for matching. Defaults to 0.2.
        
    Returns:
        list[dict]: List of selected category dictionaries that match the input categories with format:
            {
                "id": "category_id",
                "name": "category_name",
                "tokens": ["token_id_1", "token_id_2", "token_id_3"]
            }
    """
    logger.info(f"Selecting categories similar to: {categories}")
    
    # Get all available categories with tokens
    available_categories = _get_categories_with_tokens()
    
    if not available_categories:
        logger.error("No categories available from CoinGecko API")
        return []
    
    logger.info(f"Found {len(available_categories)} available categories to search through")
    
    selected_categories = []
    
    # For each input category, find the best match
    for input_category in categories:
        logger.info(f"Searching for category similar to: '{input_category}'")
        
        best_match = _find_best_category_match(
            input_category, 
            available_categories, 
            threshold=similarity_threshold
        )
        
        if best_match:
            # Check if we already have this category (avoid duplicates)
            if not any(cat['id'] == best_match['id'] for cat in selected_categories):
                selected_categories.append(best_match)
                logger.info(f"Added category: '{best_match['name']}' (ID: {best_match['id']})")
            else:
                logger.info(f"Category '{best_match['name']}' already selected, skipping duplicate")
        else:
            logger.warning(f"No similar category found for '{input_category}'")
    
    logger.info(f"Selected {len(selected_categories)} categories total")
    
    # Log the final selection
    for category in selected_categories:
        logger.info(f"Selected: {category['name']} - Tokens: {category['tokens']}")
    
    return selected_categories
