# tools/naip_mpc_tools.py
from typing import Dict, Any
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import xarray as xr
import matplotlib.pyplot as plt
from langchain_core.tools import tool
from pystac_client import Client
from odc.stac import stac_load

# PC_STAC_URL = "https://planetarycomputer.microsoft.com/api/stac/v1"
E84_STAC_URL = "https://earth-search.aws.element84.com/v1"


@tool("fetch_naip_img")
async def fetch_naip_img(
    aoi_geojson: Dict[str, Any],
    start_date: str,
    end_date: str,
    out_png_path: str = "naip_rgb.png",
    resolution: float = 1.0,
) -> Dict[str, Any]:
    """
    Query Microsoft Planetary Computer for NAIP imagery intersecting an AOI and
    date range, load all matching items into an xarray data cube using odc-stac,
    and save a simple RGB composite as a PNG.

    Args:
        aoi_geojson: GeoJSON Polygon/MultiPolygon in EPSG:4326.
        start_date: Start date (YYYY-MM-DD).
        end_date: End date (YYYY-MM-DD).
        out_png_path: Where to save the PNG relative to the current working dir.
        resolution: Output pixel size in meters (default ~1 m).

    Returns:
        Dict with:
            - stac_item_count: number of NAIP STAC items loaded
            - dataset_dims: dict of cube dimensions
            - png_path: filesystem path to the saved PNG (or None if no data)
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
        return {
            "stac_item_count": 0,
            "dataset_dims": {},
            "png_path": None,
            "note": "No NAIP items found for the given AOI and date range.",
        }

    # --- 2. Load as xarray cube with odc.stac ---
    # NAIP in MPC: 4-band multi-band asset (R,G,B,NIR) in one asset named "image".
    # odc.stac exposes these as measurements 'red','green','blue','nir' for this collection
    with ThreadPoolExecutor(max_workers=20) as executor:
        ds: xr.Dataset = stac_load(
            items,
            bands=["red", "green", "blue"],  # use only RGB
            chunks={"x": 2048, "y": 2048},  # eager load (no dask) for small AOIs
            pool=executor,
        )
    if ds.dims.get("time", 0) == 0:
        return {
            "stac_item_count": len(items),
            "dataset_dims": dict(ds.sizes),
            "png_path": None,
            "note": "Loaded dataset has no time dimension / pixels.",
        }

    # --- 3. Build an RGB composite from the cube ---
    # For the PNG, we’ll just use the first time slice (you can swap in “latest”
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
    out_path = Path(out_png_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    plt.imsave(out_path.as_posix(), arr_uint8)

    return {
        "stac_item_count": len(items),
        "dataset_dims": dict(ds.sizes),
        "png_path": out_path.as_posix(),
    }
