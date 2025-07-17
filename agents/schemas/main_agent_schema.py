from typing import List, TypedDict
from pydantic import BaseModel, Field
from ta_agent_schema import TAOutput
from fa_agent_schema import FAOutput



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



class NAIdentifierOutput(BaseModel):
    narratives: List[str] = Field(description="Identified narrative(s) based on the analysis report")
