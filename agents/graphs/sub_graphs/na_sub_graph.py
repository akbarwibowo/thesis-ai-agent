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


from agents.tools.narrative_data_getter.narrative_module import get_narrative_data, save_narrative_data_to_db, collection_name
from agents.tools.databases.mongodb import retrieve_documents
from agents.tools.narrative_data_getter.news_data_getter import get_coindesk
from agents.schemas.na_agent_schema import NAInputState, NAMapReducer, NAOutput, NAOverallState, NAOutputState, NATwitterKeywords
from agents.llm_model import get_llm
from langgraph.graph import START, END, StateGraph
from langchain_core.messages import SystemMessage, HumanMessage



def twitter_keywords_node(state: NAInputState):
    """Node to set Twitter keywords for scraping"""
    logger.info("Starting twitter_keywords_node execution")
    twitter_scrape_max = state["twitter_scrape_max_tweets"]
    if twitter_scrape_max > 0:
        news_samples = get_coindesk()
        news_samples = [news.pop("published_at") for news in news_samples]

        system_prompt = """
        You are a crypto market intelligence analyst. Your expertise is in reading news headlines and summaries to identify new, emerging, or rapidly accelerating market narratives. You are skilled at extracting the most potent and specific search terms that can be used to find high-signal conversations.
        """
        user_prompt = f"""
        Your task is to act as a research assistant. Analyze the provided sample of recent crypto news headlines below.
        Based on this sample, identify and extract the 3 to 10 most relevant keywords or multi-word phrases that should be used to search for more related data on social media platforms like X (Twitter).
        Focus on identifying keywords that represent cryptocurrency categories or narratives, such as 'AI Agents', 'DeFi', 'RWA', 'Layer 2', or 'GameFi'. Prioritize topics that seem to be new, emerging, or accelerating in importance. Avoid overly generic terms like "crypto" or "bitcoin" unless they are part of a more specific phrase (e.g., "Bitcoin ETF inflows").

        Example:
        Input Headlines: A list of articles discussing tokenized treasuries, decentralized lending protocols, and new AI-powered trading bots.

        Your Output: ["Real World Assets (RWA)", "DeFi Lending", "AI Agents"]

        If there is no clear emerging narrative, return an empty list [].

        News Headlines to Analyze:
        <news_samples>
        {news_samples}
        </news_samples>
        """
        llm_model = get_llm(temperature=0.4)
        structured_llm = llm_model.with_structured_output(NATwitterKeywords)
        logger.info("Invoking LLM to extract Twitter keywords")
        result = structured_llm.invoke([SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)])
        twitter_scrape_keywords = result.twitter_scrape_keywords if result.twitter_scrape_keywords else [] # type: ignore
        logger.info(f"Extracted Twitter keywords: {twitter_scrape_keywords}")
        logger.info("twitter_keywords_node execution completed successfully")

        return {"twitter_scrape_keywords": twitter_scrape_keywords}
    else:
        logger.info("No Twitter scraping required")
        return {"twitter_scrape_keywords": []}


def scraping_node(state: NAOverallState):
    """Scrape narrative data from various sources and store it in the database."""
    logger.info("Starting scraping_node execution")
    
    twitter_scrape_keywords = state['twitter_scrape_keywords']
    twitter_max_tweets = state['twitter_scrape_max_tweets']
    cointelegraph_max_articles = state['cointelegraph_max_articles']

    logger.info(f"Scraping parameters - Twitter keywords: Max tweets: {twitter_max_tweets}, CoinTelegraph articles: {cointelegraph_max_articles}")

    logger.info("Calling get_narrative_data to scrape sources")
    documents = get_narrative_data(
        twitter_scrape_keywords=twitter_scrape_keywords,
        twitter_scrape_max_tweets=twitter_max_tweets,
        cointelegraph_max_articles=cointelegraph_max_articles
    )
    
    logger.info(f"Successfully scraped {len(documents)} documents")
    logger.info("Saving narrative data to database")
    save_narrative_data_to_db(documents)
    logger.info(f"Documents saved to collection: {collection_name}")

    logger.info("scraping_node execution completed successfully")
    return {"db_collection": collection_name}


