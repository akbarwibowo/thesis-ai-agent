import sys
import logging
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.join(current_dir, '..', '..')
sys.path.insert(0, project_root)


logging.basicConfig(
    level=logging.INFO,  # Set to DEBUG to see debug messages too
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # This outputs to console/terminal
    ]
)


from agents.tools.narrative_data_getter.narrative_module import get_narrative_data, save_narrative_data_to_db, collection_name
from agents.tools.databases.mongodb import retrieve_documents
from agents.schemas.na_agent_schema import NAInputState, NAMapReducer, NAOutputState, NAOverallState
from agents.llm_model import llm_model
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import START, END, StateGraph
from langchain_core.messages import SystemMessage, HumanMessage



def scraping_node(state: NAInputState):
    """Scrape narrative data from various sources and store it in the database."""
    twitter_scrape_keywords = state['twitter_scrape_keywords']
    twitter_max_tweets = state['twitter_scrape_max_tweets']
    cointelegraph_max_articles = state['cointelegraph_max_articles']

    documents = get_narrative_data(
        twitter_scrape_keywords=twitter_scrape_keywords,
        twitter_scrape_max_tweets=twitter_max_tweets,
        cointelegraph_max_articles=cointelegraph_max_articles
    )
    save_narrative_data_to_db(documents)

    return {"db_collection": collection_name}


def retrieve_node(state: NAOverallState):
    """Retrieve narrative data from the database."""
    db_collection = state["db_collection"]
    documents = retrieve_documents(db_collection)
    chunked_documents = []
    for i in range(len(documents)):
        chunked_documents.append(documents[i:i + 10])  # Chunking documents into groups of 10

    return {"chunked_documents": chunked_documents}


def map_reduces_node(state: NAOverallState):
    """Map and reduce the narrative data."""
    structured_llm = llm_model.with_structured_output(NAMapReducer)
    documents = state["chunked_documents"]
    reduced_documents = []

    for doc in documents:
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

        result = structured_llm.invoke([SystemMessage(content=system_prompt)]+[HumanMessage(content=user_prompt)])

        reduced_documents.append(result)

        
    return {"reduced_documents": reduced_documents}


def narrative_analysis_node(state: NAOverallState):
    """AI node for narrative analysis"""
    llm = llm_model

    reduced_documents = state["reduced_documents"]
    documents = []

    for doc in reduced_documents:
        documents.append({
            "description": doc.summary,
            "quote": doc.quote,
            "evidence_id": doc.evidence_id
        })

    system_prompt = """
    You are an expert-level cryptocurrency market analyst. Your primary skill is synthesizing large volumes of information from news articles and social media posts to identify the single most significant, emerging market narrative. You are a master at pattern recognition and making connections between disparate pieces of information.

    Your analysis must be objective, data-driven, and strictly based on the information provided. Do not introduce any outside knowledge or speculation. Your most important duty is to provide concrete evidence for every claim you make by citing the specific documents that support your conclusions.
    """
    
    user_prompt = """
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

    If no significant narrative is identified: Your output should be a single line: No significant emerging narrative was identified from the provided data.

    Example of a good analysis output (if a narrative is found):

    Emerging Narrative: Institutional Adoption of Real World Assets (RWA)
    The primary driver behind the RWA trend appears to be direct institutional involvement. Major financial players are no longer just observing; they are actively building products in this space [101]. This move has been further validated by significant on-chain data showing a 40% increase in capital inflows to relevant protocols over the last month [210, 211].

    """
    result = llm.invoke([SystemMessage(content=system_prompt)]+[HumanMessage(content=user_prompt)], documents=documents)
    return {"final_na_report": result}

na_graph = StateGraph(NAOverallState, input_schema=NAInputState, output_schema=NAOutputState)
na_graph.add_node('scraping', scraping_node)
na_graph.add_node('retrieve', retrieve_node)
na_graph.add_node('map_reduces', map_reduces_node)
na_graph.add_node('narrative_analysis', narrative_analysis_node)

na_graph.add_edge(START, 'scraping')
na_graph.add_edge('scraping', 'retrieve')
na_graph.add_edge('retrieve', 'map_reduces')
na_graph.add_edge('map_reduces', 'narrative_analysis')
na_graph.add_edge('narrative_analysis', END)

memory = InMemorySaver()
graph = na_graph.compile(checkpointer=memory)


config = {"configurable": {"thread_id": "1"}}

result = graph.invoke({"twitter_scrape_keywords": ["crypto", "blockchain"], "twitter_scrape_max_tweets": 100, "cointelegraph_max_articles": 5}, config) # type: ignore

print(result)
