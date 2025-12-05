from types import NoneType
import pytest
from shapely.geometry import box, mapping
from langchain_core.tools.base import ToolCall

from geo_assistant.tools.naip import fetch_naip_img


@pytest.mark.asyncio
async def test_fetch_naip():
    """
    Integration test: hit MPC STAC for NAIP around Union Market (DC),
    load imagery via odc-stac, and save an RGB PNG.

    NOTE: This test requires:
      - Internet access (to reach Planetary Computer STAC + blobs)
      - Planetary Computer / NAIP service to be up
    """

    # Union Market coordinates from GeoNames: 38.90789, -76.99831
    #   N 38°54′28″  W 76°59′54″
    # We'll use a small neighborhood AOI around that point.
    # :contentReference[oaicite:0]{index=0}
    lat = 38.90789
    lon = -76.99831

    # ~0.0001 degrees buffer in each direction
    aoi = box(lon - 0.0001, lat - 0.0001, lon + 0.0001, lat + 0.0001)
    aoi_geojson = mapping(aoi)

    tool_call = ToolCall(
        name="fetch_naip_img",
        args={
            "aoi_geojson": aoi_geojson,
            "start_date": "2021-01-01",
            "end_date": "2021-12-31",
        },
        type="tool_call",
        id="test_tool_call_id",
    )

    # Call the actual tool – no STAC / odc-stac mocking
    result = await fetch_naip_img.ainvoke(tool_call)
    assert "naip_img_bytes" in result.update
    assert result.update["naip_img_bytes"] is not None, "Expected PNG bytes in result"
    assert isinstance(result.update["naip_img_bytes"], bytes)
    assert len(result.update["naip_img_bytes"]) > 1, "Expected non-empty PNG bytes"


@pytest.mark.asyncio
async def test_fetch_naip_too_large():
    """
    Integration test: request a larger AOI that should produce an image
    exceeding the 512x512 pixel limit. The tool should return no image
    bytes and include a message indicating it skipped output due to size.

    NOTE: This test requires:
      - Internet access (to reach Planetary Computer STAC + blobs)
      - Planetary Computer / NAIP service to be up
    """

    # Union Market coordinates from GeoNames: 38.90789, -76.99831
    #   N 38°54′28″  W 76°59′54″
    # We'll use a small neighborhood AOI around that point.
    # :contentReference[oaicite:0]{index=0}
    lat = 38.90789
    lon = -76.99831

    # ~0.003 degrees buffer in each direction
    aoi = box(lon - 0.003, lat - 0.003, lon + 0.003, lat + 0.003)
    aoi_geojson = mapping(aoi)

    tool_call = ToolCall(
        name="fetch_naip_img",
        args={
            "aoi_geojson": aoi_geojson,
            "start_date": "2021-01-01",
            "end_date": "2021-12-31",
        },
        type="tool_call",
        id="test_tool_call_id",
    )

    # Call the actual tool – no STAC / odc-stac mocking
    result = await fetch_naip_img.ainvoke(tool_call)
    assert "naip_img_bytes" in result.update
    assert result.update["naip_img_bytes"] is None, "Expected no PNG bytes in result"
    assert isinstance(result.update["naip_img_bytes"], NoneType)