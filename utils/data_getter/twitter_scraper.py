import json
import logging
import random
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from datetime import datetime, timedelta
import time
import re
from dotenv import load_dotenv, find_dotenv
from os import getenv

# Load environment variables
load_dotenv(find_dotenv())

# Configure logger
logging.basicConfig(
    level=logging.INFO,  # Set to DEBUG to see debug messages too
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # This outputs to console/terminal
    ]
)
logger = logging.getLogger(__name__)

# Get Twitter credentials from environment
TWITTER_EMAIL = getenv("TWITTER_EMAIL_MAIN")
TWITTER_PASSWORD = getenv("TWITTER_PASSWORD_MAIN")
TWITTER_USERNAME = getenv("TWITTER_USERNAME_MAIN")

# User agents for rotation
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
]


def random_delay(min_seconds=3, max_seconds=12):
    """Generate random delay between specified range.
    
    Args:
        min_seconds (int): Minimum delay in seconds. Defaults to 3.
        max_seconds (int): Maximum delay in seconds. Defaults to 12.
    """
    delay = random.uniform(min_seconds, max_seconds)
    logger.debug(f"Waiting for {delay:.2f} seconds")
    time.sleep(delay)


def gradual_scroll(driver, scroll_pause_time=2.0):
    """Scroll the page gradually instead of jumping to bottom.
    
    Args:
        driver (webdriver.Chrome): The Chrome WebDriver instance.
        scroll_pause_time (float): Time to pause between scrolls. Defaults to 2.0.
        
    Returns:
        bool: True if new content was loaded, False otherwise.
    """
    last_height = driver.execute_script("return window.pageYOffset + window.innerHeight")
    
    # Scroll in increments
    for i in range(3):
        driver.execute_script(f"window.scrollBy(0, {random.randint(300, 800)});")
        time.sleep(random.uniform(0.5, 1.5))
    
    # Wait for new content to load
    time.sleep(scroll_pause_time)
    
    new_height = driver.execute_script("return window.pageYOffset + window.innerHeight")
    return new_height != last_height


def check_for_errors(driver):
    """Check for error messages on the page and handle them.
    
    Args:
        driver (webdriver.Chrome): The Chrome WebDriver instance.
        
    Returns:
        bool: True if errors were found and handled, False otherwise.
    """
    error_indicators = [
        "Something went wrong",
        "Try again",
        "Oops! Something went wrong",
        "Sorry, something went wrong",
        "We're sorry, but something went wrong"
    ]
    
    try:
        page_text = driver.find_element(By.TAG_NAME, "body").text.lower()
        
        for error_text in error_indicators:
            if error_text.lower() in page_text:
                logger.warning(f"Error detected on page: {error_text}")
                random_delay(5, 15)  # Wait longer before refresh
                driver.refresh()
                random_delay(5, 10)  # Wait after refresh
                return True
                
    except Exception as e:
        logger.debug(f"Error checking page for errors: {e}")
        
    return False


