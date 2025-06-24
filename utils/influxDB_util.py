import os, json
from dotenv import load_dotenv
from typing import Dict, List, Any, Optional, Union
from influxdb_client_3 import InfluxDBClient3, Point, WritePrecision
from datetime import datetime
import pandas as pd

# Load environment variables
load_dotenv()

# InfluxDB configuration
INFLUXDB_URL = os.getenv("INFLUXDB_URL", "http://localhost:8181")
INFLUXDB_TOKEN = os.getenv("INFLUXDB_TOKEN")
INFLUXDB_ORG = os.getenv("INFLUXDB_ORG", "my-org")
INFLUXDB_HTTP_HEADER = os.getenv("INFLUXDB_HTTP_HEADER")

def get_influxdb_client() -> InfluxDBClient3:
    """
    Create and return an InfluxDB client with the configured settings.
    """
    headers = {}
    if INFLUXDB_HTTP_HEADER:
        # If custom HTTP headers are provided, parse and add them
        try:
            headers = json.loads(INFLUXDB_HTTP_HEADER)
        except json.JSONDecodeError:
            print("Warning: Could not parse INFLUXDB_HTTP_HEADER as JSON")
    
    client = InfluxDBClient3(
        host=INFLUXDB_URL,
        token=INFLUXDB_TOKEN,
        headers=headers
    )
    
    return client

def write_data(
    bucket: str,
    measurement: str,
    tags: Dict[str, str],
    fields: Dict[str, Any],
    timestamp: Optional[datetime] = None
) -> bool:
    """
    Write a single data point to InfluxDB.
    
    Args:
        bucket: The bucket to write to
        measurement: The measurement name
        tags: Dictionary of tag key-value pairs
        fields: Dictionary of field key-value pairs
        timestamp: Optional timestamp (defaults to current time if None)
        
    Returns:
        bool: True if write was successful, False otherwise
    """
    client = get_influxdb_client()
    try:
        point = Point(measurement)
        
        # Add all tags
        for tag_key, tag_value in tags.items():
            point = point.tag(tag_key, tag_value)
            
        # Add all fields
        for field_key, field_value in fields.items():
            point = point.field(field_key, field_value)
        
        # Set timestamp if provided, otherwise use current time
        if timestamp:
            point = point.time(timestamp, WritePrecision.NS)
            
        # Write the point
        client.write(bucket=bucket, record=point)
        return True
    except Exception as e:
        print(f"Error writing to InfluxDB: {e}")
        return False
    finally:
        client.close()

def write_batch_data(
    bucket: str,
    points: List[Dict[str, Any]]
) -> bool:
    """
    Write multiple data points to InfluxDB.
    
    Args:
        bucket: The bucket to write to
        points: List of dictionaries with keys 'measurement', 'tags', 'fields', and 'timestamp' (optional)
        
    Returns:
        bool: True if write was successful, False otherwise
    """
    client = get_influxdb_client()
    try:
        point_list = []
        
        for p in points:
            point = Point(p['measurement'])
            
            # Add all tags
            for tag_key, tag_value in p.get('tags', {}).items():
                point = point.tag(tag_key, tag_value)
                
            # Add all fields
            for field_key, field_value in p.get('fields', {}).items():
                point = point.field(field_key, field_value)
            
            # Set timestamp if provided
            timestamp = p.get('timestamp')
            if timestamp:
                point = point.time(timestamp, WritePrecision.NS)
                
            point_list.append(point)
            
        # Write the points
        client.write(bucket=bucket, record=point_list)
        return True
    except Exception as e:
        print(f"Error writing batch to InfluxDB: {e}")
        return False
    finally:
        client.close()

def delete_data(
    bucket: str,
    start: Union[datetime, str],
    stop: Union[datetime, str],
    predicate: str = None
) -> bool:
    """
    Delete data from InfluxDB within a time range and optional predicate.
    
    Args:
        bucket: The bucket to delete from
        start: Start time for deletion range
        stop: Stop time for deletion range
        predicate: Optional predicate to filter which data to delete (e.g., '_measurement="cpu"')
        
    Returns:
        bool: True if deletion was successful, False otherwise
    """
    client = get_influxdb_client()
    try:
        client.delete(bucket=bucket, start=start, stop=stop, predicate=predicate)
        return True
    except Exception as e:
        print(f"Error deleting data from InfluxDB: {e}")
        return False
    finally:
        client.close()

def query_data(
    bucket: str,
    query: str
) -> pd.DataFrame:
    """
    Query data from InfluxDB using SQL.
    
    Args:
        bucket: The bucket to query
        query: The SQL query to execute
        
    Returns:
        pd.DataFrame: DataFrame containing the query results
    """
    client = get_influxdb_client()
    try:
        result = client.query(query=query, database=bucket)
        return result
    except Exception as e:
        print(f"Error querying data from InfluxDB: {e}")
        return pd.DataFrame()
    finally:
        client.close()

def query_data_by_time(
    bucket: str,
    measurement: str,
    start: Union[datetime, str],
    stop: Union[datetime, str],
    fields: List[str] = None,
    tags: Dict[str, str] = None
) -> pd.DataFrame:
    """
    Query data from InfluxDB using time range and filters.
    
    Args:
        bucket: The bucket to query
        measurement: The measurement to query
        start: Start time for query
        stop: Stop time for query
        fields: Optional list of field names to include
        tags: Optional dictionary of tag filters
        
    Returns:
        pd.DataFrame: DataFrame containing the query results
    """
    # Build the SQL query
    fields_str = "*" if not fields else ", ".join([f'"{field}"' for field in fields])
    
    query = f'SELECT {fields_str} FROM "{measurement}" WHERE time >= \'{start}\' AND time <= \'{stop}\''
    
    # Add tag filters
    if tags:
        for tag_key, tag_value in tags.items():
            query += f' AND "{tag_key}" = \'{tag_value}\''
            
    return query_data(bucket, query)
