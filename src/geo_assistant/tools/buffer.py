import geopandas as gpd
from langgraph.types import Command
from langgraph.prebuilt import InjectedState
from langchain_core.tools.base import InjectedToolCallId
from langchain_core.messages import ToolMessage
from langchain_core.tools import tool
from typing import Annotated
from geo_assistant.agent.state import GeoAssistantState
from geojson_pydantic import Feature


@tool
async def get_search_area(
    buffer_size_km: float,
    state: Annotated[GeoAssistantState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId] = "",
) -> Command:
    """Get a search area buffer in km around the place defined in the agent state."""

    place_feature = state.get("place")

    if not place_feature:
        return Command(
            update={
                "messages": [
                    ToolMessage(
                        content="No place defined in the agent state to create a search area around.",
                        tool_call_id=tool_call_id,
                    )
                ],
            }
        )

    # Convert GeoJSON feature to GeoDataFrame
    gdf = gpd.GeoDataFrame.from_features(features=[place_feature])
    gdf.crs = "EPSG:4326"

    gdf_m = gdf.to_crs(epsg=3857)  # latlon to Web Mercator for meter-based buffering

    gdf_m["geometry"] = gdf_m["geometry"].buffer(
        buffer_size_km * 1000
    )  # Buffer in meters
    gdf = gdf_m.to_crs(epsg=4326)  # Back to WGS84

    # Convert back to GeoJSON feature
    if len(gdf) != 1:
        raise ValueError(
            f"{len(gdf)} features found after buffer operation, should be just 1. "
            "Was a Multi-Point/LineString/Polygon geometry passed in?"
        )
    buffer_feature = Feature(
        type="Feature",
        geometry=gdf.iloc[0].geometry.__geo_interface__,
        properties=place_feature["properties"].copy(),
    )

    return Command(
        update={
            "search_area": buffer_feature,
            "messages": [
                ToolMessage(
                    content=f"Created search area geometry buffer of {buffer_size_km} km around the place.",
                    tool_call_id=tool_call_id,
                )
            ],
        }
    )
