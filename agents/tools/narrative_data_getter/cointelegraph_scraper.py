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
        driver.execute_script(f"window.scrollBy(0, {random.randint(300, 800)});")
        time.sleep(random.uniform(0.5, 1.5))
    
    # Wait for new content to load
    time.sleep(scroll_pause_time)
    
    new_height = driver.execute_script("return window.pageYOffset + window.innerHeight")
    return new_height != last_height


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

        WebDriverWait(driver, 15)
        
        # Try different selectors for article links       
        article_links = []
        while len(article_links) < max_articles:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, 'a[href*="/news/"]')
                for element in elements:
                    href = element.get_attribute('href')
                    if href and '/news/' in href and href not in [link['url'] for link in article_links]:
                            title_element = element.find_element(By.XPATH, './/*[text()]') if element.text else element
                            title_text = title_element.get_attribute('textContent') if title_element else None
                            if not title_text:
                                title_text = element.get_attribute('title') or element.text or ""
                            title = title_text.strip() if title_text else ""
                            if title and len(title) > 10:  # Valid title
                                article_links.append({
                                    'url': href,
                                    'title': title
                                })
            except:
                logger.warning("Error finding article links, scrolling...")
                time.sleep(random.uniform(0.5, 1.0))
                pass
            _gradual_scroll(driver, scroll_pause_time=3.0)
            WebDriverWait(driver, 15)
            page += 1
            logger.info(f"Found {len(article_links)} article links on page {page}")
        
        # Process articles from gathered links
        for article_link in article_links:
            if len(articles_data) >= max_articles:
                break
            
            try:
                article_url = article_link['url']
                title = article_link['title']
                
                if not article_url.startswith('http'):
                    article_url = f"https://cointelegraph.com{article_url}"
                
                logger.info(f"Scraping article: {title[:50]}...")
                
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
