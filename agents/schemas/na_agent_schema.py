from typing import List, TypedDict, Annotated
from operator import add



class NAInputState(TypedDict):
    """the input of the narrative sub-graph"""
    start_command: str



class NAOutputState(TypedDict):
    """the output of the narrative sub-graph"""
    narrative_analysis: str
    evidence: List[str | int]



class NAOverallState(TypedDict):
    """the overall state of the narrative sub-graph"""
    db_collection: str
    documents: List[dict]



class NAMapReducer(TypedDict):
    """the map reducer for narrative data"""
    reduce: Annotated[List[str], add]
    evidence: Annotated[List[str | int], add]