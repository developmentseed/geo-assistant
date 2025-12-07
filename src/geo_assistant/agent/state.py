"""State schema for the geo-assistant agent."""

from typing import NotRequired

from geojson_pydantic import Feature, FeatureCollection
from langchain.agents import AgentState
from pydantic import Field


class GeoAssistantState(AgentState):
    place: NotRequired[Feature | None] = None
    search_area: NotRequired[Feature | None] = None
    places_within_buffer: NotRequired[FeatureCollection | None] = None
    naip_img_bytes: NotRequired[str | None] = Field(
        default=None,
        description="Base 64 encoded bytes str of the saved NAIP RGB JPEG image",
    )
