from langchain.agents import AgentState
from geojson_pydantic import Feature
from typing import Optional
from pydantic import Field, BaseModel


class DatasetDims(BaseModel):
    time: int
    band: Optional[int]
    y: int
    x: int


class NaipImageInfo(BaseModel):
    stac_item_count: int
    dataset_dims: DatasetDims
    png_path: str


class GeoAssistantState(AgentState):
    place: Optional[Feature]
    search_area: Optional[Feature]
    naip_image: Optional[NaipImageInfo] = Field(
        default=None, description="Information about the fetched NAIP image"
    )
