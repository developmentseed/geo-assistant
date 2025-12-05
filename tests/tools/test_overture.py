import os
import pytest
from langchain_core.tools.base import ToolCall
from shapely.geometry import Point
from geojson_pydantic import Feature
import geopandas as gpd
from geo_assistant.agent.state import GeoAssistantState

from geo_assistant.tools.overture import get_place
from src.geo_assistant.tools.overture import get_places_within_buffer


@pytest.fixture(autouse=True)
def setup_ci_env():
    """Configure S3 source for CI environments."""
    # Detect CI environment (GitHub Actions, GitLab CI, etc.)
    if os.getenv("CI") or os.getenv("GITHUB_ACTIONS"):
        os.environ["OVERTURE_SOURCE"] = "s3"
        os.environ["OVERTURE_S3_PATH"] = (
            "s3://overturemaps-us-west-2/release/2025-11-19.0/theme=places/type=place/*"
        )
    yield


@pytest.fixture
def geo_assistant_with_buffer_fixture():
    """Fixture with a point at (-9.1393, 38.7223) and 0.5km buffer as search_area."""
    place_geojson = Feature(
        type="Feature",
        geometry=Point(type="Point", coordinates=[-9.1393, 38.7223]),
        properties={"name": "Neighbourhood Cafe Lisbon"},
    )
    gdf = gpd.GeoDataFrame([{"geometry": Point(-9.1393, 38.7223)}], crs="EPSG:4326")

    # Convert to Web Mercator for meter-based buffering
    gdf_m = gdf.to_crs(epsg=3857)
    gdf_m["geometry"] = gdf_m["geometry"].buffer(500)  # 0.5km = 500m

    # Convert back to WGS84
    gdf_buffered = gdf_m.to_crs(epsg=4326)

    # Get the buffered geometry as GeoJSON
    search_area_geojson = gdf_buffered.iloc[0].geometry.__geo_interface__

    return GeoAssistantState(
        place=place_geojson, search_area=search_area_geojson, messages=[]
    )


async def test_get_place():
    command = await get_place.ainvoke(
        ToolCall(
            name="get_place",
            type="tool_call",
            id="test_id",
            args={"place_name": "Neighbourhood Cafe Lisbon"},
        )
    )
    assert "place" in command.update


def test_get_places_within_buffer():
    command = get_places_within_buffer.invoke(
        ToolCall(
            name="get_places_within_buffer",
            type="tool_call",
            id="test_id_places_within_buffer",
            args={
                "place": "cafe",
                "state": geo_assistant_with_buffer_fixture,
                "tool_call_id": "test_id_places_within_buffer",
            },
        )
    )

    assert "places_within_buffer" in command.update