def retrieve_node(state: NAOverallState):
    """Retrieve narrative data from the database."""
    logger.info("Starting retrieve_node execution")
    db_collection = state["db_collection"]
    documents = retrieve_documents(collection_name=db_collection)
    logger.info(f"Retrieved {len(documents)} documents from database")
    
    chunk_length = 20
    chunked_documents = []
    for i in range(0, len(documents), chunk_length):
        chunked_documents.append(documents[i:i + chunk_length])  # Chunking documents into groups of chunk_length

    logger.info(f"Documents chunked into {len(chunked_documents)} groups of up to {chunk_length} documents each")
    logger.info("retrieve_node execution completed successfully")
    return {"chunked_documents": chunked_documents}


def map_reduces_node(state: NAOverallState):
    """Map and reduce the narrative data."""
    logger.info("Starting map_reduces_node execution")
    
    llm_model = get_llm(temperature=0.4)
    structured_llm = llm_model.with_structured_output(NAMapReducer)
    documents = state["chunked_documents"]
    reduced_documents = []

    logger.info(f"Processing {len(documents)} document chunks for map-reduce operation")
    
    for i, doc in enumerate(documents):
        logger.info(f"Processing document chunk {i+1}/{len(documents)}")
        
        system_prompt = """
        You are a highly efficient cryptocurrency related data processing engine. Your purpose is to read a small batch of documents (news articles and social media posts) and extract key information in a structured JSON format. You must be objective and only use information explicitly present in the provided text. Do not add any outside opinions or analysis.
        """
        user_prompt = f"""
        Analyze the following list of documents. 
        
        <documents>
        {doc}
        </documents>

        Your task is to generate a concise summary and a provide the most important pieces of supporting evidence found within the documents.

        Instructions:

        Read all the provided documents carefully.

        Determine if the documents contain any relevant information about cryptocurrency narratives, specific projects, market-moving events (like partnerships or regulations), or significant market sentiment.

        Generate the "summary" of the documents and provide the quote with the evidence_id as your output.

        For the "summary": Write a short, one paragraph of maximum ten sentences summary of the main topics, projects, and overall sentiment discussed in this batch of documents.

        For the "quote": A direct, concise quote from the document's "description" that serves as evidence. not the full description if the description is more than three sentences long, only the selected sentence to quote.

        For the "evidence_id": The list of single or multiple integer ID of the source document that is being quoted.

        Extract no more than 5 of the most impactful pieces of evidence from this batch.

        If you determine that this batch contains no relevant information, you MUST return the following pattern and nothing else:

        "summary": "No relevant information found in this chunk."
        "quote": []
        "evidence_id": []
        """

        logger.info(f"Invoking LLM for chunk {i+1} with {len(doc)} documents")
        result = structured_llm.invoke([SystemMessage(content=system_prompt)]+[HumanMessage(content=user_prompt)])
        logger.info(f"Chunk {i+1} processed successfully")
        if result:
            reduced_documents.append(result)

    logger.info(f"Map-reduce completed. Generated {len(reduced_documents)} reduced document summaries")
    logger.info(f"example of the recuded documents: {reduced_documents[0]}")
    logger.info("map_reduces_node execution completed successfully")
    return {"reduced_documents": reduced_documents}


