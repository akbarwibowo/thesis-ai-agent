from typing import List, TypedDict


class NarrativeInputState(TypedDict):
    """the input of the narrative sub-graph"""
    start_command: str



class NarrativeOutputState(TypedDict):
    """the output of the narrative sub-graph"""
    narrative_analysis: str
    evidence: List[str | int]



class NarrativeOverallState(TypedDict):
    """the overall state of the narrative sub-graph"""
    db_collection: str
    documents: List[dict]



class MapReducer(TypedDict):
    """the map reducer for narrative data"""
    reduce: str
    evidence: List[str | int]