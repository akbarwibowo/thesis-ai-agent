from typing import TypedDict, List, Annotated
from operator import add



class TAInputState(TypedDict):
    """the input of the technical analysis sub-graph"""
    start_command: str



class TAOutputState(TypedDict):
    """the output of the technical analysis sub-graph"""
    token_name: Annotated[List[str], add]
    technical_analysis: Annotated[List[str], add]
    evidence: Annotated[List[str | int], add]