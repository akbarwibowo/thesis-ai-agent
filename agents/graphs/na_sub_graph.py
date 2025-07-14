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
    
    

    return {"narrative_analysis": "AI-generated narrative analysis", "evidence": [1, 2, 3]}

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
