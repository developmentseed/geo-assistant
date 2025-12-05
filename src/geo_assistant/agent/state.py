from langchain.agents import AgentState
from geojson_pydantic import Feature
from typing_extensions import NotRequired


class GeoAssistantState(AgentState):
    place: NotRequired[Feature | None] = None
    search_area: NotRequired[Feature | None] = None
