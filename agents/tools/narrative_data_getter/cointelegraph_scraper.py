import logging
import random
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException
from datetime import datetime
import time
import re
from dotenv import load_dotenv, find_dotenv

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

# User agents for rotation
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
]


def _random_delay(min_seconds=2, max_seconds=8):
    """Generate random delay between specified range.
    
    Args:
        min_seconds (int): Minimum delay in seconds. Defaults to 2.
        max_seconds (int): Maximum delay in seconds. Defaults to 8.
    """
    delay = random.uniform(min_seconds, max_seconds)
    logger.debug(f"Waiting for {delay:.2f} seconds")
    time.sleep(delay)


def _setup_chrome_driver():
    """Set up Chrome driver with enhanced stealth options and random user agent.

    Returns:
        webdriver.Chrome: Configured Chrome WebDriver instance.
    """
    chrome_options = Options()
    
    # Random user agent selection
    user_agent = random.choice(USER_AGENTS)
    logger.info(f"Using user agent: {user_agent}")
    
    # Enhanced stealth options
    chrome_options.add_argument("--headless")  # Run in background
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
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


def _gradual_scroll(driver, scroll_pause_time=2.0):
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
        scroll_down_length = 800
        driver.execute_script(f"window.scrollBy(0, {scroll_down_length});")
        time.sleep(random.uniform(0.5, 1.5))
    
    # Wait for new content to load
    time.sleep(scroll_pause_time)
    
    new_height = driver.execute_script("return window.pageYOffset + window.innerHeight")
    return new_height != last_height


def _smart_scroll_and_wait(driver, retry_count=0, max_retries=3):
    """Smart scrolling that handles content loading issues.
    
    Args:
        driver (webdriver.Chrome): The Chrome WebDriver instance.
        retry_count (int): Current retry attempt.
        max_retries (int): Maximum number of retries.
        
    Returns:
        bool: True if scrolling was successful, False if max retries reached.
    """
    try:
        # Check current scroll position
        current_scroll = driver.execute_script("return window.pageYOffset")
        
        # Gradual scroll down
        success = _gradual_scroll(driver, scroll_pause_time=3.0)
        
        # Additional wait for content loading
        _random_delay(2, 4)
        
        return success
        
    except Exception as e:
        logger.warning(f"Error during smart scroll (attempt {retry_count + 1}): {e}")
        if retry_count < max_retries:
            return _smart_scroll_and_wait(driver, retry_count + 1, max_retries)
        return False


