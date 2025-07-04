import requests
import logging
import re
import io
import os
import sys

from bs4 import BeautifulSoup
from urllib.parse import urlparse
from PyPDF2 import PdfReader
from dotenv import load_dotenv, find_dotenv
from os import getenv
from datetime import datetime, timedelta

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.join(current_dir, '..', '..')
sys.path.insert(0, project_root)

from utils.databases.mongodb import insert_documents, retrieve_documents, delete_document

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


def extract_text_from_pdf(pdf_content: bytes) -> str:
    """Extract text content from PDF bytes.

    Args:
        pdf_content (bytes): PDF file content as bytes.

    Returns:
        str: Extracted text from the PDF.
    """
    try:
        # Create a BytesIO object from the PDF content
        pdf_file = io.BytesIO(pdf_content)
        
        # Create a PDF reader object
        pdf_reader = PdfReader(pdf_file)
        
        # Extract text from all pages
        text_content = ""
        total_pages = len(pdf_reader.pages)
        
        logger.info(f"Extracting text from {total_pages} pages")
        
        for page_num, page in enumerate(pdf_reader.pages, 1):
            try:
                page_text = page.extract_text()
                if page_text:
                    text_content += page_text + "\n"
                logger.debug(f"Extracted text from page {page_num}/{total_pages}")
            except Exception as e:
                logger.warning(f"Error extracting text from page {page_num}: {e}")
                continue
        
        logger.info(f"Successfully extracted {len(text_content)} characters from PDF")
        return text_content
        
    except Exception as e:
        logger.error(f"Error extracting text from PDF: {e}")
        return ""


def scrape_whitepaper(url: str, timeout: int = 30) -> str:
    """Scrape text content from a whitepaper URL (supports both PDF and web content).

    Args:
        url (str): The URL of the whitepaper to scrape.
        timeout (int): Request timeout in seconds. Defaults to 30.

    Returns:
        str: Cleaned text content from the whitepaper. Returns empty string if scraping fails.

    Raises:
        Exception: If there's an error during the scraping process.
    """
    try:
        logger.info(f"Scraping text content from: {url}")
        
        # Validate URL
        parsed_url = urlparse(url)
        if not parsed_url.scheme or not parsed_url.netloc:
            logger.error(f"Invalid URL provided: {url}")
            return ""
        
        # Set up headers to mimic a real browser
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        # Make the request
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()  # Raise an exception for bad status codes
        
        # Check if the URL ends with .pdf or if content type indicates PDF
        is_pdf = (url.lower().endswith('.pdf') or 
                 'application/pdf' in response.headers.get('content-type', '').lower())
        
        if is_pdf:
            logger.info("Detected PDF content, extracting text from PDF")
            # Extract text from PDF
            text_content = extract_text_from_pdf(response.content)
        else:
            logger.info("Detected web content, parsing HTML")
            # Parse HTML content
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style", "nav", "footer", "header", "aside"]):
                script.decompose()
            
            # Remove common navigation and advertisement elements
            unwanted_classes = [
                'nav', 'navigation', 'menu', 'sidebar', 'footer', 'header',
                'advertisement', 'ad', 'ads', 'cookie', 'popup', 'modal',
                'social', 'share', 'comment', 'comments'
            ]
            
            for class_name in unwanted_classes:
                for element in soup.find_all(attrs={'class': re.compile(class_name, re.I)}):
                    element.decompose()
            
            # Extract text from main content areas first
            main_content_selectors = [
                'main', 'article', '[role="main"]', '.main-content', 
                '.content', '.post-content', '.entry-content', '.article-content'
            ]
            
            text_content = ""
            
            # Try to find main content first
            for selector in main_content_selectors:
                main_element = soup.select_one(selector)
                if main_element:
                    text_content = main_element.get_text()
                    logger.debug(f"Found main content using selector: {selector}")
                    break
            
            # If no main content found, get all text
            if not text_content:
                text_content = soup.get_text()
                logger.debug("Using full page text content")
        
        # Clean the text
        cleaned_text = clean_text(text_content)
        
        content_type = "PDF" if is_pdf else "web page"
        logger.info(f"Successfully scraped {len(cleaned_text)} characters from {content_type}: {url}")
        return cleaned_text
        
    except requests.RequestException as e:
        logger.error(f"Request error while scraping {url}: {e}")
        return ""
    except Exception as e:
        logger.error(f"Error scraping whitepaper {url}: {e}")
        return ""


