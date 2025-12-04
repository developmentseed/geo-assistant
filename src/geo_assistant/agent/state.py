from langchain.agents import AgentState as BaseAgentState
from geojson_pydantic import FeatureCollection
from typing import Optional


class GeoAssistantState(BaseAgentState):
    place: Optional[FeatureCollection]
    search_area: Optional[FeatureCollection]
