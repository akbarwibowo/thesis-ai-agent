from typing import TypedDict, List
from pydantic import BaseModel, Field



class TAInputState(TypedDict):
    """the input of the ta sub-graph"""
    token_ids: List[str]



class TAOutput(BaseModel):
    """
    A structured output schema for the Technical Analysis Agent.
    Each field corresponds to a specific section of the analysis requested in the prompt.
    """
    token_name: str = Field(
        description="The name or symbol of the token being analyzed."
    )
    
    trend_analysis: str = Field(
        description="The analysis of the overall trend, based on the price's relationship with its moving averages (SMA and EMA)."
    )
    
    momentum_analysis: str = Field(
        description="The analysis of market momentum, based on the interpretation of the RSI (Relative Strength Index) values."
    )
    
    volume_analysis: str = Field(
        description="The analysis of trading volume and how it confirms or contradicts the recent price action."
    )
    
    synthesis_and_outlook: str = Field(
        description="A concluding summary that synthesizes all the above points into a final technical outlook for the token."
    )



class TAOutputState(TypedDict):
    """the output state of the ta sub-graph"""
    final_ta_report: List[TAOutput]



class TAOverallState(TAInputState, TAOutputState):
    """the overall state of the ta sub-graph"""
    price_data: List[dict]