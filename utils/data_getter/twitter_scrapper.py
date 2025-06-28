import json
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from datetime import datetime, timedelta
import time
from dotenv import load_dotenv, find_dotenv
from os import getenv

# Load environment variables
load_dotenv(find_dotenv())

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
    ]
)

# Configure logger
logger = logging.getLogger(__name__)

# Get Twitter credentials from environment
TWITTER_EMAIL = getenv("TWITTER_EMAIL_MAIN")
TWITTER_PASSWORD = getenv("TWITTER_PASSWORD_MAIN")
TWITTER_USERNAME = getenv("TWITTER_USERNAME_MAIN")


def setup_chrome_driver():
    """Set up Chrome driver with appropriate options for scraping.

    Returns:
        webdriver.Chrome: Configured Chrome WebDriver instance.
    """
    chrome_options = Options()
    # chrome_options.add_argument("--headless")  # Comment out to see browser running
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    
    try:
        driver = webdriver.Chrome(options=chrome_options)
        logger.info("Chrome driver initialized successfully")
        return driver
    except Exception as e:
        logger.error(f"Failed to initialize Chrome driver: {e}")
        raise


def login_to_twitter(driver):
    """Login to Twitter/X using credentials from environment variables.

    Args:
        driver (webdriver.Chrome): The Chrome WebDriver instance.

    Returns:
        bool: True if login is successful, False otherwise.

    Raises:
        Exception: If there's an error during the login process.
    """
    try:
        logger.info("Attempting to login to Twitter/X")

        if not TWITTER_EMAIL or not TWITTER_PASSWORD:
            logger.error("TWITTER_EMAIL or TWITTER_PASSWORD not found in environment variables")
            return False
        
        # Navigate to Twitter login page
        driver.get("https://twitter.com/login")
        wait = WebDriverWait(driver, 20)
        
        # Wait for and fill email/username field
        email_field = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'input[name="text"]'))
        )
        email_field.clear()
        email_field.send_keys(TWITTER_EMAIL)
        logger.info("Email entered successfully")
        
        # Click Next button
        next_button = driver.find_element(By.XPATH, '//span[text()="Next"]')
        next_button.click()
        time.sleep(2)
        
        # Handle potential username prompt (sometimes Twitter asks for username instead of email)
        try:
            username_field = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'input[data-testid="ocfEnterTextTextInput"]'))
            )
            username_field.clear()
            username_field.send_keys(str(TWITTER_USERNAME))
            next_button = driver.find_element(By.XPATH, '//span[text()="Next"]')
            next_button.click()
            time.sleep(2)
            logger.info("Username verification completed")
        except TimeoutException:
            # Username field didn't appear, continue to password
            pass
        
        # Wait for and fill password field
        password_field = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'input[name="password"]'))
        )
        password_field.clear()
        password_field.send_keys(TWITTER_PASSWORD)
        logger.info("Password entered successfully")
        
        # Click Login button
        login_button = driver.find_element(By.XPATH, '//span[text()="Log in"]')
        login_button.click()
        
        # Wait for successful login (check for home page elements)
        wait.until(
            EC.any_of(
                EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="SideNav_AccountSwitcher_Button"]')),
                EC.presence_of_element_located((By.CSS_SELECTOR, '[aria-label="Home timeline"]')),
                EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="primaryColumn"]'))
            )
        )
        
        logger.info("Successfully logged in to Twitter/X")
        return True
        
    except TimeoutException as e:
        logger.error(f"Timeout during login process: {e}")
        return False
    except Exception as e:
        logger.error(f"Error during Twitter login: {e}")
        return False


def parse_twitter_date(date_str):
    """Parse Twitter date format to datetime object.

    Args:
        date_str (str): Date string from Twitter (e.g., "2h", "1d", "Mar 15", etc.)

    Returns:
        str: Formatted date string in YYYY-MM-DD format.
    """
    now = datetime.now()
    
    if 'm' in date_str and date_str.replace('m', '').isdigit():
        # Minutes ago (e.g., "5m")
        minutes = int(date_str.replace('m', ''))
        tweet_time = now - timedelta(minutes=minutes)
    elif 'h' in date_str and date_str.replace('h', '').isdigit():
        # Hours ago (e.g., "2h")
        hours = int(date_str.replace('h', ''))
        tweet_time = now - timedelta(hours=hours)
    elif 'd' in date_str and date_str.replace('d', '').isdigit():
        # Days ago (e.g., "1d")
        days = int(date_str.replace('d', ''))
        tweet_time = now - timedelta(days=days)
    else:
        # Try to parse other formats or default to current time
        try:
            # Handle formats like "Mar 15" or full dates
            if len(date_str.split()) == 2:
                month_day = date_str.split()
                month_names = {
                    'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6,
                    'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12
                }
                month = month_names.get(month_day[0], now.month)
                day = int(month_day[1])
                tweet_time = datetime(now.year, month, day)
            else:
                tweet_time = now
        except:
            tweet_time = now
    
    return tweet_time.strftime("%Y-%m-%d")


