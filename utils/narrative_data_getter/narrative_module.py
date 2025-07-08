import sys
import re
import logging
import os
import asyncio
import atexit

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.join(current_dir, '..', '..')
sys.path.insert(0, project_root)

from news_data_getter import get_coindesk, get_crypto_panic
from twitter_scraper import scrape_crypto_tweets
from cointelegraph_scraper import scrape_cointelegraph_news
from utils.databases.mongodb import insert_documents, retrieve_documents, delete_collection


logging.basicConfig(
    level=logging.INFO,  # Set to DEBUG to see debug messages too
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # This outputs to console/terminal
    ]
)

logger = logging.getLogger(__name__)

collection_name = "narrative_data"

def _cleanup_asyncio():
    """Clean up asyncio resources properly."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            pending = asyncio.all_tasks(loop)
            for task in pending:
                task.cancel()
        loop.close()
    except Exception:
        pass

# Register cleanup function to run at exit
atexit.register(_cleanup_asyncio)



async def _parallel_runner(
    twitter_scrape_keywords: list[str] = [], 
    twitter_scrape_max_tweets: int = 500,
    cointelegraph_max_articles: int = 500
    ):
    """Run scraping tasks in parallel."""
    logger.info("Starting parallel scraping tasks...")
    try:
        results = await asyncio.gather(
            asyncio.to_thread(get_coindesk),
            asyncio.to_thread(get_crypto_panic),
            asyncio.to_thread(scrape_cointelegraph_news, max_articles=cointelegraph_max_articles),
            asyncio.to_thread(scrape_crypto_tweets, max_tweets=twitter_scrape_max_tweets, queries=twitter_scrape_keywords) if twitter_scrape_keywords else asyncio.to_thread(scrape_crypto_tweets, max_tweets=twitter_scrape_max_tweets)
        )
        narrative_data = []
        for result in results:
            if result:
                narrative_data.extend(result)

        return narrative_data
    except Exception as e:
        logger.error(f"Error in parallel scraping tasks: {e}")
        return []


def get_narrative_data(
        twitter_scrape_keywords: list[str] = [], 
        twitter_scrape_max_tweets: int = 500,
        cointelegraph_max_articles: int = 500
        ) -> list[dict[str, str]]:

    """Fetch narrative data from news (Coindesk, Crypto Panic, Cointelegraph) and twitter scraping sources.

    Args:
        twitter_scrape_keywords (list[str]): The keywords to use for scraping Twitter.
        twitter_scrape_max_tweets (int): The maximum number of tweets to scrape.
        cointelegraph_max_articles (int): The maximum number of articles to scrape from Cointelegraph.

    Returns:
        list: A list of narrative data articles with title, description, source, and published_at fields.
    """
    try:
        narrative_data = asyncio.run(_parallel_runner(
            twitter_scrape_keywords=twitter_scrape_keywords,
            twitter_scrape_max_tweets=twitter_scrape_max_tweets,
            cointelegraph_max_articles=cointelegraph_max_articles
        ))

        id = 1

        for data in narrative_data:
            desc_text = data.get('description', '')
            cleaned_text = desc_text.replace('\n', ' ').replace('\r', '').strip() if desc_text else ''
            cleaned_text = re.sub(r'http\S+|www\S+|https\S+', '', cleaned_text, flags=re.MULTILINE)
            cleaned_text = re.sub(r'@\w+', '', cleaned_text)
            cleaned_text = re.sub(r'#(\w+)', r'\1', cleaned_text)
            cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()
            data['description'] = cleaned_text

            data['id'] = str(id)
            id += 1

        return narrative_data
    except Exception as e:
        logger.error(f"Error fetching narrative data: {e}")
        return []


def save_narrative_data_to_db(narrative_data: list[dict[str, str]]) -> bool:
    """
    Save narrative data to MongoDB collection with collection name is "narrative_data"
    Args:
        narrative_data (list[dict[str, str]]): The narrative data to save.
    Returns:
        bool: True if saving is successful, False otherwise.
    """
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