def clean_text(text: str) -> str:
    """Clean scraped text content by removing extra whitespace and unwanted characters.

    Args:
        text (str): Raw text content to clean.

    Returns:
        str: Cleaned text content.
    """
    if not text:
        return ""
    
    try:
        # Remove excessive whitespace and normalize line breaks
        text = re.sub(r'\s+', ' ', text)
        
        # Remove extra newlines and tabs
        text = re.sub(r'[\n\r\t]+', ' ', text)
        
        # Clean PDF artifacts (common in PDF extraction)
        text = re.sub(r'[^\w\s\.,!?;:()\-\'"/@#$%&*+=\[\]{}|\\`~]', '', text)
        
        # Remove page numbers and headers/footers (common PDF artifacts)
        text = re.sub(r'\b\d+\s*$', '', text, flags=re.MULTILINE)  # Remove trailing page numbers
        text = re.sub(r'^\s*\d+\s*', '', text, flags=re.MULTILINE)  # Remove leading page numbers
        
        # Remove repeated punctuation
        text = re.sub(r'([.!?]){2,}', r'\1', text)
        
        # Remove multiple spaces
        text = re.sub(r' {2,}', ' ', text)
        
        # Remove leading/trailing whitespace
        text = text.strip()
        
        # Remove very short lines that are likely navigation, headers, or ads
        lines = text.split('.')
        meaningful_lines = []
        
        for line in lines:
            line = line.strip()
            # Keep lines that are substantial (more than 15 characters and contain actual words)
            # Reduced from 20 to 15 for PDF content which might be more fragmented
            if len(line) > 15 and len(line.split()) > 2:
                meaningful_lines.append(line)
        
        # Rejoin meaningful content
        cleaned_text = '. '.join(meaningful_lines)
        
        # Final cleanup
        cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()
        
        # Limit text length to prevent extremely long content
        max_length = 15000  # Increased from 10,000 to 15,000 for whitepaper content
        if len(cleaned_text) > max_length:
            cleaned_text = cleaned_text[:max_length] + "..."
            logger.info(f"Text truncated to {max_length} characters")
        
        return cleaned_text
    except Exception as e:
        logger.error(f"Error cleaning text: {e}")
        return ""


def get_fundamental_data(token_id: str) -> dict:
    """Fetch fundamental data for a specific token from CoinGecko.

    Args:
        token_id (str): The ID of the token to fetch data for.

    Returns:
        dict: A dictionary containing the fundamental data of the token.
                the schema of the dictionary is as follows where "developer_data" contains information about the developer's GitHub repositories or "Not Listed" if no repositories are available.:
                {
                    "name": str,
                    "categories": list[str],
                    "description": str,
                    "link_to_whitepaper": str | "whitepaper_text": str,
                    "positive_sentiment": float,
                    "negative_sentiment": float,
                    "total_value_locked": float,
                    "market_cap": float,
                    "fully_diluted_valuation": float,
                    "total_supply": float,
                    "circulating_supply": float,
                    "max_supply": float,
                    "max_supply_infinite": bool,
                    "developer_data": dict | str,
                    "updated": datetime
                }
    """
    try:
        url = f"{COINGECKO_ENDPOINT}coins/{token_id}"
        response = requests.get(
        url=url,
        params={
            "localization": "false",
            "tickers": "false",
            "market_data": "true",
            "community_data": "true",
            "developer_data": "true",
            "sparkline": "false",
            },
        headers={
            "accept": "application/json",
            "x-cg-demo-api-key": COINGECKO_API_KEY
            }
        )

        if response.status_code != 200:
            logger.error(f"Failed to fetch categories: {response.status_code} - {response.text}")
            return {}
        
        data = response.json()

        developer_data = "Not Listed" if data.get("links").get("repos_url").get("github") == [] else data.get("developer_data", {})

        cleaned_data = {
            "name": data.get("name", ""),
            "categories": data.get("categories", []),
            "description": data.get("description", {}).get("en", ""),
            "link_to_whitepaper": data.get("links", {}).get("whitepaper", ""),
            "positive_sentiment": data.get("sentiment_votes_up_percentage", 0.0),
            "negative_sentiment": data.get("sentiment_votes_down_percentage", 0.0),
            "total_value_locked": data.get("market_data", {}).get("total_value_locked", 0.0),
            "market_cap": data.get("market_data", {}).get("market_cap", {}).get("usd", 0.0),
            "fully_diluted_valuation": data.get("market_data", {}).get("fully_diluted_valuation", {}).get("usd", 0.0),
            "total_supply": data.get("market_data", {}).get("total_supply", 0.0),
            "circulating_supply": data.get("market_data", {}).get("circulating_supply", 0.0),
            "max_supply": data.get("market_data", {}).get("max_supply", 0.0),
            "max_supply_infinite": data.get("max_supply", None),
            "developer_data": developer_data,
            "updated": datetime.now()
        }

        description_text = cleaned_data.get("description", "")
        if description_text:
            # Clean the description text
            cleaned_description = clean_text(description_text)
            cleaned_data["description"] = cleaned_description

        # extract whitepaper
        whitepaper_url = cleaned_data.get("link_to_whitepaper", "")
        if whitepaper_url:
            # Fetch and process the whitepaper content
            whitepaper_text = scrape_whitepaper(whitepaper_url, timeout=60)
            if whitepaper_text:
                cleaned_whitepaper_text = clean_text(whitepaper_text)
                cleaned_data["whitepaper_text"] = cleaned_whitepaper_text
                cleaned_data.pop("link_to_whitepaper", None)  # Remove the original link if text is available

        return cleaned_data

    except requests.RequestException as e:
        logger.error(f"Error fetching fundamental data for {token_id}: {e}")
        return {}


