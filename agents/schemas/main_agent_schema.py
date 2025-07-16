from typing import List, TypedDict, Annotated
from operator import add
from ta_agent_schema import TAOutputState
from fa_agent_schema import FAOutputState



class MainState(TypedDict):
    start_command: str
    token_ids: List[str]
    twitter_scrape_keywords: List[str]
    twitter_scrape_max_tweets: int
    cointelegraph_max_articles: int
    final_na_report: str
    final_ta_report: TAOutputState
    final_fa_report: FAOutputState
    final_analysis_report: str