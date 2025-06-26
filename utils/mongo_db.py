from pymongo import MongoClient
from dotenv import find_dotenv, load_dotenv
from os import getenv

load_dotenv(find_dotenv())

uri = str(getenv("MONGODB_URI"))
database_name = str(getenv("MONGODB_DATABASE"))

client = MongoClient(uri)

database = client[database_name]


def insert_documents(collection_name: str, documents: list):
    """Insert a documents into a specified collection."""
    try:
        collection = database[collection_name]
        collection.insert_many(documents)
        return True
    except Exception as e:
        return f"Error inserting documents: {str(e)}"


def retrieve_documents(collection_name: str):
    """Retrieve all documents from a specified collection."""
    try:
        collection = database[collection_name]
        return list(collection.find({}))
    except Exception as e:
        return f"Error retrieving documents: {str(e)}"


def delete_collection(name: str):
    """Delete a collection from the database."""
    try:
        database.drop_collection(name)
        return True
    except Exception as e:
        return f"Error deleting collection: {str(e)}"
    finally:
        client.close()
