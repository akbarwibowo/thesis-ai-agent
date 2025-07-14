from typing import List, TypedDict, Annotated
from operator import add



class FAInputState(TypedDict):
    """the input of the fa sub-graph"""
    start_command: str



class FAOutputState(TypedDict):
    """the output of the fa sub-graph"""
    token_name: Annotated[List[str], add]
    fundamental_analysis: Annotated[List[str], add]
    evidence: Annotated[List[str | int], add]



class FAOverallState(TypedDict):
    """the overall state of the fa sub-graph"""
    db_collection: Annotated[List[str], add]
    documents: Annotated[List[dict], add]
    token_name: Annotated[List[str], add]
    fundamental_analysis: Annotated[List[str], add]
    evidence: Annotated[List[str | int], add]