def _find_article_links_with_retry(driver, existing_links, max_retries=3):
    """Find article links with retry mechanism for content loading issues.
    
    Args:
        driver (webdriver.Chrome): The Chrome WebDriver instance.
        existing_links (list): List of already found article links.
        max_retries (int): Maximum number of retries.
        
    Returns:
        list: New article links found.
    """
    new_links = []
    
    for retry in range(max_retries + 1):
        try:
            logger.debug(f"Searching for article links (attempt {retry + 1})")
            
            # Find article elements
            elements = driver.find_elements(By.CSS_SELECTOR, 'a[href*="/news/"]')
            logger.debug(f"Found {len(elements)} potential article elements")
            
            initial_count = len(new_links)
            
            for element in elements:
                try:
                    href = element.get_attribute('href')
                    if not href or '/news/' not in href:
                        continue
                        
                    # Check if we already have this link
                    existing_urls = [link['url'] for link in existing_links + new_links]
                    if href in existing_urls:
                        continue
                    
                    # Try to get title from various sources
                    title_text = None
                    
                    # Method 1: Direct text content
                    if element.text and element.text.strip():
                        title_text = element.text.strip()
                    
                    # Method 2: Find child text elements
                    if not title_text:
                        try:
                            text_elements = element.find_elements(By.XPATH, './/*[text()]')
                            for text_elem in text_elements:
                                text_content = text_elem.get_attribute('textContent')
                                if text_content and text_content.strip() and len(text_content.strip()) > 10:
                                    title_text = text_content.strip()
                                    break
                        except:
                            pass
                    
                    # Method 3: Try title attribute
                    if not title_text:
                        title_text = element.get_attribute('title')
                    
                    # Method 4: Try aria-label
                    if not title_text:
                        title_text = element.get_attribute('aria-label')
                    
                    if title_text and len(title_text.strip()) > 10:
                        new_links.append({
                            'url': href,
                            'title': title_text.strip()
                        })
                        
                except Exception as e:
                    logger.debug(f"Error processing individual element: {e}")
                    continue
            
            new_count = len(new_links) - initial_count
            logger.debug(f"Found {new_count} new article links in attempt {retry + 1}")
            
            # If we found new links, break out of retry loop
            if new_count > 0:
                break
                
            # If no new links found and we have retries left, try scrolling strategy
            if retry < max_retries:
                logger.info(f"No new links found on attempt {retry + 1}, trying scroll strategy")
                
                # Scroll up to potentially reload content
                current_scroll = driver.execute_script("return window.pageYOffset")
                if current_scroll > 100:
                    scroll_up_amount = min(300, current_scroll // 2)
                    driver.execute_script(f"window.scrollBy(0, -{scroll_up_amount});")
                    logger.debug(f"Scrolled up by {scroll_up_amount}px")
                    time.sleep(random.uniform(2, 3))
                
                # Wait for content to load
                _random_delay(3, 5)
                
                # Try a small scroll down to trigger content loading
                driver.execute_script("window.scrollBy(0, 200);")
                time.sleep(random.uniform(1, 2))
                
        except Exception as e:
            logger.warning(f"Error in link finding attempt {retry + 1}: {e}")
            if retry < max_retries:
                _random_delay(2, 4)
                continue
            else:
                break
    
    logger.info(f"Total new links found: {len(new_links)}")
    return new_links


def _parse_cointelegraph_date(date_str):
    """Parse Cointelegraph date format to YYYY-MM-DD format.

    Args:
        date_str (str): Date string from Cointelegraph.

    Returns:
        str: Formatted date string in YYYY-MM-DD format.
    """
    try:
        date_str = re.sub(r'\s+', ' ', date_str.strip())
        
        date_formats = [
            "%Y-%m-%dT%H:%M:%S.%fZ",    # 2025-06-24T07:59:41.000Z
            "%Y-%m-%dT%H:%M:%SZ",       # 2025-06-24T07:59:41Z
            "%Y-%m-%dT%H:%M:%S",        # 2025-06-24T07:59:41
            "%Y-%m-%d"                  # 2025-06-24
        ]
        for date_format in date_formats:
            try:
                parsed_date = datetime.strptime(date_str, date_format)
                return parsed_date.strftime("%Y-%m-%d")
            except ValueError:
                logger.debug(f"Date format '{date_str}' does not match expected formats")
        logger.warning(f"Could not parse date {date_str} with any known format")
        return datetime.now().strftime("%Y-%m-%d")
        
    except Exception as e:
        logger.warning(f"Error parsing date {date_str}: {e}")
        return datetime.now().strftime("%Y-%m-%d")


def _scrape_article_content(driver, article_url):
    """Scrape the full content of a single article.

    Args:
        driver (webdriver.Chrome): The Chrome WebDriver instance.
        article_url (str): URL of the article to scrape.

    Returns:
        str: The article content/description.
    """
    try:
        driver.get(article_url)
        _random_delay(2, 5)
        
        # Wait for article content to load
        wait = WebDriverWait(driver, 15)
        
        # Try different selectors for article content
        content_selectors = [
            'div.post-content',
            'div.article-content',
            'div.content',
            'article .post-content',
            'article .article-content',
            '.post__content',
            '.article__content',
            '[class*="content"]',
            'article p'
        ]
        
        content = ""
        for selector in content_selectors:
            try:
                content_element = wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                )
                content_text = content_element.get_attribute('textContent')
                if content_text:
                    content = content_text.strip()
                    if content and len(content) > 100:  # Valid content found
                        break
            except TimeoutException:
                continue
        
        # If no structured content found, try to get all paragraphs
        if not content or len(content) < 100:
            try:
                paragraphs = driver.find_elements(By.CSS_SELECTOR, 'article p, .content p, .post-content p')
                paragraph_texts = []
                for p in paragraphs:
                    p_text = p.get_attribute('textContent')
                    if p_text and p_text.strip():
                        paragraph_texts.append(p_text.strip())
                content = ' '.join(paragraph_texts)
            except:
                pass
        
        # Clean up content
        content = re.sub(r'\s+', ' ', content).strip()
        
        # Limit content length
        max_content_length = 3000
        if len(content) > max_content_length:
            content = content[:max_content_length] + "..."
        
        return content if content else "Content not available"
        
    except Exception as e:
        logger.warning(f"Error scraping article content from {article_url}: {e}")
        return "Content not available"


