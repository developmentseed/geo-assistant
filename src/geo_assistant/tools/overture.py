import json
import os
from typing import Annotated

import duckdb
import geopandas as gpd
from dotenv import load_dotenv
from geojson_pydantic import Feature
from langchain_core.messages import ToolMessage
from langchain_core.tools import tool
from langchain_core.tools.base import InjectedToolCallId
from langgraph.prebuilt import InjectedState
from langgraph.types import Command
from shapely.geometry import shape

from geo_assistant.agent.state import GeoAssistantState

# Load environment variables
load_dotenv()


def create_database_connection():
    """Create and configure a DuckDB connection with necessary extensions.

    Args:
        database_path: Path to the DuckDB database file

    Returns:
        Configured DuckDB connection

    """
    connection = duckdb.connect()
    connection.execute("INSTALL spatial;")
    connection.execute("INSTALL httpfs;")
    connection.load_extension("spatial")
    connection.load_extension("httpfs")
    return connection


@tool
async def get_place(
    place_name: str,
    tool_call_id: Annotated[str, InjectedToolCallId] = "",
) -> Command:
    """Get place location from Overture Maps based on user input place name."""

    db_connection = create_database_connection()
    source = os.getenv("OVERTURE_SOURCE", "local")
    if source == "s3":
        data_path = os.getenv("OVERTURE_S3_PATH")
        db_connection.execute("SET s3_region='us-west-2';")
    else:
        data_path = os.getenv("OVERTURE_LOCAL_PATH")

    location_results = db_connection.execute(
        f"""
      LOAD spatial;

      SELECT
          id,
          jaro_winkler_similarity(LOWER(names.primary), LOWER('{place_name}')) AS similarity_score,
          names.primary AS name,
          confidence,
          CAST(socials AS JSON) AS socials,
          ST_AsGeoJSON(geometry) AS geometry,
      FROM read_parquet(
          '{data_path}',
          filename=true,
          hive_partitioning=1
      )
      WHERE jaro_winkler_similarity(LOWER(names.primary), LOWER('{place_name}')) > 0.5
      ORDER BY similarity_score DESC
      LIMIT 1;
  """,
    ).fetchall()

    db_connection.close()

    geometry = json.loads(location_results[0][-1])

    feature = Feature(
        type="Feature",
        geometry=geometry,
        properties={
            "overture_id": location_results[0][0],
            "name": location_results[0][2],
            "socials": location_results[0][4],
        },
    )

    return Command(
        update={
            "place": feature,
            "messages": [
                ToolMessage(
                    content=f"Found place with Overture name: {location_results[0][2]} based on user query. Socials: {location_results[0][4]}",
                    tool_call_id=tool_call_id,
                ),
            ],
        },
    )


def normalize_place_type(place: str) -> str:
    """Normalize place type input to Overture categories."""
    place_lower = place.lower().strip()

    # Mapping of variations to canonical Overture types
    mappings = {
        # Restaurants
        "restaurant": "restaurant",
        "restaurants": "restaurant",
        # Cafes/Coffee shops
        "cafe": "cafe",
        "cafes": "cafe",
        "coffee": "cafe",
        "coffee shop": "cafe",
        "coffee shops": "cafe",
        "coffeeshop": "cafe",
        # Bars
        "bar": "bar",
        "bars": "bar",
        "pub": "bar",
        "pubs": "bar",
    }

    return mappings.get(place_lower, place_lower)


@tool
async def get_places_within_buffer(
    place: str,
    state: Annotated[GeoAssistantState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> Command:
    """Get places from Overture Maps within user specified area and user specified Overture place type.

    Accepts: restaurant(s), cafe(s), coffee shop(s), bar(s), pub(s) - case insensitive."""

    # Normalize the place type
    place = normalize_place_type(place)

    # get bounds of buffered place
    search_area = state["search_area"]

    db_connection = create_database_connection()
    source = os.getenv("OVERTURE_SOURCE", "local")
    if source == "s3":
        data_path = os.getenv("OVERTURE_S3_PATH")
        db_connection.execute("SET s3_region='us-west-2';")
    else:
        data_path = os.getenv("OVERTURE_LOCAL_PATH")

    places_df = db_connection.execute(
        f"""
        LOAD spatial;
        SELECT
            id,
            names.primary AS name,
            ST_AsGeoJSON(geometry) AS geometry,
            websites,
            socials,
            categories
        FROM read_parquet(
            '{data_path}',
            filename=true,
            hive_partitioning=1
        )
        WHERE ST_Intersects(geometry, ST_GeomFromGeoJSON('{json.dumps(search_area.geometry.model_dump())}'))
        AND categories.primary = '{place}'
        LIMIT 10;
        """,
    ).fetchdf()

    db_connection.close()

    # Convert geometry column from GeoJSON strings to shapely geometries
    places_df["geometry"] = places_df["geometry"].apply(lambda x: shape(json.loads(x)))

    # Create GeoDataFrame
    gdf = gpd.GeoDataFrame(places_df, geometry="geometry", crs="EPSG:4326")

    # Convert to GeoJSON FeatureCollection and ensure no numpy arrays
    feature_collection = json.loads(json.dumps(gdf.__geo_interface__, default=str))

    return Command(
        update={
            "places_within_buffer": feature_collection,
            "messages": [
                ToolMessage(
                    content="Found places based on user query",
                    tool_call_id=tool_call_id,
                ),
            ],
        },
    )
