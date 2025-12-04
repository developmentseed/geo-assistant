from langchain.agents import AgentState as BaseAgentState
from geojson_pydantic import FeatureCollection
from typing import Optional
from pydantic import Field


class AgentState(BaseAgentState):
    feature_collection: Optional[FeatureCollection] = Field(
        default=None, description="FeatureCollection to be used for the analysis"
    )
