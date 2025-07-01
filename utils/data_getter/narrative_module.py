import sys
import re
import logging
import os
import json

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.join(current_dir, '..', '..')
sys.path.insert(0, project_root)

from news_data_getter import get_coindesk, get_crypto_panic
from twitter_scraper import scrape_crypto_tweets
from utils.databases.mongodb import insert_documents
from cointelegraph_scraper import scrape_cointelegraph_news


logging.basicConfig(
    level=logging.INFO,  # Set to DEBUG to see debug messages too
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # This outputs to console/terminal
    ]
)

logger = logging.getLogger(__name__)

def get_narrative_data(scraping_query: list[str] = []) -> list[dict[str, str]]:
    """Fetch narrative data from news and twitter scraping sources.

    Args:
        scraping_query (list[str]): The keywords to use for scraping.
        since_date (str): The date to filter results since.

    Returns:
        list: A list of narrative data articles with title, description, source, and published_at fields.
    """
    narrative_data = []
    id = 1

    # Get coindesk news data
    coindesk_data = get_coindesk()
    for data in coindesk_data:
        desc_text = data.get('description', '')
        cleaned_text = desc_text.replace('\n', ' ').replace('\r', '').strip() if desc_text else ''
        cleaned_text = re.sub(r'http\S+|www\S+|https\S+', '', cleaned_text, flags=re.MULTILINE)
        cleaned_text = re.sub(r'@\w+', '', cleaned_text)
        cleaned_text = re.sub(r'#(\w+)', r'\1', cleaned_text)
        cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()
        data['description'] = cleaned_text

        data['id'] = str(id)
        id += 1
        data['source'] = 'news'
    narrative_data.extend(coindesk_data)

    # Get cryptopanic news data
    crypto_panic_data = get_crypto_panic()
    for data in crypto_panic_data:
        desc_text = data.get('description', '')
        cleaned_text = desc_text.replace('\n', ' ').replace('\r', '').strip() if desc_text else ''
        cleaned_text = re.sub(r'http\S+|www\S+|https\S+', '', cleaned_text, flags=re.MULTILINE)
        cleaned_text = re.sub(r'@\w+', '', cleaned_text)
        cleaned_text = re.sub(r'#(\w+)', r'\1', cleaned_text)
        cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()
        data['description'] = cleaned_text

        data['id'] = str(id)
        id += 1
        data['source'] = 'news'
    narrative_data.extend(crypto_panic_data)

    # Get Twitter data
    if not scraping_query:
        twitter_data = scrape_crypto_tweets()
    else:
        twitter_data = scrape_crypto_tweets(queries=scraping_query)

    for data in twitter_data:
        tweet_text = data.get('tweet', '')
        cleaned_tweet = tweet_text.replace('\n', ' ').replace('\r', '').strip() if tweet_text else ''
        cleaned_tweet = re.sub(r'http\S+|www\S+|https\S+', '', cleaned_tweet, flags=re.MULTILINE)
        cleaned_tweet = re.sub(r'@\w+', '', cleaned_tweet)
        cleaned_tweet = re.sub(r'#(\w+)', r'\1', cleaned_tweet)
        cleaned_tweet = re.sub(r'\s+', ' ', cleaned_tweet).strip()
        data['tweet'] = cleaned_tweet

        data.pop('tweet_url', None)
        data['id'] = str(id)
        id += 1
        
        data['source'] = 'twitter'
    narrative_data.extend(twitter_data)

    return narrative_data

def save_narrative_data_to_db(narrative_data: list[dict[str, str]], collection_name: str = "narrative_data") -> bool:
    if not narrative_data:
        logger.warning("No narrative data to save.")
        return False

    try:
        insert_documents(collection_name, narrative_data)
        logger.info(f"Successfully saved narrative data to {collection_name}.")
        return True
    except Exception as e:
        logger.error(f"Error saving narrative data to {collection_name}: {e}")
        return False


# if __name__ == "__main__":
#     # Example usage
#     narrative_data = get_narrative_data()
#     if narrative_data:
#         save_narrative_data_to_db(narrative_data)
#     else:
#         logger.info("No narrative data fetched.")
    # retrieved_data = retrieve_documents("narrative_data")
    # print(type(retrieved_data))  # Print or save the JSON data as needed
    # print(retrieved_data)  # Print or save the JSON data as needed
    # with open('narrative_data.json', 'w', encoding='utf-8') as f:
    #     json.dump(retrieved_data, f, indent=4, ensure_ascii=False)
