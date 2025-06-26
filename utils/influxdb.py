from influxdb_client.client.influxdb_client import InfluxDBClient
from influxdb_client.client.write.point import Point
from influxdb_client.client.write_api import ASYNCHRONOUS
from dotenv import load_dotenv, find_dotenv
from os import getenv
from datetime import datetime, timezone
from typing import List, Dict
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('influxdb_utils')

load_dotenv(find_dotenv())

BUCKET = str(getenv("INFLUXDB_BUCKET"))
TOKEN = str(getenv("INFLUXDB_TOKEN"))
ORG = str(getenv("INFLUXDB_ORG"))
URL = str(getenv("INFLUXDB_URL"))

def save_price_data(token_name: str, token_symbol: str, price_data: List[Dict]):
    """
    Saves a list of time-series price data points to InfluxDB.

    Args:
        token_name (str): The name of the token (e.g., "Bitcoin", "Ethereum").
                          This will be used as a measurement in InfluxDB.
        token_symbol (str): The symbol of the token (e.g., "BTC", "ETH").
                            This will be used as a tag in InfluxDB.
        price_data (list of dict): A list of data points. Each dictionary
                                   should represent a single point in time
                                   (like a candlestick) and must contain at least
                                   a 'time' field and other numeric fields (e.g., open, high, low, close, volume).
                                   The 'time' field can be an ISO 8601 string or a datetime object.

    Returns:
        bool: True if the write operation was successful, False otherwise.
    """
    if not all([URL, TOKEN, ORG, BUCKET]):
        logger.error("InfluxDB environment variables are not fully configured.")
        return False

    with InfluxDBClient(url=URL, token=TOKEN, org=ORG) as client:
        write_api = client.write_api(write_options=ASYNCHRONOUS)

        # convert our list of dictionaries into a list of InfluxDB 'Point' objects
        points_to_write = []

        logger.info(f"Preparing {len(price_data)} data points for '{token_name}'...")

        for entry in price_data:
            # Create a Point object for each entry.
            point = Point(measurement_name=token_name.upper()) \
                .tag("token_symbol", token_symbol.upper())

            # Add all other dictionary keys (except 'time') as "fields"
            for key, value in entry.items():
                # convert time from string to datetime
                time = entry['time']
                time = datetime.fromisoformat(time) if isinstance(time, str) else time

                point = point.time(format_timestamp(time))

                if key != "time":
                    try:
                        point = point.field(key, float(value))
                    except (ValueError, TypeError):
                        # Handle cases where a value might not be numeric
                        logger.warning(f"Skipping non-numeric value for key '{key}' in {token_name} data.")

            points_to_write.append(point)

        try:
            logger.info(f"Writing {len(points_to_write)} points to bucket '{BUCKET}'...")
            # Write the entire list of points to InfluxDB in a single batch
            write_api.write(bucket=BUCKET, org=ORG, record=points_to_write)
            logger.info("Successfully wrote data to InfluxDB.")
            return True
        except Exception as e:
            logger.error(f"An error occurred while writing to InfluxDB: {e}")
            return False
        

def get_price_data(token_symbol, start_time=None, stop_time=None, measurement="token_price"):
    """
    Retrieves time-series price data from InfluxDB for a specific token.

    Args:
        token_symbol (str): The symbol of the token (e.g., "BTC", "ETH").
                            This will be used to filter the data by tag.
        start_time (str, datetime, optional): The start time for the data query.
                                             Can be a datetime object or an ISO 8601 string.
                                             If None, will retrieve data from the earliest available point.
        stop_time (str, datetime, optional): The end time for the data query.
                                           Can be a datetime object or an ISO 8601 string.
                                           If None, will retrieve data up to the latest available point.
        measurement (str, optional): The measurement name in InfluxDB. Defaults to "token_price".

    Returns:
        list: A list of dictionaries containing the retrieved data points.
              Each dictionary represents a data point with keys for time and fields
              like open, high, low, close, and volume.
        None: If an error occurs or no data is found.
    """
    if not all([URL, TOKEN, ORG, BUCKET]):
        logger.error("InfluxDB environment variables are not fully configured.")
        return None

    try:
        with InfluxDBClient(url=URL, token=TOKEN, org=ORG) as client:
            query_api = client.query_api()
            
            # Construct the Flux query
            query = f'from(bucket:"{BUCKET}") |> range('
            
            # Add time range parameters if provided
            if start_time:
                if isinstance(start_time, datetime):
                    start_time = start_time.isoformat() + "Z"
                query += f'start: {start_time}'
            
            if stop_time:
                if isinstance(stop_time, datetime):
                    stop_time = stop_time.isoformat() + "Z"
                query += f', stop: {stop_time}'
            
            query += f') |> filter(fn:(r) => r._measurement == "{measurement}")'
            query += f' |> filter(fn:(r) => r.symbol == "{token_symbol.upper()}")'
            
            logger.info(f"Executing query for {token_symbol} data...")
            result = query_api.query(query=query, org=ORG)
            
            # Process the results
            data_points = []
            if not result:
                logger.info(f"No data found for {token_symbol}.")
                return []
            
            # Group the records by time to reconstruct complete data points
            time_grouped_data = {}
            
            for table in result:
                for record in table.records:
                    # Get the time and convert to ISO format
                    time_str = record.get_time().isoformat() + "Z"
                    field = record.get_field()
                    value = record.get_value()
                    
                    # Initialize the data point if it doesn't exist
                    if time_str not in time_grouped_data:
                        time_grouped_data[time_str] = {"time": time_str}
                    
                    # Add the field value
                    time_grouped_data[time_str][field] = value
            
            # Convert the dictionary to a list
            data_points = list(time_grouped_data.values())
            
            logger.info(f"Retrieved {len(data_points)} data points for '{token_symbol}'.")
            return data_points
            
    except Exception as e:
        logger.error(f"An error occurred while querying InfluxDB: {e}")
        return None


