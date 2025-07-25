from typing import List, TypedDict
from pydantic import BaseModel, Field



class NAInputState(TypedDict):
    """the input of the narrative sub-graph"""
    twitter_scrape_max_tweets: int
    cointelegraph_max_articles: int



class NATwitterKeywords(BaseModel):
    """the Twitter keywords for scraping"""
    twitter_scrape_keywords: List[str] = Field(default_factory=list, description="List of keywords to scrape Twitter for crypto narratives")



class NAOutput(BaseModel):
    """the output of the narrative sub-graph"""
    narrative_analysis: str = Field(description="the report of narrative analysis")
    evidence: List[str | int] = Field(description="the evidence id(s) being used to support the analysis result without dupliacates")



class NAMapReducer(BaseModel):
    """the map reducer for narrative data"""
    summary: str = Field(description="The summary of the narrative documents")
    quote: List[str] = Field(description="A direct quote from the narrative documents. Could be a single quote or multiple quotes.")
    evidence_id: List[str | int] = Field(description="The evidence for the narrative documents")



class NAOutputState(TypedDict):
    final_na_report: str



class NAOverallState(NAInputState, NAOutputState):
    """the overall state of the narrative sub-graph"""
    db_collection: str
    chunked_documents: List[List[dict[str, str]]]
    reduced_documents: List[NAMapReducer]
    twitter_scrape_keywords: List[str]