def scrape_twitter_search(query, max_tweets=100, driver=None, since_date="2025-04-01"):
    """Scrape tweets from Twitter search results.

    Args:
        query (str): Search query to look for tweets about.
        max_tweets (int): Maximum number of tweets to scrape. Defaults to 100.
        driver (webdriver.Chrome, optional): Existing Chrome WebDriver instance. If None, creates new driver and handles login.
        since_date (str): Date to search tweets from in YYYY-MM-DD format. Defaults to "2025-04-01".

    Returns:
        list: A list of dictionaries containing tweet data with 'tweets' and 'published_at' fields.
              Returns empty list if scraping fails.

    Raises:
        Exception: If there's an error during the scraping process.
    """
    driver_created = False
    if driver is None:
        driver_created = True
        driver = setup_chrome_driver()
        # Login to Twitter first
        if not login_to_twitter(driver):
            logger.error("Failed to login to Twitter. Cannot proceed with scraping.")
            return []
        
    try:
        logger.info(f"Starting Twitter scraping for query: {query} since {since_date}")
        
        # Navigate to Twitter search with date filter
        # Twitter search syntax: query since:YYYY-MM-DD
        search_query = f"{query} since:{since_date}"
        search_url = f"https://twitter.com/search?q={search_query}&src=typed_query&f=live"
        driver.get(search_url)
        logger.info(f"Navigating to Twitter search URL: {search_url}")
        
        # Wait for page to load
        time.sleep(5)
        
        tweets_data = []
        last_height = driver.execute_script("return document.body.scrollHeight")
        scroll_attempts = 0
        max_scroll_attempts = 10
        
        while len(tweets_data) < max_tweets and scroll_attempts < max_scroll_attempts:
            # Find tweet elements
            tweet_elements = driver.find_elements(By.CSS_SELECTOR, '[data-testid="tweet"]')
            
            for tweet_element in tweet_elements:
                if len(tweets_data) >= max_tweets:
                    break
                    
                try:
                    # Extract tweet text
                    tweet_text_element = tweet_element.find_element(By.CSS_SELECTOR, '[data-testid="tweetText"]')
                    tweet_text = tweet_text_element.text
                    
                    # Extract timestamp
                    time_element = tweet_element.find_element(By.CSS_SELECTOR, 'time')
                    date_str = time_element.get_attribute('datetime')
                    
                    if date_str:
                        # Parse ISO format datetime
                        tweet_datetime = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                        formatted_date = tweet_datetime.strftime("%Y-%m-%d")
                    else:
                        # Fallback to text content
                        date_text = time_element.text
                        formatted_date = parse_twitter_date(date_text)
                    
                    # Create tweet object
                    tweet_obj = {
                        "tweets": tweet_text,
                        "published_at": formatted_date
                    }
                    
                    # Check if tweet already exists (avoid duplicates)
                    if tweet_obj not in tweets_data:
                        tweets_data.append(tweet_obj)
                        logger.debug(f"Scraped tweet: {tweet_text[:50]}...")
                    
                except NoSuchElementException:
                    continue
                except Exception as e:
                    logger.warning(f"Error extracting tweet data: {e}")
                    continue
            
            # Scroll down to load more tweets
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(3)
            
            # Check if new content loaded
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                scroll_attempts += 1
            else:
                scroll_attempts = 0
            last_height = new_height
        
        logger.info(f"Successfully scraped {len(tweets_data)} tweets for query: {query}")
        return tweets_data
        
    except Exception as e:
        error_msg = f"Error scraping Twitter for query '{query}': {e}"
        logger.error(error_msg)
        print(error_msg)
        return []
    
    finally:
        if driver_created and driver:
            driver.quit()
            logger.info("Chrome driver closed")