def get_timestamp_range(measurement_name: str, token_symbol: str):
    """
    Retrieves the oldest and newest timestamps for a specific measurement 
    and optionally filtered by token symbol.

    Args:
        measurement_name (str): The name of the measurement to query
        token_symbol (str, optional): The token symbol to filter by

    Returns:
        tuple: (oldest_timestamp, newest_timestamp) as datetime objects,
               or (None, None) if no data or error occurs
    """
    if not all([URL, TOKEN, ORG, BUCKET]):
        logger.error("InfluxDB environment variables are not fully configured.")
        return None, None

    try:
        with InfluxDBClient(url=URL, token=TOKEN, org=ORG) as client:
            query_api = client.query_api()
            
            # Base query structure
            base_query = f'''
            from(bucket: "{BUCKET}")
              |> range(start: 0)
              |> filter(fn: (r) => r._measurement == "{measurement_name}")
            '''
            
            # Add token symbol filter if provided
            if token_symbol:
                base_query += f'  |> filter(fn: (r) => r.token_symbol == "{token_symbol.upper()}")'
            
            # Query for oldest timestamp
            oldest_query = base_query + '''
              |> first()
              |> keep(columns: ["_time"])
            '''
            
            # Query for newest timestamp
            newest_query = base_query + '''
              |> last() 
              |> keep(columns: ["_time"])
            '''
            
            # Execute queries
            logger.info(f"Querying timestamp range for measurement '{measurement_name}'...")
            oldest_result = query_api.query(query=oldest_query, org=ORG)
            newest_result = query_api.query(query=newest_query, org=ORG)
            
            # Parse results
            oldest_timestamp = None
            if oldest_result and len(oldest_result) > 0 and len(oldest_result[0].records) > 0:
                oldest_timestamp = oldest_result[0].records[0].get_time()
            
            newest_timestamp = None
            if newest_result and len(newest_result) > 0 and len(newest_result[0].records) > 0:
                newest_timestamp = newest_result[0].records[0].get_time()
            
            logger.info(f"Timestamp range for '{measurement_name}': {oldest_timestamp} to {newest_timestamp}")
            return oldest_timestamp, newest_timestamp
            
    except Exception as e:
        logger.error(f"Error querying timestamp range from InfluxDB: {e}")
        return None, None


def format_timestamp(timestamp):
    """
    Format a datetime object to RFC3339Nano format with UTC timezone.
    
    Args:
        dt (datetime): The datetime object to format
        
    Returns:
        str: The formatted datetime string in RFC3339Nano format
    """
    if not timestamp:
        return None
    
    # Convert to UTC if it has a timezone, otherwise assume it's UTC
    if timestamp.tzinfo is not None:
        timestamp = timestamp.astimezone(timezone.utc)
    else:
        # If no timezone info, assume it's UTC
        timestamp = timestamp.replace(tzinfo=timezone.utc)

    # Format with nanosecond precision
    # Python only supports microseconds (6 decimal places)
    # but we can pad with zeros for nanosecond format
    formatted = timestamp.strftime('%Y-%m-%dT%H:%M:%S.%f')
    # Remove the trailing zeros from microseconds and add zeros to make it nanoseconds
    formatted = formatted[:-3] + '000Z'
    
    return formatted


