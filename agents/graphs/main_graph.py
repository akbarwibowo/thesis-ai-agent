import sys
import logging
import os
from typing import Sequence

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

from agents.graphs.sub_graphs.na_sub_graph import na_graph
from agents.graphs.sub_graphs.ta_sub_graph import ta_graph
from agents.graphs.sub_graphs.fa_sub_graph import fa_graph
from agents.schemas.main_agent_schema import MainState, NAIdentifierOutput
from agents.schemas.na_agent_schema import NAOutputState
from agents.llm_model import llm_model
from langgraph.graph import START, END, StateGraph
from langchain_core.messages import SystemMessage, HumanMessage
from agents.tools.databases.mongodb import retrieve_documents
from agents.tools.narrative_data_getter.narrative_module import collection_name
from agents.tools.token_data_getter.token_selection import categories_selector, _get_categories_with_tokens
from agents.tools.token_data_getter.tokens_identity import get_token_identity



def start_graph(state: MainState):
    """Start node for the main graph"""
    logger.info("Starting main graph execution")

    start_command = state["start_command"]
    logger.info(f"Received start command: {start_command}")
    
    if start_command != "START":
        logger.error(f"Invalid start command: {start_command}. Expected 'START'.")
        raise ValueError("Invalid start command. Expected 'START'.")

    logger.info("Retrieving existing narrative data from database")
    narrative_data = retrieve_documents(collection_name=collection_name)
    
    existing_count = len(narrative_data) if isinstance(narrative_data, list) else 0
    logger.info(f"Found {existing_count} existing narrative documents in database")

    if not isinstance(narrative_data, list) or not narrative_data:
        # empty database
        max_twitter_scrape = 500
        max_cointelegraph_scrape = 500
        logger.info("Database is empty - setting maximum scraping limits")
    elif len(narrative_data) < 500:
        max_twitter_scrape = 250
        max_cointelegraph_scrape = 250
        logger.info(f"Database has {len(narrative_data)} documents - setting moderate scraping limits")
    elif len(narrative_data) < 1000:
        max_twitter_scrape = 1000 - len(narrative_data)
        max_cointelegraph_scrape = 1000 - len(narrative_data)
        logger.info(f"Database has {len(narrative_data)} documents - setting reduced scraping limits")
    else:
        max_twitter_scrape = 0
        max_cointelegraph_scrape = 0
        logger.info(f"Database has {len(narrative_data)} documents - skipping scraping")
    
    logger.info(f"Scraping configuration - Twitter: {max_twitter_scrape}, CoinTelegraph: {max_cointelegraph_scrape}")
    
    logger.info(f"start_graph execution completed.")
    
    return {
        "cointelegraph_max_articles": max_cointelegraph_scrape,
        "twitter_scrape_max_tweets": max_twitter_scrape,
    }


