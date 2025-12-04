from langchain.agents import AgentState
from geojson_pydantic import Feature
from typing import Optional


class GeoAssistantState(AgentState):
    place: Optional[Feature]
    search_area: Optional[Feature]