def narrative_analysis_node(state: NAOverallState) -> NAOutputState:
    """AI node for narrative analysis"""
    logger.info("Starting narrative_analysis_node execution")
    
    llm_model = get_llm(temperature=0.3)
    structured_llm = llm_model.with_structured_output(NAOutput)
    
    reduced_documents = state["reduced_documents"]
    logger.info(f"Processing {len(reduced_documents)} reduced documents for narrative analysis")
    
    documents = []

    for i, doc in enumerate(reduced_documents):
        logger.info(f"Converting reduced document {i+1}/{len(reduced_documents)} to analysis format")
        documents.append({
            "description": doc.summary,
            "quote": doc.quote,
            "evidence_id": doc.evidence_id
        })

    logger.info(f"Prepared {len(documents)} documents for final narrative analysis")

    system_prompt = """
    You are an expert-level cryptocurrency market analyst. Your primary skill is synthesizing large volumes of information from news articles and social media posts to identify the single most significant, emerging market narrative. You are a master at pattern recognition and making connections between disparate pieces of information.

    Your analysis must be objective, data-driven, and strictly based on the information provided. Do not introduce any outside knowledge or speculation. Your most important duty is to provide concrete evidence for every claim you make by citing the specific documents that support your conclusions.
    """
    
    user_prompt = f"""
    <documents>
    {documents}
    </documents>

    You have been provided with a list of document summaries. Each summary represents a small batch of recent news articles and social media posts. The content of each summary is a concise analysis of the topics, projects, and sentiment discussed within its original documents.

    Your task is to perform the following steps:

    Synthesize All Summaries: Read through all the provided summaries to get a holistic view of the current market conversation.

    Identify the Dominant Narrative: Determine the single most significant, emerging narrative. This could be a technology (e.g., "AI & Crypto"), a sector (e.g., "Real World Assets - RWA"), or a market trend (e.g., "Institutional DeFi Adoption").

    Construct a Detailed Analysis: Write a comprehensive analysis explaining why this narrative is emerging. Your analysis should cover key aspects such as:

    The core concept of the narrative.

    The key projects or players involved.

    The primary drivers (e.g., new technology, institutional investment, regulatory changes, high-profile partnerships).

    Provide Evidence with Citations: This is the most critical step. For every claim or key point in your analysis, you MUST provide supporting evidence by citing the id of the original document(s) that support that claim. You should format citations as [id]. You can cite multiple documents for a single claim, like [id_1, id_2, id_3].

    Your final output must be a single, well-structured markdown block. Do not include any conversational text before or after your analysis.

    If a narrative is identified: Structure your output with a main title for the narrative, followed by your detailed analysis with citations.

    If no significant narrative is identified: Your output should be a single line: "No significant emerging narrative was identified from the provided data."

    Example of a good analysis output (if a narrative is found):

    Emerging Narrative: Institutional Adoption of Real World Assets (RWA)
    The primary driver behind the RWA trend appears to be direct institutional involvement. Major financial players are no longer just observing; they are actively building products in this space [101]. This move has been further validated by significant on-chain data showing a 40% increase in capital inflows to relevant protocols over the last month [210, 211].

    """
    
    logger.info("Invoking LLM for final narrative analysis")
    result = structured_llm.invoke([SystemMessage(content=system_prompt)]+[HumanMessage(content=user_prompt)])

    logger.info(f"Narrative analysis completed - Report length: {len(str(result))} characters")
    
    # Error handling for None result
    if result is None:
        logger.error("LLM returned None result for narrative analysis")
        error_report = """
        # NARRATIVE ANALYSIS REPORT
        Error: Unable to generate narrative analysis due to LLM failure.
        ## NARRATIVE REPORT PROOF ID
        []
        """
        return {"final_na_report": error_report}
    
    # Error handling for missing attributes
    if not hasattr(result, 'narrative_analysis'):
        logger.error("LLM result missing 'narrative_analysis' attribute")
        error_report = """
        # NARRATIVE ANALYSIS REPORT  
        Error: Invalid LLM response format - missing narrative analysis content.
        ## NARRATIVE REPORT PROOF ID
        []
        """
        return {"final_na_report": error_report}
    
    logger.info("narrative_analysis_node execution completed successfully")

    result_str = result.narrative_analysis # type: ignore
    result_evidence_str = str(result.evidence) if hasattr(result, 'evidence') else "[]" # type: ignore
    final_report_structure = f"""
    # NARRATIVE ANALYSIS REPORT
    {result_str}
    ## NARRATIVE REPORT PROOF ID
    {result_evidence_str}
    """.lstrip()

    return {"final_na_report": final_report_structure}


def na_graph():
    """
    Narrative Analysis (NA) graph setup.
    Input State:
    - twitter_scrape_keywords: List of keywords for Twitter scraping.
    - twitter_scrape_max_tweets: Maximum number of tweets to scrape.
    - cointelegraph_max_articles: Maximum number of articles to scrape from Cointelegraph.

    Output State:
    - final_na_report: The final narrative analysis report.
    """
    logger.info("Setting up Narrative Analysis (NA) graph")

    na_graph = StateGraph(NAOverallState, input_schema=NAInputState, output_schema=NAOutputState)
    na_graph.add_node("twitter_keywords", twitter_keywords_node)
    na_graph.add_node('scraping', scraping_node)
    na_graph.add_node('retrieve', retrieve_node)
    na_graph.add_node('map_reduces', map_reduces_node)
    na_graph.add_node('narrative_analysis', narrative_analysis_node)

    na_graph.add_edge(START, "twitter_keywords")
    na_graph.add_edge("twitter_keywords", 'scraping')
    na_graph.add_edge('scraping', 'retrieve')
    na_graph.add_edge('retrieve', 'map_reduces')
    na_graph.add_edge('map_reduces', 'narrative_analysis')
    na_graph.add_edge('narrative_analysis', END)

    logger.info("Graph nodes and edges configured successfully")

    graph = na_graph.compile()

    logger.info("Graph compiled successfully")

    return graph
