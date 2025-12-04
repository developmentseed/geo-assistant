from langchain.agents import AgentState as BaseAgentState
from geojson_pydantic import FeatureCollection
from typing import Optional


class AgentState(BaseAgentState):
    place: Optional[FeatureCollection]
