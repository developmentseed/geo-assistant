import base64
from typing import NotRequired

from geojson_pydantic import Feature
from langchain.agents import AgentState
from pydantic import Field, field_serializer


class GeoAssistantState(AgentState):
    place: NotRequired[Feature | None] = None
    search_area: NotRequired[Feature | None] = None
    naip_img_bytes: NotRequired[bytes | None] = Field(
        default=None,
        description="Bytes of the saved NAIP RGB PNG image",
    )

    @field_serializer("naip_img_bytes")
    def serialize_naip_img_bytes(self, value: bytes | None) -> str | None:
        """Convert bytes to base64-encoded string for JSON serialization."""
        if value is None:
            return None
        return base64.b64encode(value).decode("utf-8")
