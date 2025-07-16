from typing import List, TypedDict
from pydantic import BaseModel, Field



class FAInputState(TypedDict):
    """the input of the fa sub-graph"""
    token_ids: List[str]



class FAOutput(BaseModel):
    """the output of the fa sub-graph"""
    token_name: str = Field(description="The name of the token")
    fundamental_analysis: str = Field(description="The fundamental analysis results")
    evidence: List[str] = Field(description="The evidence supporting the analysis based on the fundamental data without duplicates")



class FAOutputState(TypedDict):
    """the output state of the fa sub-graph"""
    final_fa_report: List[FAOutput]



class FAOverallState(FAInputState, FAOutputState):
    """the overall state of the fa sub-graph"""
    documents: List[dict]