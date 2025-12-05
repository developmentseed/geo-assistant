from langchain.agents import AgentState
from geojson_pydantic import Feature
from typing import NotRequired
from pydantic import Field


class GeoAssistantState(AgentState):
    place: NotRequired[Feature | None] = None
    search_area: NotRequired[Feature | None] = None
    naip_png_path: NotRequired[str | None] = Field(
        default=None, description="Path to the saved NAIP RGB PNG image"
    )
