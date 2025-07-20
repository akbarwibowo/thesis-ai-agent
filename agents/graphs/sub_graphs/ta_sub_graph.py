import sys
import logging
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.join(current_dir, '..', '..')
sys.path.insert(0, project_root)

# Create logger for this module
logger = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.INFO,  # Set to DEBUG to see debug messages too
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # This outputs to console/terminal
    ]
)


from langgraph.graph import START, END, StateGraph
from langchain_core.messages import SystemMessage, HumanMessage
from agents.schemas.ta_agent_schema import TAInputState, TAOutputState, TAOverallState, TAOutput
from agents.tools.token_data_getter.technical_data_module import get_price_data_of_tokens, save_price_data_to_db
from agents.tools.token_data_getter.tokens_identity import get_token_identity
from agents.tools.technical_calculator.indicator_module import calculate_ema, calculate_sma, calculate_rsi
from agents.llm_model import llm_model



def get_and_save_node(state: TAInputState):
    """Get price data and save it to the database."""
    logger.info("Starting get_and_save_node execution")
    
    token_ids = state["token_ids"]
    logger.info(f"Processing price data for {len(token_ids)} tokens: {token_ids}")
    
    logger.info("Calling get_price_data_of_tokens to fetch price data")
    price_datas = get_price_data_of_tokens(token_ids=token_ids)
    logger.info(f"Successfully retrieved price data for {len(price_datas)} tokens")

    # Log data quality information
    for i, data in enumerate(price_datas):
        token_id = data.get('token_id', 'Unknown')
        price_points = len(data.get('price_data', []))
        logger.info(f"Token {i+1} ({token_id}) - Price data points: {price_points}")

    logger.info("Saving price data to database")
    save_price_data_to_db(price_data=price_datas)
    logger.info("Price data saved to database successfully")

    logger.info(f"get_and_save_node execution completed successfully.")
    return {"price_data": price_datas}