def narrative_identifier(state: NAOutputState):
    """Node to identify the narrative based on the report"""
    logger.info("Starting narrative_identifier execution")
    
    narrative_report = state["final_na_report"]
    logger.info(f"Processing narrative report of length: {len(str(narrative_report))} characters")

    available_categories = _get_categories_with_tokens()
    categories_name = [cat["name"] for cat in available_categories]

    structured_llm = llm_model.with_structured_output(NAIdentifierOutput)
    system_prompt = """
    You are a highly specialized data extraction AI. Your sole function is to read a given block of text and identify the primary cryptocurrency market narrative categories mentioned within it. You are precise and your output is always in a structured format. Do not add any explanation or conversational text.
    """
    # USER PROMPT 1
    # user_prompt = f"""
    # Your task is to read the following analysis report and identify the main cryptocurrency narrative categories discussed. The narratives are usually sectors or themes like "Real World Assets (RWA)", "DeFi", "AI & DePIN", "GameFi", "Layer 2 Scaling", "Stablecoins", etc.
    # Your output MUST be a valid list of strings.
    # If you identify one or more narratives, list their names in the list.
    # If the report does not mention any clear narrative, return an empty list [].
    # Example 1:
    # Input Report: "...the analysis shows a strong trend in AI and Decentralized Compute..."
    # Your Output: ["AI", "Decentralized Compute"]
    # Example 2:
    # Input Report: "...the market is showing general sideways movement without a clear focus..."
    # Your Output: []
    # Analysis Report to Process:
    # <narrative_analysis_report>
    # {narrative_report}
    # </narrative_analysis_report>
    # """

    # USER PROMPT 2
    user_prompt = f"""
    Your task is to read the following analysis report and identify the main cryptocurrency narrative categories discussed.
    The available categories are: {', '.join(categories_name)}.
    Your output MUST be a valid list of strings.
    If you identify one or more narratives, list their names in the list.
    If the report does not mention any clear narrative, return an empty list [].
    # Example 1:
    Input Report: "...the analysis shows a strong trend in AI and Decentralized Compute..."
    Your Output: ["AI", "Decentralized Compute"]
    Example 2:
    Input Report: "...the market is showing general sideways movement without a clear focus..."
    Your Output: []
    Analysis Report to Process:
    <narrative_analysis_report>
    {narrative_report}
    </narrative_analysis_report>
    """

    logger.info("Invoking LLM for narrative identification")
    result = structured_llm.invoke([SystemMessage(content=system_prompt)] + [HumanMessage(content=user_prompt)])
    narrative_list = result.narratives if hasattr(result, 'narratives') else [] # type: ignore
    
    logger.info(f"Identified narratives: {narrative_list}")
    
    if not narrative_list and not isinstance(narrative_list, list):
        logger.info("No narratives identified - generating explanatory report")
        system_prompt = """
        You are an expert financial markets communicator. Your primary skill is taking complex, data-heavy analysis and translating it into a clear, concise, and easy-to-understand summary for a general audience. You excel at explaining why a conclusion was reached, focusing on the underlying market dynamics.
        """
        user_prompt = f"""
        The following is a technical analysis report that concluded no single, dominant narrative is currently emerging in the cryptocurrency market.
        Your task is to rewrite this report into a simple, clear explanation for the end-user. Your explanation should:
        State clearly that no single, strong narrative was identified.
        Briefly explain the likely reasons based on the report (e.g., "the market is showing conflicting signals," "different sectors are receiving equal attention," or "the market is in a period of consolidation").
        Be concise and easy to understand.
        Do not include the original report in your output. Just provide the final, rewritten explanation.
        Original Analysis Report to Rewrite:

        <narrative_analysis_report>
        {narrative_report}
        </narrative_analysis_report>
        """
        logger.info("Invoking LLM for no-narrative explanation")
        result = llm_model.invoke([SystemMessage(content=system_prompt)] + [HumanMessage(content=user_prompt)])
        final_report = "# NO NARRATIVE IDENTIFIED\n" + str(result.content if hasattr(result, 'content') else "No narrative identified and no explanation provided.")

        logger.info(f"narrative_identifier completed (no narratives)")
        return {"final_analysis_report": final_report}
    
    logger.info("Selecting token categories based on identified narratives")
    categories = categories_selector(narrative_list, available_categories=available_categories)
    
    if not categories:
        logger.warning("No categories found for identified narratives")
        logger.info(f"narrative_identifier completed (no categories)")
        return {"final_analysis_report": "No Categories Found."}

    logger.info(f"Found {len(categories)} categories for analysis")
    
    token_ids = []
    for i, category in enumerate(categories):
        token_count = len(category.get("tokens", []))
        logger.info(f"Category {i+1}: {category.get('name', 'Unknown')} - {token_count} tokens")
        token_ids.extend(category.get("tokens", []))
        
        # Resolve token names
        resolved_names = []
        for token_id in category["tokens"]:
            identity = get_token_identity(token_id)
            if identity:
                resolved_names.append(identity["name"])
            else:
                logger.warning(f"Could not resolve identity for token_id: {token_id}")
        
        category["token_names"] = resolved_names
        logger.info(f"Resolved {len(resolved_names)} token names for category: {category.get('name', 'Unknown')}")

    logger.info(f"Total tokens to analyze: {len(token_ids)}")

    logger.info(f"narrative_identifier execution completed.")

    return {
        "identified_narratives": narrative_list,
        "token_ids": token_ids,
        "categories_with_tokens": categories,
        "final_analysis_report": "continue to final analysis"
    }


def should_continue(state: MainState) -> Sequence[str]:
    """Node to check if there is narrative identified."""
    logger.info("Evaluating whether to continue with detailed analysis")
    
    final_analysis_report = state["final_analysis_report"]
    
    if "NO NARRATIVE IDENTIFIED" in final_analysis_report or "No Categories Found" in final_analysis_report:
        logger.info("No narrative identified - terminating analysis pipeline")
        return END

    logger.info("Narratives identified - proceeding with fundamental and technical analysis")
    return ["fa_node", "ta_node"]


