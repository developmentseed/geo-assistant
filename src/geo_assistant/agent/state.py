from langchain.agents import AgentState
from geojson_pydantic import Feature
from typing import Optional
from pydantic import Field


class GeoAssistantState(AgentState):
    place: Optional[Feature]
    search_area: Optional[Feature]
    naip_png_path: Optional[str] = Field(
        default=None, description="Path to the saved NAIP RGB PNG image"
    )
