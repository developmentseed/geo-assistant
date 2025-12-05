"""Tool to find closest matching Overture place based on user input."""

import json
import os
from typing import Annotated

import duckdb
from dotenv import load_dotenv
from geojson_pydantic import Feature
from langchain_core.messages import ToolMessage
from langchain_core.tools import tool
from langchain_core.tools.base import InjectedToolCallId
from langgraph.types import Command

# Load environment variables
load_dotenv()


def create_database_connection():
    """
    Create and configure a DuckDB connection with necessary extensions.

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
