from typing import NotRequired

from geojson_pydantic import Feature
from langchain.agents import AgentState
from pydantic import Field


class GeoAssistantState(AgentState):
    place: NotRequired[Feature | None] = None
    search_area: NotRequired[Feature | None] = None
    naip_img_bytes: NotRequired[bytes | None] = Field(
        default=None,
        description="Bytes of the saved NAIP RGB PNG image",
    )
