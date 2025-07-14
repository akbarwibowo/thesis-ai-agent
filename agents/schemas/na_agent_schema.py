from typing import List, TypedDict, Annotated
from pydantic import BaseModel, Field
from operator import add



class NAInputState(TypedDict):
    """the input of the narrative sub-graph"""
    twitter_scrape_keywords: List[str]
    twitter_scrape_max_tweets: int
    cointelegraph_max_articles: int



class NAOutputState(TypedDict):
    """the output of the narrative sub-graph"""
    narrative_analysis: str
    evidence: List[str | int]



class NAMapReducer(BaseModel):
    """the map reducer for narrative data"""
    summary: str = Field(description="The summary of the narrative documents")
    quote: List[str] = Field(description="A direct quote from the narrative documents. Could be a single quote or multiple quotes.")
    evidence_id: List[str | int] = Field(description="The evidence for the narrative documents")



class NAOverallState(NAInputState, NAOutputState):
    """the overall state of the narrative sub-graph"""
    db_collection: str
    chunked_documents: List[List[dict[str, str]]]
    reduced_documents: List[NAMapReducer]
    final_na_report: str