def scrape_twitter_user(username, max_tweets=50):
    """Scrape tweets from a specific Twitter user's timeline.

    Args:
        username (str): Twitter username (without @ symbol).
        max_tweets (int): Maximum number of tweets to scrape. Defaults to 50.

    Returns:
        list: A list of dictionaries containing tweet data with 'tweets' and 'published_at' fields.
              Returns empty list if scraping fails.

    Raises:
        Exception: If there's an error during the scraping process.
    """
    driver = None
    try:
        logger.info(f"Starting Twitter scraping for user: @{username}")
        driver = setup_chrome_driver()
        
        # Login to Twitter first
        if not login_to_twitter(driver):
            logger.error("Failed to login to Twitter. Cannot proceed with scraping.")
            return []
        
        # Navigate to user's Twitter profile
        profile_url = f"https://twitter.com/{username}"
        driver.get(profile_url)
        logger.info(f"Navigating to Twitter profile: {profile_url}")
        
        # Wait for page to load
        time.sleep(5)
        
        tweets_data = []
        last_height = driver.execute_script("return document.body.scrollHeight")
        scroll_attempts = 0
        max_scroll_attempts = 10
        
        while len(tweets_data) < max_tweets and scroll_attempts < max_scroll_attempts:
            # Find tweet elements
            tweet_elements = driver.find_elements(By.CSS_SELECTOR, '[data-testid="tweet"]')
            
            for tweet_element in tweet_elements:
                if len(tweets_data) >= max_tweets:
                    break
                    
                try:
                    # Extract tweet text
                    tweet_text_element = tweet_element.find_element(By.CSS_SELECTOR, '[data-testid="tweetText"]')
                    tweet_text = tweet_text_element.text
                    
                    # Extract timestamp
                    time_element = tweet_element.find_element(By.CSS_SELECTOR, 'time')
                    date_str = time_element.get_attribute('datetime')
                    
                    if date_str:
                        # Parse ISO format datetime
                        tweet_datetime = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                        formatted_date = tweet_datetime.strftime("%Y-%m-%d")
                    else:
                        # Fallback to text content
                        date_text = time_element.text
                        formatted_date = parse_twitter_date(date_text)
                    
                    # Create tweet object
                    tweet_obj = {
                        "tweets": tweet_text,
                        "published_at": formatted_date
                    }
                    
                    # Check if tweet already exists (avoid duplicates)
                    if tweet_obj not in tweets_data:
                        tweets_data.append(tweet_obj)
                        logger.debug(f"Scraped tweet from @{username}: {tweet_text[:50]}...")
                    
                except NoSuchElementException:
                    continue
                except Exception as e:
                    logger.warning(f"Error extracting tweet data: {e}")
                    continue
            
            # Scroll down to load more tweets
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(3)
            
            # Check if new content loaded
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                scroll_attempts += 1
            else:
                scroll_attempts = 0
            last_height = new_height
        
        logger.info(f"Successfully scraped {len(tweets_data)} tweets from @{username}")
        return tweets_data
        
    except Exception as e:
        error_msg = f"Error scraping Twitter user '@{username}': {e}"
        logger.error(error_msg)
        print(error_msg)
        return []
    
    finally:
        if driver:
            driver.quit()
            logger.info("Chrome driver closed")


def scrape_crypto_tweets(queries: list[str] = ["cryptocurrency OR crypto", "altcoin or altcoins"], max_tweets=100, since_date="2025-04-01"):
    """Scrape tweets related to cryptocurrency topics.

    Args:
        queries (list[str]): List of search queries to look for tweets about. Defaults to common crypto terms.
        max_tweets (int): Maximum number of tweets to scrape. Defaults to 100.
        since_date (str): Date to search tweets from in YYYY-MM-DD format. Defaults to "2025-04-01".

    Returns:
        list: A list of dictionaries containing tweet data with 'tweets' and 'published_at' fields.
              Returns empty list if scraping fails.
    """
    driver = None
    try:
        logger.info(f"Starting crypto tweets scraping with shared driver session since {since_date}")
        
        # Setup driver and login once
        driver = setup_chrome_driver()
        if not login_to_twitter(driver):
            logger.error("Failed to login to Twitter. Cannot proceed with scraping.")
            return []
        
        all_tweets = []
        tweets_per_query = max_tweets // len(queries) if len(queries) > 0 else max_tweets
        
        for query in queries:
            logger.info(f"Scraping query: {query}")
            tweets = scrape_twitter_search(query, tweets_per_query, driver, since_date)
            all_tweets.extend(tweets)
            
            if len(all_tweets) >= max_tweets:
                break
        
        # Remove duplicates and limit to max_tweets
        unique_tweets = []
        seen_tweets = set()
        
        for tweet in all_tweets:
            tweet_text = tweet["tweets"]
            if tweet_text not in seen_tweets:
                seen_tweets.add(tweet_text)
                unique_tweets.append(tweet)
                
            if len(unique_tweets) >= max_tweets:
                break
        
        logger.info(f"Scraped {len(unique_tweets)} unique crypto-related tweets")
        return unique_tweets
        
    except Exception as e:
        error_msg = f"Error scraping crypto tweets: {e}"
        logger.error(error_msg)
        print(error_msg)
        return []
    
    finally:
        if driver:
            driver.quit()
            logger.info("Chrome driver closed after completing all queries")