def final_report(state: MainState):
    """Node to generate the final report based on the combined analysis reports"""
    logger.info("Starting final_report generation")

    narrative_report = state["final_na_report"]
    identified_narratives = state["identified_narratives"]
    fa_reports = state["final_fa_report"]
    ta_reports = state["final_ta_report"]
    categories_with_tokens = state["categories_with_tokens"]

    logger.info(f"Compiling final report with {len(identified_narratives)} narratives")
    logger.info(f"Including {len(fa_reports)} fundamental analysis reports")
    logger.info(f"Including {len(ta_reports)} technical analysis reports")
    logger.info(f"Processing {len(categories_with_tokens)} token categories")

    final_analysis_report = f"""{narrative_report}

        ## Identified Narratives
        {identified_narratives}

        # Tokens of Identified Narratives<br>
        """

    for i, category in enumerate(categories_with_tokens):
        category_name = str(category['name']).capitalize()
        token_count = len(category["token_names"])
        logger.info(f"Adding category {i+1}: {category_name} with {token_count} tokens")
        
        final_analysis_report += f"## {category_name}<br>"
        for token in category["token_names"]:
            final_analysis_report += f"- {token}<br>"
    
    logger.info("Adding fundamental analysis reports to final report")
    final_analysis_report += "<br># Fundamental Analysis Reports<br>"
    for i, fa_report in enumerate(fa_reports):
        token_name = str(fa_report.token_name).capitalize()
        proof_count = len(fa_report.proof)
        logger.info(f"Adding FA report {i+1}: {token_name} with {proof_count} proof points")
        
        final_analysis_report += f"## {token_name}<br>"
        final_analysis_report += f"### Fundamental Analysis<br>{fa_report.fundamental_analysis}<br>"
        final_analysis_report += f"### Proof<br>"
        for proof in fa_report.proof:
            final_analysis_report += f"- {proof}<br>"

    logger.info("Adding technical analysis reports to final report")
    final_analysis_report += "<br># Technical Analysis Reports<br>"
    for i, ta_report in enumerate(ta_reports):
        token_name = str(ta_report.token_name).capitalize()
        logger.info(f"Adding TA report {i+1}: {token_name}")
        
        final_analysis_report += f"## {token_name}<br>"
        final_analysis_report += f"### Trend Analysis<br>{ta_report.trend_analysis}<br>"
        final_analysis_report += f"### Momentum Analysis<br>{ta_report.momentum_analysis}<br>"
        final_analysis_report += f"### Volume Analysis<br>{ta_report.volume_analysis}<br>"
        final_analysis_report += f"### Outlook<br>{ta_report.synthesis_and_outlook}<br>"
    final_analysis_report = final_analysis_report.strip().replace('\n', '<br>')
    report_length = len(final_analysis_report)
    logger.info(f"Final report generated successfully.")
    logger.info(f"Final report length: {report_length} characters")
    
    return {"final_analysis_report": final_analysis_report}


def main_graph():
    """AI Analyst Main Graph"""
    logger.info("Setting up Main AI Analyst Graph")
    
    logger.info("Initializing sub-graphs")
    na_node = na_graph()
    fa_node = fa_graph()
    ta_node = ta_graph()
    logger.info("Sub-graphs initialized successfully")
    
    logger.info("Configuring main graph structure")
    graph = StateGraph(MainState)
    graph.add_node("start", start_graph)
    graph.add_node("na_node", na_node)
    graph.add_node("narrative_identifier", narrative_identifier)
    graph.add_node("fa_node", fa_node)
    graph.add_node("ta_node", ta_node)
    graph.add_node("final_report", final_report)

    logger.info("Adding graph edges")
    graph.add_edge(START, "start")
    graph.add_edge("start", "na_node")
    graph.add_edge("na_node", "narrative_identifier")
    graph.add_conditional_edges("narrative_identifier", should_continue, ["fa_node", "ta_node", END])
    graph.add_edge(["ta_node", "fa_node"], "final_report")
    graph.add_edge("final_report", END)

    logger.info("Compiling main graph")
    ai_agent = graph.compile()

    logger.info(f"Main graph setup completed.")

    return ai_agent
