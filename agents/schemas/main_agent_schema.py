import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.join(current_dir, '..', '..')
sys.path.insert(0, project_root)

from typing import List, TypedDict
from pydantic import BaseModel, Field
from agents.schemas.ta_agent_schema import TAOutput
from agents.schemas.fa_agent_schema import FAOutput



class MainState(TypedDict):
    start_command: str
    token_ids: List[str]
    twitter_scrape_keywords: List[str]
    identified_narratives: List[str]
    twitter_scrape_max_tweets: int
    cointelegraph_max_articles: int
    final_na_report: str # populated by the NA graph
    final_ta_report: List[TAOutput] # populated by the TA graph
    final_fa_report: List[FAOutput] # populated by the FA graph
    final_analysis_report: str
    categories_with_tokens: List[dict]  # List of categories with their tokens and names



class NAIdentifierOutput(BaseModel):
    narratives: List[str] = Field(description="Identified narrative(s) based on the analysis report")