def delete_price_data(token_name: str, token_symbol: str):
    """
    Deletes time-series price data from InfluxDB for a specific token.

    Args:
        token_name (str): The name of the token used as measurement name.
        token_symbol (str): The symbol of the token used in tags.
        start_time (str, datetime, optional): The start time for the deletion range.
                                             If None, will start from the earliest available point.
        stop_time (str, datetime, optional): The end time for the deletion range.
                                           If None, will delete up to the latest available point.

    Returns:
        bool: True if the delete operation was successful, False otherwise.
    """
    if not all([URL, TOKEN, ORG, BUCKET]):
        logger.error("InfluxDB environment variables are not fully configured.")
        return False

    try:
        with InfluxDBClient(url=URL, token=TOKEN, org=ORG) as client:
            oldest_timestamp, newest_timestamp = get_timestamp_range(measurement_name=token_name.upper(), token_symbol=token_symbol.upper())
            oldest_timestamp = format_timestamp(oldest_timestamp)
            newest_timestamp = format_timestamp(newest_timestamp)
            delete_api = client.delete_api()
            
            # Construct predicate for filtering data to delete
            predicate = f'_measurement="{token_name.upper()}" AND token_symbol="{token_symbol.upper()}"'
            
            logger.info(f"Deleting data for {token_name} ({token_symbol})")
            
            # Execute the delete operation
            delete_api.delete(start=str(oldest_timestamp), stop=str(newest_timestamp), predicate=predicate, bucket=BUCKET, org=ORG)

            logger.info(f"Successfully deleted {token_name} ({token_symbol}) data from InfluxDB.")
            return True
            
    except Exception as e:
        logger.error(f"An error occurred while deleting from InfluxDB: {e}")
        return False


# --- Example Usage ---
# This block will only run when you execute this script directly (e.g., `python your_file.py`)
if __name__ == '__main__':
    # logger.info("Running InfluxDB examples...")

    # 1. Create some mock data, similar to what an API might return
    # mock_btc_data = [
    #     # Using ISO 8601 format strings for time, which is very common
    #     {'time': '2024-06-26T10:00:00Z', 'open': 70000.5, 'high': 70100.0, 'low': 69900.2, 'close': 70050.8, 'volume': 100.2},
    #     {'time': '2024-06-26T10:01:00Z', 'open': 70050.8, 'high': 70200.1, 'low': 70050.8, 'close': 70150.3, 'volume': 120.5},
    #     {'time': '2024-06-26T10:02:00Z', 'open': 70150.3, 'high': 70180.7, 'low': 70080.4, 'close': 70100.9, 'volume': 95.8},
    # ]

    # mock_eth_data = [
    #     # Using datetime objects for time also works perfectly
    #     {'time': datetime.now(), 'open': 3500.1, 'high': 3510.2, 'low': 3499.8, 'close': 3505.5, 'volume': 800.7},
    # ]
    # # 2. Call the function to save the data
    # # Ensure your .env file is correctly set up before running this
    # if TOKEN:
    #     logger.info("--- Saving BTC Data ---")
    #     save_price_data(token_name="Bitcoin", token_symbol="BTC", price_data=mock_btc_data)
    #     save_price_data(token_name="Ethereum", token_symbol="ETH", price_data=mock_eth_data)
    # else:
    #     logger.warning("Skipping examples: INFLUXDB_TOKEN not found in .env file.")
    #     logger.info("Please ensure your .env file is configured with your InfluxDB credentials.")

    # Uncomment to test data retrieval
    # logger.info("--- Retrieving BTC Data Example ---")
    # # Get BTC data from the last week
    # end_time = datetime.now()
    # start_time = end_time - timedelta(days=7)

    # btc_data = get_price_data("Bitcoin", start_time=start_time, stop_time=end_time)
    # if btc_data:
    #     logger.info(f"First data point: {btc_data[0] if btc_data else 'No data found'}")
    #     logger.info(f"Total data points: {len(btc_data)}")

    # Add to the end of your __main__ block
    # if TOKEN:
    #     logger.info("--- Testing Timestamp Range Query ---")
    #     # Get timestamp range for Bitcoin measurement
    #     oldest, newest = get_timestamp_range("BITCOIN", "BTC")
    #     print(type(oldest))
    #     print(oldest)
    #     if oldest and newest:
    #         logger.info(f"Bitcoin data range: {oldest.strftime('%Y-%m-%d %H:%M:%S')} to {newest.strftime('%Y-%m-%d %H:%M:%S')}")
    #         logger.info(f"Total time span: {(newest - oldest).days} days, {(newest - oldest).seconds // 3600} hours")
    #     else:
    #         logger.info("No timestamp range found for Bitcoin")

    delete_price_data("bitcoin", "btc")   
