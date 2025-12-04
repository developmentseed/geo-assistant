import pytest
from pathlib import Path
from shapely.geometry import box, mapping
from langchain_core.tools.base import ToolCall

from geo_assistant.tools.naip import fetch_naip_img


@pytest.mark.asyncio
async def test_fetch_naip(tmp_path):
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
    aoi = box(lon - 0.01, lat - 0.01, lon + 0.01, lat + 0.01)
    aoi_geojson = mapping(aoi)

    out_png = tmp_path / "naip_test_img.png"

    tool_call = ToolCall(
        name="fetch_naip_img",
        args={
            "aoi_geojson": aoi_geojson,
            "start_date": "2018-01-01",
            "end_date": "2022-12-31",
            "out_png_path": str(out_png),
            "resolution": 1.0,
        },
        type="tool_call",
        id="test_tool_call_id",
    )

    # Call the actual tool – no STAC / odc-stac mocking
    result = await fetch_naip_img.ainvoke(tool_call["args"])

    # Basic sanity checks on result
    assert result["stac_item_count"] > 0, "Expected at least one NAIP item"
    assert "time" in result["dataset_dims"]
    assert result["dataset_dims"]["time"] >= 1

    # PNG should have been written to disk
    png_path = Path(result["png_path"])
    assert png_path == out_png
    assert png_path.is_file(), f"PNG was not created at {png_path}"
