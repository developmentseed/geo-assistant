import pytest
from pathlib import Path
from shapely.geometry import box, mapping
from langchain_core.tools.base import ToolCall
import os
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

    # ~0.01 degrees (~1.1 km) buffer in each direction
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
    assert "naip_png_path" in result.update
    assert result.update["naip_png_path"] is not None, "Expected a PNG path in result"
    png_path = Path(result.update["naip_png_path"])

    assert png_path.is_file(), f"PNG was not created at {png_path}"
    os.remove(png_path)  # Clean up after ourselves
