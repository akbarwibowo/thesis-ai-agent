import logging
import math

# Configure logger
logging.basicConfig(
    level=logging.INFO,  # Set to DEBUG to see debug messages too
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # This outputs to console/terminal
    ]
)
logger = logging.getLogger(__name__)


def calculate_sma(prices: list[float], period: int) -> list[float]:
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


def calculate_ema(prices: list[float], period: int) -> list[float]:
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
