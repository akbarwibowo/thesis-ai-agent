from news_data_getter import get_coindesk, get_crypto_panic
from twitter_scraper import scrape_crypto_tweets

import logging

logging.basicConfig(
    level=logging.INFO,  # Set to DEBUG to see debug messages too
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # This outputs to console/terminal
    ]
)

logger = logging.getLogger(__name__)

def get_narrative_data(scraping_query: list[str] = [], since_date: str = "") -> list:
    """Fetch narrative data from news and twitter scraping sources.

    Args:
        scraping_query (list[str]): The keywords to use for scraping.
        since_date (str): The date to filter results since.

    Returns:
        list: A list of narrative data articles with title, description, source, and published_at fields.
    """
    narrative_data = []
    id = 1

    # Get news data
    coindesk_data = get_coindesk()
    for data in coindesk_data:
        data['id'] = str(id)
        id += 1
        data['source'] = 'news'
    narrative_data.extend(coindesk_data)

    # Get crypto panic data
    crypto_panic_data = get_crypto_panic()
    for data in crypto_panic_data:
        data['id'] = str(id)
        id += 1
        data['source'] = 'news'
    narrative_data.extend(crypto_panic_data)

    # Get Twitter data
    twitter_data = scrape_crypto_tweets(queries=scraping_query, since_date=since_date)

    for data in twitter_data:
        data.pop('tweet_url', None)
        data['id'] = str(id)
        id += 1
        data['source'] = 'twitter'
    narrative_data.extend(twitter_data)

    return narrative_data