def setup_chrome_driver():
    """Set up Chrome driver with enhanced stealth options and random user agent.

    Returns:
        webdriver.Chrome: Configured Chrome WebDriver instance.
    """
    chrome_options = Options()
    
    # Random user agent selection
    user_agent = random.choice(USER_AGENTS)
    logger.info(f"Using user agent: {user_agent}")
    
    # Enhanced stealth options
    # chrome_options.add_argument("--headless")  # Comment out to see browser running
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument("--disable-web-security")
    chrome_options.add_argument("--allow-running-insecure-content")
    chrome_options.add_argument("--disable-features=VizDisplayCompositor")
    chrome_options.add_argument(f"--user-agent={user_agent}")
    
    # Additional stealth options
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-plugins")
    chrome_options.add_argument("--disable-images")  # Faster loading
    chrome_options.add_argument("--disable-javascript-harmony-shipping")
    chrome_options.add_argument("--disable-background-timer-throttling")
    chrome_options.add_argument("--disable-backgrounding-occluded-windows")
    chrome_options.add_argument("--disable-renderer-backgrounding")
    chrome_options.add_argument("--disable-features=TranslateUI")
    chrome_options.add_argument("--disable-ipc-flooding-protection")
    
    # Randomize window size slightly
    width = random.randint(1900, 1920)
    height = random.randint(1000, 1080)
    chrome_options.add_argument(f"--window-size={width},{height}")
    
    try:
        driver = webdriver.Chrome(options=chrome_options)
        
        # Execute script to hide automation indicators
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        logger.info("Chrome driver initialized successfully with enhanced stealth")
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
        random_delay(2, 4)
        
        # Handle potential username prompt (sometimes Twitter asks for username instead of email)
        try:
            username_field = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'input[data-testid="ocfEnterTextTextInput"]'))
            )
            username_field.clear()
            username_field.send_keys(str(TWITTER_USERNAME))
            next_button = driver.find_element(By.XPATH, '//span[text()="Next"]')
            next_button.click()
            random_delay(2, 4)
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
        list: A list of dictionaries containing tweet data with 'tweet', 'published_at', and 'tweet_url' fields.
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
        search_query = f"{query} since:{since_date} lang:en"
        search_url = f"https://twitter.com/search?q={search_query}&src=typed_query&f=live"
        driver.get(search_url)
        logger.info(f"Navigating to Twitter search URL: {search_url}")
        
        random_delay(5, 8)
        
        # Check for errors on initial page load
        if check_for_errors(driver):
            logger.info("Retrying after handling page error")
            driver.get(search_url)
            random_delay(5, 8)
        
        tweets_data = []
        scroll_attempts = 0
        max_scroll_attempts = 10
        
        while len(tweets_data) < max_tweets and scroll_attempts < max_scroll_attempts:
            # Check for errors periodically
            if scroll_attempts > 0 and scroll_attempts % 3 == 0:
                if check_for_errors(driver):
                    logger.info("Retrying search after handling page error")
                    driver.get(search_url)
                    random_delay(5, 8)
                    continue
            
            tweet_elements = driver.find_elements(By.CSS_SELECTOR, '[data-testid="tweet"]')
            
            for tweet_element in tweet_elements:
                if len(tweets_data) >= max_tweets:
                    break
                    
                try:
                    # Extract tweet text
                    tweet_text_element = tweet_element.find_element(By.CSS_SELECTOR, '[data-testid="tweetText"]')
                    tweet_text = tweet_text_element.text
                    
                    # Extract timestamp and link
                    time_element = tweet_element.find_element(By.CSS_SELECTOR, 'time')
                    tweet_link = time_element.find_element(By.XPATH, './..').get_attribute('href')
                    date_str = time_element.get_attribute('datetime')
                    
                    if date_str:
                        tweet_datetime = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                        formatted_date = tweet_datetime.strftime("%Y-%m-%d")
                    else:
                        date_text = time_element.text
                        formatted_date = parse_twitter_date(date_text)
                    if len(tweet_text) > 60:
                        tweet_obj = {
                            "tweet": tweet_text,
                            "published_at": formatted_date,
                            "tweet_url": tweet_link
                        }
                    
                        if tweet_obj not in tweets_data:
                            tweets_data.append(tweet_obj)
                            logger.debug(f"Scraped tweet: {tweet_text[:50]}...")
                except NoSuchElementException:
                    continue
                except Exception as e:
                    logger.warning(f"Error extracting tweet data: {e}")
                    continue
            
            # Use gradual scrolling instead of jumping to bottom
            content_loaded = gradual_scroll(driver, scroll_pause_time=random.uniform(2, 4))
            
            if not content_loaded:
                scroll_attempts += 1
            else:
                scroll_attempts = 0
            
            # Random delay between scroll attempts
            random_delay(1, 3)
        
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


def scrape_crypto_tweets(
        queries: list[str] = [
            "cryptocurrency", 
            "altcoin OR altcoins", 
            "RWA OR 'real-world assets'", 
            "'layer 1'", 
            "'layer 2'", 
            "blockchain", 
            "defi OR 'decentralized finance'", 
            "dex OR 'decentralized exchange'", 
            "AI OR 'artificial intelligence' AND token", 
            "Depin", 
            "token AND 'AI Agent'", 
            "gamefi", 
            "'institutional adoption' AND 'cryptocurrency'"
            ], 
        max_tweets=1500, since_date="2025-01-01"):
    """Scrape tweets related to cryptocurrency topics.

    Args:
        queries (list[str]): List of search queries to look for tweets about. Defaults to common crypto terms.
        max_tweets (int): Maximum number of tweets to scrape. Defaults to 100.
        since_date (str): Date to search tweets from in YYYY-MM-DD format. Defaults to "2025-01-01".

    Returns:
        list: A list of dictionaries containing tweet data with 'tweet', 'published_at' and 'tweet_url' fields.
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
            
            # Random delay between queries to avoid rate limiting
            if query != queries[-1]:  # Don't delay after the last query
                random_delay(5, 15)
            
            if len(all_tweets) >= max_tweets:
                break
        
        # Remove duplicates and limit to max_tweets
        unique_tweets = []
        seen_tweets = set()
        
        for tweet in all_tweets:
            tweet_text = tweet["tweet"]
            tweet_url = tweet["tweet_url"]
            if (tweet_text, tweet_url) not in seen_tweets:
                seen_tweets.add((tweet_text, tweet_url))
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

# if __name__ == "__main__":
#     result = scrape_crypto_tweets(max_tweets=500)
#     json_result = json.dumps(result, indent=2, ensure_ascii=False)
#     with open("crypto_tweets.json", "w", encoding="utf-8") as f:
#         f.write(json_result)
