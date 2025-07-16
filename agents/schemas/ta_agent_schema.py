from typing import TypedDict, List
from pydantic import BaseModel, Field



class TAInputState(TypedDict):
    """the input of the ta sub-graph"""
    token_ids: List[str]



class TAOutput(BaseModel):
    """the output of the ta sub-graph"""
    token_name: str = Field(description="The name of the token")
    technical_analysis: str = Field(description="The technical analysis results")
    evidence: List[str] = Field(description="The evidence supporting the analysis based on the technical data without duplicates")



class TAOutputState(TypedDict):
    """the output state of the ta sub-graph"""
    final_ta_report: List[TAOutput]



class TAOverallState(TAInputState, TAOutputState):
    """the overall state of the ta sub-graph"""
    documents: List[dict]