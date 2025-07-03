from pymongo import MongoClient
from dotenv import find_dotenv, load_dotenv
from os import getenv
import logging


# Configure logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
    ]
)

logger = logging.getLogger(__name__)

load_dotenv(find_dotenv())

uri = str(getenv("MONGODB_URI"))
database_name = str(getenv("MONGODB_DATABASE"))

client = MongoClient(uri)

database = client[database_name]


def insert_documents(collection_name: str, documents: list[dict]) -> bool:
    """Insert documents into a specified collection.

    Args:
        collection_name (str): The name of the collection to insert documents into.
        documents (list): A list of documents to insert into the collection.

    Returns:
        bool: True if insertion is successful | str: error message string if failed.
    """
    try:
        logger.info(f"Inserting {len(documents)} documents into collection: {collection_name}")
        collection = database[collection_name]
        collection.insert_many(documents)
        logger.info(f"Successfully inserted {len(documents)} documents into {collection_name}")
        return True
    except Exception as e:
        error_msg = f"Error inserting documents: {str(e)}"
        logger.error(error_msg)
        return False


def retrieve_documents(collection_name: str) -> list[dict]:
    """Retrieve all documents from a specified collection.

    Args:
        collection_name (str): The name of the collection to retrieve documents from.

    Returns:
        list (list): List of documents if successful | message (str): error message string if failed.
    """
    try:
        logger.info(f"Retrieving documents from collection: {collection_name}")
        collection = database[collection_name]
        documents = list(collection.find({}, {'_id': 0}))  # Exclude MongoDB's default _id field
        if documents:
            logger.info(f"Successfully retrieved {len(documents)} documents from {collection_name}")
            return documents
        else:
            logger.info(f"No documents found in collection: {collection_name}")
            return []
    except Exception as e:
        error_msg = f"Error retrieving documents: {str(e)}"
        logger.error(error_msg)
        return []


def delete_collection(name: str):
    """
    Delete a collection from the database.

    Args:
        name (str): The name of the collection to delete.

    Returns:
        bool: True if deletion is successful
        str: error message string if failed.
    """
    try:
        logger.info(f"Deleting collection: {name}")
        database.drop_collection(name)
        logger.info(f"Successfully deleted collection: {name}")
        return True
    except Exception as e:
        error_msg = f"Error deleting collection: {str(e)}"
        logger.error(error_msg)
        return False
    finally:
        client.close()