def scrape_cointelegraph_news(max_articles=50):
    """Scrape news articles from Cointelegraph.

    Args:
        max_articles (int): Maximum number of articles to scrape. Defaults to 50.

    Returns:
        list: A list of dictionaries containing news data with 'title', 'description', 'source', and 'published_at' fields.
              Returns empty list if scraping fails.

    Raises:
        Exception: If there's an error during the scraping process.
    """
    driver = None
    try:
        logger.info(f"Starting Cointelegraph news scraping for {max_articles} articles")
        driver = _setup_chrome_driver()
        
        # Navigate to Cointelegraph news page
        base_url = "https://cointelegraph.com/tags/altcoin"
        driver.get(base_url)
        logger.info(f"Navigating to Cointelegraph: {base_url}")
        
        _random_delay(3, 6)
        
        articles_data = []
        page = 0
        no_new_links_count = 0  # Track consecutive failures to find new links
        max_no_new_links = 3    # Max consecutive failures before giving up

        WebDriverWait(driver, 15)
        
        # Try different selectors for article links       
        article_links = []
        while len(article_links) < max_articles and no_new_links_count < max_no_new_links:
            logger.info(f"Searching for article links on page {page + 1} (found {len(article_links)} so far)")
            
            # Use the new smart link finding function
            new_links = _find_article_links_with_retry(driver, article_links)
            
            if new_links:
                article_links.extend(new_links)
                no_new_links_count = 0  # Reset counter since we found new links
                logger.info(f"Found {len(new_links)} new links. Total: {len(article_links)}")
            else:
                no_new_links_count += 1
                logger.warning(f"No new links found (attempt {no_new_links_count}/{max_no_new_links})")
                
                if no_new_links_count < max_no_new_links:
                    # Try smart scrolling strategy
                    scroll_success = _smart_scroll_and_wait(driver, retry_count=no_new_links_count - 1)
                    if not scroll_success:
                        logger.warning("Smart scrolling failed, trying one more time with basic scroll")
                        _gradual_scroll(driver, scroll_pause_time=4.0)
                    
                    # Wait a bit longer between failed attempts
                    _random_delay(4, 7)
                else:
                    logger.info("Max consecutive failures reached, stopping link search")
                    break
            
            # If we found new links, continue with normal scrolling
            if new_links and len(article_links) < max_articles:
                scroll_success = _smart_scroll_and_wait(driver)
                WebDriverWait(driver, 10)
            
            page += 1
        
        # Process articles from gathered links
        for article_link in article_links:
            if len(articles_data) >= max_articles:
                break
            
            try:
                article_url = article_link['url']
                title = article_link['title']
                
                if not article_url.startswith('http'):
                    article_url = f"https://cointelegraph.com{article_url}"
                
                logger.info(f"Scraping article: {title[:50]}.... Article URL: {article_url}")
                
                # Get article content
                description = _scrape_article_content(driver, article_url)
                
                # Try to extract date from the article page
                try:
                    date_selectors = [
                        'time',
                        '.post-meta time',
                        '.article-meta time',
                        '[datetime]',
                        '.date',
                        '.published-date',
                        '.post-date'
                    ]
                    
                    published_at = None
                    for date_selector in date_selectors:
                        try:
                            date_element = driver.find_element(By.CSS_SELECTOR, date_selector)
                            date_text = date_element.get_attribute('datetime') or date_element.get_attribute('textContent')
                            if date_text:
                                published_at = _parse_cointelegraph_date(date_text)
                                break
                        except:
                            continue
                    
                    if not published_at:
                        published_at = datetime.now().strftime("%Y-%m-%d")
                        
                except:
                    published_at = datetime.now().strftime("%Y-%m-%d")
                
                # Create article object
                article_obj = {
                    "title": title,
                    "description": description,
                    "source": "Cointelegraph News",
                    "published_at": published_at,
                }
                
                if article_obj not in articles_data:
                    articles_data.append(article_obj)
                logger.debug(f"Scraped article: {title[:50]}... ({len(articles_data)}/{max_articles})")
                
                # Random delay between articles
                _random_delay(1, 3)
                
            except Exception as e:
                logger.warning(f"Error processing article {article_link.get('url', 'unknown')}: {e}")
                continue
        
        # Try to navigate to next page or scroll for more content
        if len(articles_data) < max_articles:
            try:
                _gradual_scroll(driver, scroll_pause_time=3.0)
                _random_delay(3, 6)
                
            except Exception as e:
                logger.debug(f"Could not load more content: {e}")
                # break

        logger.info(f"Successfully scraped {len(articles_data)} articles from Cointelegraph")
        return articles_data
        
    except Exception as e:
        error_msg = f"Error scraping Cointelegraph news: {e}"
        logger.error(error_msg)
        print(error_msg)
        return []
    
    finally:
        if driver:
            driver.quit()
            logger.info("Chrome driver closed")


if __name__ == "__main__":
    # Example usage
    articles = scrape_cointelegraph_news(max_articles=100)
    for article in articles:
        print(f"Title: {article['title']}\nDescription: {article['description']}\nSource: {article['source']}\nPublished At: {article['published_at']}\n")
        print("="*80)
