# tools/naip_mpc_tools.py
from typing import Dict, Any, Optional, Annotated
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor
import numpy as np
import xarray as xr
import matplotlib.pyplot as plt
from langchain_core.tools import tool
from pystac_client import Client
from odc.stac import stac_load
from langgraph.types import Command
from langchain_core.messages import ToolMessage
from langchain_core.tools.base import InjectedToolCallId

import dotenv

dotenv.load_dotenv()

# PC_STAC_URL = "https://planetarycomputer.microsoft.com/api/stac/v1"
E84_STAC_URL = "https://earth-search.aws.element84.com/v1"


@tool("fetch_naip_img")
async def fetch_naip_img(
    aoi_geojson: Dict[str, Any],
    start_date: str,
    end_date: str,
    tool_call_id: Annotated[Optional[str], InjectedToolCallId] = None,
) -> Command:
    """
    Query Microsoft Planetary Computer for NAIP imagery intersecting an AOI and
    date range, load all matching items into an xarray data cube using odc-stac,
    and save a simple RGB composite as a PNG.

    Args:
        aoi_geojson: GeoJSON Polygon/MultiPolygon in EPSG:4326.
        start_date: Start date (YYYY-MM-DD).
        end_date: End date (YYYY-MM-DD).

    """
    # --- 1. STAC search on Element84's EarthSearch API ---
    catalog = Client.open(E84_STAC_URL)

    search = catalog.search(
        collections=["naip"],
        intersects=aoi_geojson,
        datetime=f"{start_date}/{end_date}",
    )

    items = list(search.items())
    if len(items) == 0:
        return Command(
            update={
                "messages": [
                    ToolMessage(
                        content="No NAIP imagery found for the specified area and date range.",
                        tool_call_id=tool_call_id,
                    )
                ],
                "naip_png_path": None,
            }
        )

    # --- 2. Load as xarray cube with odc.stac ---
    # NAIP in MPC: 4-band multi-band asset (R,G,B,NIR) in one asset named "image".
    # odc.stac exposes these as measurements 'red','green','blue','nir' for this collection

    with ThreadPoolExecutor(max_workers=5) as executor:
        ds: xr.Dataset = stac_load(
            items,
            bands=["Red", "Green", "Blue"],  # use only RGB
            geopolygon=aoi_geojson,
            resolution=1.0,  # NAIP native ~1 m
            executor=executor,
        )
    if ds.dims.get("time", 0) == 0:
        return Command(
            update={
                "messages": [
                    ToolMessage(
                        content="Unable to load NAIP RGB image, dataset has no time dimension",
                        tool_call_id=tool_call_id,
                    )
                ],
                "naip_png_path": None,
            }
        )

    # Enforce max output size based on dataset sizes (y, x)
    sizes = dict(ds.sizes)
    h = int(sizes.get("y", 0))
    w = int(sizes.get("x", 0))
    if h > 512 or w > 512:
        return Command(
            update={
                "messages": [
                    ToolMessage(
                        content=f"NAIP RGB image {w}x{h} exceeds 512x512 limit. Skipping image output.",
                        tool_call_id=tool_call_id,
                    )
                ],
                "naip_img_bytes": None,
            }
        )

    # --- 3. Build an RGB composite from the cube ---
    # For the PNG, we’ll just use the first time slice (you can swap in “latest”
    # or a temporal reduction if you prefer).
    red = ds["Red"].isel(time=0)
    green = ds["Green"].isel(time=0)
    blue = ds["Blue"].isel(time=0)

    # Stack into (y, x, 3) array
    rgb = xr.concat([red, green, blue], dim="band")  # (band, y, x)
    rgb = rgb.transpose("y", "x", "band")  # (y, x, band)

    # Convert to uint8 for PNG with a simple contrast stretch.
    arr = rgb.values.astype("float32")
    # Robust min/max to avoid a few hot pixels blowing out the stretch
    vmin = np.nanpercentile(arr, 2)
    vmax = np.nanpercentile(arr, 98)
    if vmax <= vmin:
        vmin, vmax = np.nanmin(arr), np.nanmax(arr)

    arr = np.clip((arr - vmin) / (vmax - vmin + 1e-6), 0, 1)
    arr_uint8 = (arr * 255).astype("uint8")

    # --- 4. Save PNG ---

    buf = BytesIO()
    plt.imsave(buf, arr_uint8, format="png")
    buf.seek(0)
    img_bytes = buf.getvalue()

    return Command(
        update={
            "messages": [
                ToolMessage(
                    content="NAIP RGB image fetched and encoded as PNG bytes.",
                    tool_call_id=tool_call_id,
                )
            ],
            # This is what your downstream tool should consume
            "naip_img_bytes": img_bytes,
        }
    )
