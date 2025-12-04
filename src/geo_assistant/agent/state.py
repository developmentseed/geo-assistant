from langchain.agents import AgentState as BaseAgentState
from geojson_pydantic import FeatureCollection
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


class AgentState(BaseAgentState):
    feature_collection: Optional[FeatureCollection] = Field(
        default=None, description="FeatureCollection to be used for the analysis"
    )
    naip_image: Optional[NaipImageInfo] = Field(
        default=None, description="Information about the fetched NAIP image"
    )
