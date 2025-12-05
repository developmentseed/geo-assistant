# tools/naip_mpc_tools.py
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from typing import Annotated

import dotenv
import matplotlib.pyplot as plt
import numpy as np
import xarray as xr
from langchain_core.messages import ToolMessage
from langchain_core.tools import tool
from langchain_core.tools.base import InjectedToolCallId
from langgraph.prebuilt import InjectedState
from langgraph.types import Command
from odc.stac import stac_load
from pystac.extensions.raster import RasterBand
from pystac_client import Client

from geo_assistant.agent.state import GeoAssistantState

dotenv.load_dotenv()

DATA_URL = "https://planetarycomputer.microsoft.com/api/stac/v1"


@tool("fetch_naip_img")
async def fetch_naip_img(
    start_date: str,
    end_date: str,
    state: Annotated[GeoAssistantState, InjectedState],
    tool_call_id: Annotated[str | None, InjectedToolCallId] = None,
) -> Command:
    """
    Query Microsoft Planetary Computer for NAIP imagery intersecting an AOI and
    date range, load all matching items into an xarray data cube using odc-stac,
    and save a simple RGB composite as a PNG.

    Args:
        start_date: Start date (YYYY-MM-DD).
        end_date: End date (YYYY-MM-DD).

    """
    # --- 1. STAC search on Element84's EarthSearch API ---
    catalog = Client.open(DATA_URL)

    search = catalog.search(
        collections=["naip"],
        intersects=state["search_area"].geometry,
        datetime=f"{start_date}/{end_date}",
    )

    items = list(search.items())

    # This is a hack to add raster extension info to the items, since
    # the Planetary Computer STAC API adds the band information using the
    # eo:bands extension, but odc.stac expects the raster:bands extension.
    for item in items:
        item.assets["image"].ext.add("raster")
        item.assets["image"].ext.raster.bands = [
            RasterBand.create() for _ in ("red", "green", "blue", "nir")
        ]

    if len(items) == 0:
        return Command(
            update={
                "messages": [
                    ToolMessage(
                        content="No NAIP imagery found for the specified area and date range.",
                        tool_call_id=tool_call_id,
                    ),
                ],
                "naip_png_path": None,
            },
        )

    # --- 2. Load as xarray cube with odc.stac ---
    # NAIP in MPC: 4-band multi-band asset (R,G,B,NIR) in one asset named "image".
    # odc.stac exposes these as measurements 'red','green','blue','nir' for this collection
    # Limit to first item for now
    with ThreadPoolExecutor(max_workers=5) as executor:
        ds: xr.Dataset = stac_load(
            items[:1],
            bands=["red", "green", "blue"],  # use only RGB
            geopolygon=state["search_area"].geometry,
            resolution=1.0,  # NAIP native ~1 m
            executor=executor,
            crs=items[0].properties["proj:code"],
        )

    if ds.dims.get("time", 0) == 0:
        return Command(
            update={
                "messages": [
                    ToolMessage(
                        content="Unable to load NAIP RGB image, dataset has no time dimension",
                        tool_call_id=tool_call_id,
                    ),
                ],
                "naip_img_bytes": None,
            },
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
                    ),
                ],
                "naip_img_bytes": None,
            },
        )

    # --- 3. Build an RGB composite from the cube ---
    # For the PNG, we'll just use the first time slice (you can swap in “latest”
    # or a temporal reduction if you prefer).
    red = ds["red"].isel(time=0)
    green = ds["green"].isel(time=0)
    blue = ds["blue"].isel(time=0)

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
                ),
            ],
            "naip_img_bytes": img_bytes,
        },
    )
