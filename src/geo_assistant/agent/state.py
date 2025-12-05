from langchain.agents import AgentState
from geojson_pydantic import Feature, FeatureCollection
from typing import Optional


class GeoAssistantState(AgentState):
    place: Optional[Feature]
    search_area: Optional[Feature]
    places_within_buffer: Optional[FeatureCollection]
