from influxdb_client.client.influxdb_client import InfluxDBClient
from influxdb_client.client.write.point import Point
from influxdb_client.client.write_api import SYNCHRONOUS
from dotenv import load_dotenv, find_dotenv
from os import getenv
from datetime import datetime, timedelta

load_dotenv(find_dotenv())

BUCKET = str(getenv("INFLUXDB_BUCKET"))
TOKEN = str(getenv("INFLUXDB_TOKEN"))
ORG = str(getenv("INFLUXDB_ORG"))
URL = str(getenv("INFLUXDB_URL"))

def save_price_data(token_symbol, price_data):
    """
    Saves a list of time-series price data points to InfluxDB.

    Args:
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
        print("Error: InfluxDB environment variables are not fully configured.")
        return False

    # The 'with' statement ensures the client is properly closed after use
    with InfluxDBClient(url=URL, token=TOKEN, org=ORG) as client:
        # A WriteAPI is used to write data. SYNCHRONOUS mode writes data in batches
        # and waits for the server to acknowledge the write.
        write_api = client.write_api(write_options=SYNCHRONOUS)

        # We will convert our list of dictionaries into a list of InfluxDB 'Point' objects
        points_to_write = []

        print(f"Preparing {len(price_data)} data points for '{token_symbol}'...")

        for entry in price_data:
            # Create a Point object for each entry.
            # A "measurement" is like a table name in a SQL database.
            point = Point("token_price") \
                .tag("symbol", token_symbol.upper()) \
                .time(entry["time"]) # The time of the data point

            # Add all other dictionary keys (except 'time') as "fields"
            # Fields are the actual data values you want to store and query.
            for key, value in entry.items():
                if key != "time":
                    # Ensure numeric values are cast correctly (float is safest)
                    try:
                        point = point.field(key, float(value))
                    except (ValueError, TypeError):
                        # Handle cases where a value might not be numeric
                        print(f"Warning: Skipping non-numeric value for key '{key}' in {token_symbol} data.")

            points_to_write.append(point)

        try:
            print(f"Writing {len(points_to_write)} points to bucket '{BUCKET}'...")
            # Write the entire list of points to InfluxDB in a single batch
            write_api.write(bucket=BUCKET, org=ORG, record=points_to_write)
            print("Successfully wrote data to InfluxDB.")
            return True
        except Exception as e:
            print(f"An error occurred while writing to InfluxDB: {e}")
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
        print("Error: InfluxDB environment variables are not fully configured.")
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
            
            print(f"Executing query for {token_symbol} data...")
            result = query_api.query(query=query, org=ORG)
            
            # Process the results
            data_points = []
            if not result:
                print(f"No data found for {token_symbol}.")
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
            
            print(f"Retrieved {len(data_points)} data points for '{token_symbol}'.")
            return data_points
            
    except Exception as e:
        print(f"An error occurred while querying InfluxDB: {e}")
        return None


# --- Example Usage ---
# This block will only run when you execute this script directly (e.g., `python your_file.py`)
# It demonstrates how to use the function.
if __name__ == '__main__':
    print("Running InfluxDB save example...")

    # 1. Create some mock data, similar to what an API might return
    mock_btc_data = [
        # Using ISO 8601 format strings for time, which is very common
        {'time': '2025-06-26T10:00:00Z', 'open': 70000.5, 'high': 70100.0, 'low': 69900.2, 'close': 70050.8, 'volume': 100.2},
        {'time': '2025-06-26T10:01:00Z', 'open': 70050.8, 'high': 70200.1, 'low': 70050.8, 'close': 70150.3, 'volume': 120.5},
        {'time': '2025-06-26T10:02:00Z', 'open': 70150.3, 'high': 70180.7, 'low': 70080.4, 'close': 70100.9, 'volume': 95.8},
    ]

    mock_eth_data = [
        # Using datetime objects for time also works perfectly
        {'time': datetime.now(), 'open': 3500.1, 'high': 3510.2, 'low': 3499.8, 'close': 3505.5, 'volume': 800.7},
    ]


    # 2. Call the function to save the data
    # Ensure your .env file is correctly set up before running this
    if TOKEN:
        print("\n--- Saving BTC Data ---")
        save_price_data(token_symbol="BTC", price_data=mock_btc_data)

        print("\n--- Saving ETH Data ---")
        save_price_data(token_symbol="ETH", price_data=mock_eth_data)
    else:
        print("\nSkipping example: INFLUXDB_TOKEN not found in .env file.")
        print("Please ensure your .env file is configured with your InfluxDB credentials.")

    print("\n--- Retrieving BTC Data Example ---")
    # Get BTC data from the last week
    end_time = datetime.now()
    start_time = end_time - timedelta(days=7)
    
    btc_data = get_price_data("BTC", start_time=start_time, stop_time=end_time)
    if btc_data:
        print(f"First data point: {btc_data[0] if btc_data else 'No data found'}")
        print(f"Total data points: {len(btc_data)}")
