"""
Database utilities for MongoDB and InfluxDB connections
"""
import os
from dotenv import load_dotenv
from pymongo import MongoClient
from influxdb_client import InfluxDBClient

# Load environment variables
load_dotenv()

def get_mongodb_client():
    """
    Returns a MongoDB client using connection details from environment variables
    """
    mongodb_uri = os.getenv("MONGODB_URI")
    if not mongodb_uri:
        raise ValueError("MONGODB_URI environment variable not set")
    
    client = MongoClient(mongodb_uri)
    return client

def get_mongodb_database():
    """
    Returns the MongoDB database object
    """
    client = get_mongodb_client()
    db_name = os.getenv("MONGODB_DATABASE", "crypto_analytics")
    return client[db_name]

def get_influxdb_client():
    """
    Returns an InfluxDB client using connection details from environment variables
    """
    url = os.getenv("INFLUXDB_URL")
    token = os.getenv("INFLUXDB_TOKEN")
    org = os.getenv("INFLUXDB_ORG")
    
    if not all([url, token, org]):
        raise ValueError("InfluxDB environment variables not properly set")
    
    client = InfluxDBClient(url=url, token=token, org=org)
    return client

def get_influxdb_write_api():
    """
    Returns an InfluxDB write API object
    """
    client = get_influxdb_client()
    return client.write_api()

def get_influxdb_query_api():
    """
    Returns an InfluxDB query API object
    """
    client = get_influxdb_client()
    return client.query_api()
