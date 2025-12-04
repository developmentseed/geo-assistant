import json
from typing import Annotated

import duckdb
from langchain_core.messages import ToolMessage
from langchain_core.tools import tool
from langchain_core.tools.base import InjectedToolCallId
from langgraph.types import Command


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
    place_name: str, tool_call_id: Annotated[str, InjectedToolCallId] = ""
) -> Command:
    """Get place location from Overture Maps based on user input place name."""

    db_connection = create_database_connection()

    location_results = db_connection.execute(
        f"""
      LOAD spatial;

      SET s3_region='us-west-2';

      SELECT
          id,
          jaro_winkler_similarity(LOWER(names.primary), LOWER('{place_name}')) AS similarity_score,
          names.primary AS name,
          confidence,
          CAST(socials AS JSON) AS socials,
          ST_AsGeoJSON(geometry) AS geometry,
      FROM read_parquet(
          'data/overture/places/*',
          filename=true,
          hive_partitioning=1
      )
      WHERE jaro_winkler_similarity(LOWER(names.primary), LOWER('{place_name}')) > 0.5
      ORDER BY similarity_score DESC
      LIMIT 1;
  """
    ).fetchall()

    db_connection.close()

    geometry = json.loads(location_results[0][-1])

    # Create FeatureCollection
    feature_collection = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": geometry,
                "properties": {
                    "name": location_results[0][2],
                    "overture_id": location_results[0][0],
                },
            }
        ],
    }

    return Command(
        update={
            "place": feature_collection,
            "messages": [
                ToolMessage(
                    content=f"Found place with Overture name: {location_results[0][2]} based on user query",
                    tool_call_id=tool_call_id,
                )
            ],
        },
    )
