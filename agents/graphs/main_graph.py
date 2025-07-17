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

from sub_graphs.na_sub_graph import na_graph
from sub_graphs.ta_sub_graph import ta_graph
from sub_graphs.fa_sub_graph import fa_graph
from agents.schemas.main_agent_schema import MainState, NAIdentifierOutput
from agents.schemas.na_agent_schema import NAOutputState
from agents.llm_model import llm_model
from langgraph.graph import START, END, StateGraph
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import START, END, StateGraph
from langgraph.types import Send
from langchain_core.messages import SystemMessage, HumanMessage
from agents.tools.databases.mongodb import retrieve_documents
from agents.tools.narrative_data_getter.narrative_module import collection_name
from agents.tools.token_data_getter.token_selection import categories_selector
from agents.tools.token_data_getter.tokens_identity import get_token_identity



def start_graph(state: MainState):
    """Start node for the main graph"""

    start_command = state["start_command"]
    if start_command != "START":
        logger.error(f"Invalid start command: {start_command}. Expected 'START'.")
        raise ValueError("Invalid start command. Expected 'START'.")

    narrative_data = retrieve_documents(collection_name=collection_name)

    if not isinstance(narrative_data, list) or not narrative_data:
        # empty database
        max_twitter_scrape = 500
        max_cointelegraph_scrape = 500
    elif len(narrative_data) < 500:
        max_twitter_scrape = 250
        max_cointelegraph_scrape = 250
    elif len(narrative_data) < 1000:
        max_twitter_scrape = 1000 - len(narrative_data)
        max_cointelegraph_scrape = 1000 - len(narrative_data)
    else:
        max_twitter_scrape = 0
        max_cointelegraph_scrape = 0
    
    return {
        "cointelegraph_max_articles": max_cointelegraph_scrape,
        "twitter_scrape_max_tweets": max_twitter_scrape,
    }


def narrative_identifier(state: NAOutputState):
    """Node to identify the narrative based on the report"""
    narrative_report = state["final_na_report"]

    structured_llm = llm_model.with_structured_output(NAIdentifierOutput)
    system_prompt = """
    You are a highly specialized data extraction AI. Your sole function is to read a given block of text and identify the primary cryptocurrency market narrative categories mentioned within it. You are precise and your output is always in a structured format. Do not add any explanation or conversational text.
    """
    user_prompt = f"""
    Your task is to read the following analysis report and identify the main cryptocurrency narrative categories discussed. The narratives are usually sectors or themes like "Real World Assets (RWA)", "DeFi", "AI & DePIN", "GameFi", "Layer 2 Scaling", "Stablecoins", etc.
    Your output MUST be a valid list of strings.
    If you identify one or more narratives, list their names in the list.
    If the report does not mention any clear narrative, return an empty list [].
    Example 1:
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

    result = structured_llm.invoke([SystemMessage(content=system_prompt)] + [HumanMessage(content=user_prompt)])
    narrative_list = result.narratives if hasattr(result, 'narratives') else [] # type: ignore
    if not narrative_list and not isinstance(narrative_list, list):
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
        result = llm_model.invoke([SystemMessage(content=system_prompt)] + [HumanMessage(content=user_prompt)])
        final_report = "# NO NARRATIVE IDENTIFIED\n" + str(result.content if hasattr(result, 'content') else "No narrative identified and no explanation provided.")
        return {"final_analysis_report": final_report}
    
    categories = categories_selector(narrative_list)
    if not categories:
        return {"final_analysis_report": "No Categories Found."}

    token_ids = []
    for category in categories:
        token_ids.extend(category.get("tokens", []))
        category["token_names"] = [get_token_identity(token_id)["name"] for token_id in category["tokens"] if get_token_identity(token_id)]

    return {
        "identified_narratives": narrative_list,
        "token_ids": token_ids,
        "categories_with_tokens": categories,
    }


def should_continue(state: MainState) -> Sequence[str]:
    """Node to check if there is narrative identified."""
    final_analysis_report = state["final_analysis_report"]

    if "NO NARRATIVE IDENTIFIED" in final_analysis_report or "No Categories Found" in final_analysis_report:
        return END

    return ["fa_node", "ta_node"]


def final_report(state: MainState):
    """Node to generate the final report based on the combined analysis reports"""

    narrative_report = state["final_na_report"]
    identified_narratives = state["identified_narratives"]
    fa_reports = state["final_fa_report"]
    ta_reports = state["final_ta_report"]
    categories_with_tokens = state["categories_with_tokens"]

    final_analysis_report = f"""
    {narrative_report}
    ## Identified Narratives
    {identified_narratives}

    # Tokens of Identified Narratives\n
    """

    for category in categories_with_tokens:
        final_analysis_report += f"## {str(category['name']).capitalize()}\n"
        for token in category["token_names"]:
            final_analysis_report += f"- {token}\n"
    
    final_analysis_report += "\n# Fundamental Analysis Reports\n"
    for fa_report in fa_reports:
        final_analysis_report += f"## {str(fa_report.token_name).capitalize()}\n"
        final_analysis_report += f"### Fundamental Analysis\n{fa_report.fundamental_analysis}\n"
        final_analysis_report += f"### Proof\n"
        for proof in fa_report.proof:
            final_analysis_report += f"- {proof}\n"

    final_analysis_report += "\n# Technical Analysis Reports\n"
    for ta_report in ta_reports:
        final_analysis_report += f"## {str(ta_report.token_name).capitalize()}\n"
        final_analysis_report += f"### Trend Analysis\n{ta_report.trend_analysis}\n"
        final_analysis_report += f"### Momentum Analysis\n{ta_report.momentum_analysis}\n"
        final_analysis_report += f"### Volume Analysis\n{ta_report.volume_analysis}\n"
        final_analysis_report += f"### Outlook\n{ta_report.synthesis_and_outlook}\n"

    return {"final_analysis_report": final_analysis_report}


def main_graph():
    """AI Analyst Main Graph"""
    na_node = na_graph()
    fa_node = fa_graph()
    ta_node = ta_graph()
    graph = StateGraph(MainState)
    graph.add_node("start", start_graph)
    graph.add_node("na_node", na_node)
    graph.add_node("narrative_identifier", narrative_identifier)
    graph.add_node("fa_node", fa_node)
    graph.add_node("ta_node", ta_node)
    graph.add_node("final_report", final_report)

    graph.add_edge(START, "start")
    graph.add_edge("start", "na_node")
    graph.add_edge("na_node", "narrative_identifier")
    graph.add_conditional_edges("narrative_identifier", should_continue, ["fa_node", "ta_node", END])
    graph.add_edge(["ta_node", "fa_node"], "final_report")
    graph.add_edge("final_report", END)

    ai_agent = graph.compile()

    return ai_agent


if __name__ == "__main__":
    ai_agent = main_graph()
    # ai_agent.invoke({"start_command": "START"})
    graph_png = ai_agent.get_graph().draw_mermaid_png()
    with open("graph.png", "wb") as f:
        f.write(graph_png)
