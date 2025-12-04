from langchain.agents import AgentState
from geojson_pydantic import FeatureCollection
from typing import Optional


class GeoAssistantState(AgentState):
    place: Optional[FeatureCollection]
    search_area: Optional[FeatureCollection]
