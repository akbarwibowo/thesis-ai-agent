import logging

# Configure logger
logging.basicConfig(
    level=logging.INFO,  # Set to DEBUG to see debug messages too
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # This outputs to console/terminal
    ]
)
logger = logging.getLogger(__name__)


def calculate_sma(prices: list[float], period: int = 21) -> list[float]:
    """
    Calculate Simple Moving Average (SMA) for a given list of prices and period.
    Args:
        prices (list[float]): List of prices.
        period (int): The period over which to calculate the SMA.
    Returns:
        list[float]: List of SMA values. The length will be len(prices) - period + 1.
    """
    if not prices or period <= 0 or period > len(prices):
        return []

    sma_values = []
    for i in range(len(prices) - period + 1):
        sma = sum(prices[i:i + period]) / period
        sma_values.append(sma)

    return sma_values


def calculate_ema(prices: list[float], period: int = 13) -> list[float]:
    """
    Calculate Exponential Moving Average (EMA) for a given list of prices and period.
    
    Args:
        prices (list[float]): List of prices.
        period (int): The period over which to calculate the EMA.
    Returns:
        list[float]: List of EMA values. The length will be len(prices) - period + 1.
    """
    if not prices or period <= 0 or period > len(prices):
        return []

    smoothing_factor = 2 / (period + 1)
    
    # Calculate initial SMA
    initial_sma = sum(prices[:period]) / period
    ema_values = [initial_sma]
    
    # Calculate EMA for remaining values
    for i in range(period, len(prices)):
        current_price = prices[i]
        previous_ema = ema_values[-1]
        ema = (current_price * smoothing_factor) + (previous_ema * (1 - smoothing_factor))
        ema_values.append(ema)

    return ema_values


def calculate_rsi(prices: list[float], period: int = 14) -> list[float]:
    """
    Calculates the Relative Strength Index (RSI) using Wilder's Smoothing Method.

    Args:
        prices (list[float]): A list of price points (e.g., closing prices).
        period (int): The lookback period for the RSI. The standard is 14.

    Returns:
        list[float]: A list of the calculated RSI values. The list will be
                     shorter than the input prices list by 'period'.
    """
    if not prices or period <= 0 or len(prices) <= period:
        return []

    deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]

    gains = [delta if delta > 0 else 0 for delta in deltas]
    losses = [-delta if delta < 0 else 0 for delta in deltas]

    initial_avg_gain = sum(gains[:period]) / period
    initial_avg_loss = sum(losses[:period]) / period
    
    smoothed_gains = [initial_avg_gain]
    smoothed_losses = [initial_avg_loss]

    for i in range(period, len(gains)):
        current_gain = (smoothed_gains[-1] * (period - 1) + gains[i]) / period
        current_loss = (smoothed_losses[-1] * (period - 1) + losses[i]) / period
        
        smoothed_gains.append(current_gain)
        smoothed_losses.append(current_loss)

    rsi_values = []
    for i in range(len(smoothed_gains)):
        avg_gain = smoothed_gains[i]
        avg_loss = smoothed_losses[i]

        if avg_loss == 0:
            # If there are no losses, RSI is 100
            rsi = 100.0
        else:
            # Calculate Relative Strength (RS)
            rs = avg_gain / avg_loss
            # Calculate RSI
            rsi = 100 - (100 / (1 + rs))
        
        rsi_values.append(rsi)

    return rsi_values