def technical_analysis_node(state: TAOverallState):
    """AI node for technical analysis."""
    logger.info("Starting technical_analysis_node execution")
    
    structured_llm = llm_model.with_structured_output(TAOutput)
    system_prompt = """
    You are a quantitative technical analyst AI. Your sole function is to interpret raw time-series data for a given cryptocurrency to identify trends, momentum, and potential signals.
    Your Rules:
    - Analyze ONLY the provided data. Do not use any external knowledge or information about events that are not present in the data.
    - Focus on the relationships between the data points. Analyze how the price interacts with the moving averages (SMA, EMA), the state of the RSI, and how volume confirms or contradicts price movements.
    - Do not provide financial advice or make future price predictions. Your analysis must be a neutral, objective interpretation of the data's current state.
    - Your output must be a concise, well-structured analysis, suitable for a professional market report.
    """

    price_datas = state["price_data"]
    logger.info(f"Processing technical analysis for {len(price_datas)} tokens")
    
    ta_analysis_list = []
    for i, data in enumerate(price_datas):
        token_id = data["token_id"]
        logger.info(f"Analyzing token {i+1}/{len(price_datas)} - Token ID: {token_id}")
        
        token_identity = get_token_identity(token_id=token_id)
        token_name = token_identity.get("name", "Unknown Token") if token_identity else "Unknown Token"
        logger.info(f"Token identity resolved: {token_name}")
        
        prices = [float(price["price"]) for price in data["price_data"]]
        logger.info(f"Processing {len(prices)} price data points for {token_name}")
        
        # Log price range for context
        if prices:
            min_price = min(prices)
            max_price = max(prices)
            latest_price = prices[-1]
            logger.info(f"Price range - Min: ${min_price:.2f}, Max: ${max_price:.2f}, Latest: ${latest_price:.2f}")

        # Technical indicator parameters
        ema_period = 13
        sma_period = 21
        rsi_period = 14
        
        logger.info(f"Calculating technical indicators - EMA({ema_period}), SMA({sma_period}), RSI({rsi_period})")
        ema_values = calculate_ema(prices=prices, period=ema_period)
        sma_values = calculate_sma(prices=prices, period=sma_period)
        rsi_values = calculate_rsi(prices=prices, period=rsi_period)
        
        logger.info(f"Technical indicators calculated - EMA: {len(ema_values)} values, SMA: {len(sma_values)} values, RSI: {len(rsi_values)} values")

        # Log latest indicator values for context
        if ema_values and ema_values[-1] is not None:
            logger.info(f"Latest EMA({ema_period}): ${ema_values[-1]:.2f}")
        if sma_values and sma_values[-1] is not None:
            logger.info(f"Latest SMA({sma_period}): ${sma_values[-1]:.2f}")
        if rsi_values and rsi_values[-1] is not None:
            logger.info(f"Latest RSI({rsi_period}): {rsi_values[-1]:.2f}")

        # make the indicators value points has same length as prices
        ema_values = [None] * (len(prices) - len(ema_values)) + ema_values
        sma_values = [None] * (len(prices) - len(sma_values)) + sma_values
        rsi_values = [None] * (len(prices) - len(rsi_values)) + rsi_values

        logger.info("Aligning indicator data with price data timeline")
        data["token_name"] = token_name
        for j in range(len(data["price_data"])):
            data["price_data"][j]["ema"] = ema_values[j]
            data["price_data"][j]["sma"] = sma_values[j]
            data["price_data"][j]["rsi"] = rsi_values[j]
        
        user_prompt = f"""
        Based on the following time-series data for {token_name}, provide a comprehensive, evidence-based technical analysis.
        <technical_data>
        {data}
        </technical_data>
        Instructions:
        - For each section, you must describe the specific data behavior that supports your analysis.
        - Trend Analysis: Describe the overall trend by analyzing the relationship between the price, the {ema_period}-period EMA, and the {sma_period}-period SMA. If you note a significant crossover, describe its timing within the data series (e.g., "a golden cross occurred recently in the last portion of the data").
        - Momentum Analysis: Interpret the {rsi_period}-period RSI values. Indicate whether the asset shows signs of being overbought (>70), oversold (<30), or is in a neutral range. Describe the recent RSI trend (e.g., "RSI has been rising for the past few days and is now entering overbought territory").
        - Volume Analysis: Analyze the volume data. Does it confirm the recent price trend, or does it suggest a lack of conviction? Cite specific patterns, such as "The recent price increase was confirmed by a significant volume spike in the last few data points."
        - Synthesis & Outlook: Provide a concluding summary of the current technical outlook based on the combined, evidence-backed signals from the trend, momentum, and volume.
        """

        logger.info(f"Invoking LLM for technical analysis of {token_name}")
        result = structured_llm.invoke([SystemMessage(content=system_prompt)]+[HumanMessage(content=user_prompt)])
        
        logger.info(f"Technical analysis for {token_name} completed successfully")
        if result:
            ta_analysis_list.append(result)
    logger.info(f"All technical analyses completed. Generated {len(ta_analysis_list)} analysis reports")
    logger.info(f"technical_analysis_node execution completed successfully")
    return {"final_ta_report": ta_analysis_list}


def ta_graph():
    """AI Node for technical analysis (TA) graph setup."""
    logger.info("Setting up Technical Analysis (TA) graph")

    graph = StateGraph(TAOverallState, input_schema=TAInputState, output_schema=TAOutputState)
    graph.add_node("get_and_save_node", get_and_save_node)
    graph.add_node("technical_analysis_node", technical_analysis_node)

    graph.add_edge(START, "get_and_save_node")
    graph.add_edge("get_and_save_node", "technical_analysis_node")
    graph.add_edge("technical_analysis_node", END)

    logger.info("Graph nodes and edges configured successfully")
    ta_graph = graph.compile()
    logger.info("TA graph compiled successfully")

    return ta_graph
