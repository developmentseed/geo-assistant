from json import tool
import shapely
import geopandas as gpd
from langgraph.types import Command
from langraph.prebuild import InjectedState
from langchain_core.tools.base import InjectedToolCallId
from langchain_core.messages import ToolMessage
from typing import Annotated
from geo_assistant.agent.state import AgentState


@tool
def get_search_area(
    buffer_size_km: int,
    state: Annotated[AgentState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId] = "",
) -> Command:
    """Get a search area buffer in km around the place defined in the agent state."""

    place_feature_collection = state.get_current().place  # type: ignore[attr-defined]

    if not place_feature_collection:
        raise ValueError("No place defined in the agent state.")

    # Convert GeoJSON FeatureCollection to GeoDataFrame
    gdf = gpd.GeoDataFrame.from_features(place_feature_collection["features"])

    # Create a buffer of 1 km around the place
    gdf_m = gdf.to_crs(epsg=3857)  # Web Mercator for meter-based buffering

    gdf_m["geometry"] = gdf_m["geometry"].apply(
        lambda geom: shapely.geometry.shape(geom).buffer(
            buffer_size_km * 1000
        )  # to-do reproject
    )
    gdf = gdf_m.to_crs(epsg=4326)  # Back to WGS84

    # Convert back to GeoJSON FeatureCollection
    buffer_feature_collection = gdf.__geo_interface__

    return Command(
        update={
            "search_area": buffer_feature_collection,
            "messages": [
                ToolMessage(
                    content=f"Created search area geometry buffer of {buffer_size_km} km around the place.",
                    tool_call_id=tool_call_id,
                )
            ],
        }
    )
