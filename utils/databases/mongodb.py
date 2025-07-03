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

if __name__ == "__main__":
    # Example usage
    collection_name = "bitcoin"
    documents = [
        {
            "fundamental_data": {
                "name": "Bitcoin",
                "symbol": "BTC",
                "market_cap": 800000000000,
                "price": 40000,
                "volume_24h": 30000000000,
                "circulating_supply": 19000000,
                "total_supply": 21000000
            },
            "prices": [
                [
                    1711843200000,
                    69702.3087473573
                ],
                [
                    1711929600000,
                    71246.9514406015
                ],
                [
                    1711983682000,
                    68887.7495158568
                ],
            ]
        }
    ]
    
    # Insert documents
    insert_result = insert_documents(collection_name, documents)
    print(insert_result)
    
    # Retrieve documents
    retrieve_result = retrieve_documents(collection_name)
    print(retrieve_result)

    fundamental_data = retrieve_result[0]["fundamental_data"]
    print(f"Fundamental Data: {fundamental_data}")
    
    # Delete collection
    delete_result = delete_collection(collection_name)
    print(delete_result)
