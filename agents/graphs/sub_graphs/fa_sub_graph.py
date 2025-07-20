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


from agents.tools.token_data_getter.fundamental_data_module import get_fundamental_data_of_tokens, save_fundamental_data_to_db
from agents.tools.token_data_getter.tokens_identity import get_token_identity
from agents.tools.databases.mongodb import retrieve_documents
from agents.schemas.fa_agent_schema import FAInputState, FAOutputState, FAOverallState, FAOutput
from agents.llm_model import get_llm
from langgraph.graph import START, END, StateGraph
from langchain_core.messages import SystemMessage, HumanMessage



def get_and_save_node(state: FAInputState):
    """get fundamental data and save it to the database"""
    logger.info("Starting get_and_save_node execution")

    token_ids = state["token_ids"]
    logger.info(f"Processing fundamental data for {len(token_ids)} tokens: {token_ids}")

    logger.info("Calling get_fundamental_data_of_tokens to fetch data")
    fundamental_datas = get_fundamental_data_of_tokens(token_ids=token_ids)
    logger.info(f"Successfully retrieved fundamental data for {len(fundamental_datas)} tokens")
    
    # Log data quality information
    for i, data in enumerate(fundamental_datas):
        token_id = data.get('token_id', 'Unknown')
        has_whitepaper = bool(data.get('whitepaper_text', ''))
        has_website = bool(data.get('website_text', ''))
        logger.info(f"Token {i+1} ({token_id}) - Whitepaper: {'✓' if has_whitepaper else '✗'}, Website: {'✓' if has_website else '✗'}")
    
    logger.info("Saving fundamental data to database")
    save_fundamental_data_to_db(fundamental_datas)
    logger.info("Fundamental data saved to database successfully")

    logger.info(f"get_and_save_node execution completed successfully")
    return {"documents": fundamental_datas}


def fundamental_analysis_node(state: FAOverallState):
    """AI node for fundamental analysis"""
    logger.info("Starting fundamental_analysis_node execution")

    llm_model = get_llm(temperature=0.2)
    structured_llm = llm_model.with_structured_output(FAOutput)
    system_prompt = """
    You are a meticulous and deeply knowledgeable cryptocurrency fundamental analyst. Your expertise lies in dissecting project documentation, such as whitepapers and official websites, to produce a comprehensive and objective investment-style analysis.
    You are not a financial advisor and you do not give price predictions. Your sole purpose is to evaluate a project's fundamentals based only on the information provided. You must support every analytical point with direct evidence from the source documents.
    """

    documents = state["documents"]
    logger.info(f"Processing fundamental analysis for {len(documents)} documents")

    fa_analysis_list = []
    for i, doc in enumerate(documents):
        logger.info(f"Analyzing document {i+1}/{len(documents)} - Token ID: {doc.get('token_id', 'Unknown')}")
        
        token_identity = get_token_identity(doc["token_id"])
        if token_identity:
            doc["token_name"] = token_identity["name"]
            logger.info(f"Token identity resolved: {token_identity['name']}")
        else:
            logger.warning(f"Could not resolve token identity for token_id: {doc['token_id']}")

        user_prompt = f"""
        <fundamental_data>
        {doc}
        </fundamental_data>

        You have been provided with structured data and the full text of key documents for a single cryptocurrency project.
        Your Task:
        Conduct a comprehensive fundamental analysis of the project. Your analysis must be structured into the following sections:
        Project Summary: Briefly explain what the project is and what problem it aims to solve.
        Technology & Use Case: Analyze the core technology and the primary utility of the project's token. Is the use case compelling and essential for the ecosystem?
        Tokenomics: Analyze the token's economic model. Discuss its supply (total, max, circulating), its distribution (team, investors, community), and any inflationary or deflationary mechanisms.
        Team & Roadmap: Assess the team's background (if available) and the clarity and ambition of their future roadmap.

        Crucial Instructions:
        The "token_name" is just a string of the token name being analyzed.
        The "fundamental_analysis" value should be a single string containing your full, well-structured analysis in markdown format.
        The "proof" value should be data that support the analysis result, such as tokenomics data, quote from the whitepaper, etc.
        """
        
        logger.info(f"Invoking LLM for fundamental analysis of token {i+1}")
        result = structured_llm.invoke([SystemMessage(content=system_prompt)]+[HumanMessage(content=user_prompt)])
        if result:
            fa_analysis_list.append(result)
    logger.info(f"All fundamental analyses completed. Generated {len(fa_analysis_list)} analysis reports")
    logger.info(f"fundamental_analysis_node execution completed successfully")
    return {"final_fa_report": fa_analysis_list}


def fa_graph():
    """
    Fundamental Analysis (FA) graph setup.
    Input State:
    - token_ids: List of token IDs to analyze.

    Output State:
    - final_fa_report: The final fundamental analysis report. List of FAOutput objects containing token name, analysis, and proof.
    """

    logger.info("Setting up Fundamental Analysis (FA) graph")
    
    graph = StateGraph(FAOverallState, input_schema=FAInputState, output_schema=FAOutputState)
    graph.add_node("get_and_save", get_and_save_node)
    graph.add_node("fundamental_analysis", fundamental_analysis_node)
    
    graph.add_edge(START, "get_and_save")
    graph.add_edge("get_and_save", "fundamental_analysis")
    graph.add_edge("fundamental_analysis", END)

    logger.info("Graph nodes and edges configured successfully")
    fa_graph = graph.compile()
    logger.info("FA graph compiled successfully")

    return fa_graph