def get_fundamental_data_of_tokens(token_ids: list) -> list:
    """Fetch fundamental data for multiple tokens from CoinGecko.

    Args:
        token_ids (list): A list of token IDs to fetch data for.

    Returns:
        list: A list of dictionaries containing the fundamental data of the tokens.
                the schema of the dictionary is as follows where "developer_data" contains information about the developer's GitHub repositories or "Not Listed" if no repositories are available.:
                [
                    {
                        token_id: str,
                        "fundamental_data":
                            {
                                "name": str,
                                "categories": list[str],
                                "description": str,
                                "link_to_whitepaper": str | "whitepaper_text": str,
                                "positive_sentiment": float,
                                "negative_sentiment": float,
                                "total_value_locked": float,
                                "market_cap": float,
                                "fully_diluted_valuation": float,
                                "total_supply": float,
                                "circulating_supply": float,
                                "max_supply": float,
                                "max_supply_infinite": bool,
                                "developer_data": dict | str,
                                "updated": datetime
                            }
                    }
                ]
    """
    try:
        all_data = []
        for token_id in token_ids:
            logger.info(f"Fetching fundamental data for {token_id}")

            # check token collection in DB
            existing_data = retrieve_documents(token_id)
            if isinstance(existing_data, list) and existing_data and 'fundamental_data' in existing_data[0]:
                today = datetime.now()
                updated_date = existing_data[0]["updated"]
                if updated_date - today < timedelta(weeks=4):
                    all_data.append({
                        "token_id": token_id,
                        "fundamental_data": existing_data[0]
                    })
                    logger.info(f"Successfully retrieved data for {token_id} from DB")
                    continue
                else:
                    logger.info(f"Data for {token_id} is outdated, fetching new data")
                    logger.info(f"Deleting outdated data for {token_id} from DB")
                    delete_document(token_id, existing_data[0])
                    logger.info(f"Deleted outdated data for {token_id} from DB")

            data = get_fundamental_data(token_id)
            if data:
                all_data.append({
                    "token_id": token_id,
                    "fundamental_data": data
                })
                logger.info(f"Successfully fetched data for {token_id}")
            else:
                logger.warning(f"No data found for {token_id}")

        return all_data
    except Exception as e:
        logger.error(f"Error fetching fundamental data for tokens: {e}")
        return []


def save_fundamental_data_to_db(fundamental_data: list) -> dict:
    """Save fundamental data to MongoDB collection.

    Args:
        fundamental_data (list): The fundamental data to save.

    Returns:
        dict: A dictionary containing the status of the save operation.
    """
    try:
        if not fundamental_data:
            logger.warning("No fundamental data to save.")
            return {"status": "No data to save"}

        try:
            return_status = {}
            for data in fundamental_data:
                collection_name = data.get("token_id", "unknown_token")
                data_to_save = data["fundamental_data"]

                # Check if the collection already exists
                existing_data = retrieve_documents(collection_name)
                if isinstance(existing_data, list) and existing_data:
                    # If data already exists, delete it before inserting new data
                    logger.info(f"Deleting existing data for {collection_name} in DB")
                    delete_document(collection_name, existing_data[0])
                    logger.info(f"Deleted existing data for {collection_name} in DB")

                insert_documents(collection_name, [data_to_save])
                return_status[collection_name] = f"fundamental data for {collection_name} saved successfully"
                logger.info(f"Successfully saved fundamental data to {collection_name}.")

            return return_status
        except Exception as e:
            logger.error(f"Error saving fundamental data: {e}")
            return {"status": "error", "message": str(e)}
    except Exception as e:
        logger.error(f"Error saving fundamental data to DB: {e}")
        return {"status": "error", "message": str(e)}
