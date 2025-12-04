from typing import Annotated
import duckdb
import json
from langchain_core.tools import tool
from langgraph.types import Command
from langchain_core.messages import ToolMessage
from langchain_core.tools.base import InjectedToolCallId


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
def get_place(
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
          's3://overturemaps-us-west-2/release/2025-11-19.0/theme=places/type=place/*',
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


# @tool
# def get_overture_locations(
#     area_of_interest: Feature,
#     place_name: Optional[str] = None,
#     place_type: Optional[str] = None,
#     overture_release: str = "2024-11-13.0",
#     similarity_threshold: float = 0.6,
#     tool_call_id: Annotated[str, InjectedToolCallId] = "",
# ) -> Command:
#     """
#     Get locations from Overture Maps.

#     Parameters
#     ----------
#     area_of_interest : Feature
#         Area of interest to search for locations in
#     place_name : str, optional
#         Name of the place to search for
#     place_type : str, optional
#         Type of the place to search for
#     overture_release : str
#         Overture Maps release version
#     similarity_threshold : float
#         Minimum similarity score (0-1) for fuzzy name matching
#     tool_call_id : str
#         Tool call ID

#     Returns
#     -------
#     Command
#         Command that updates state with location features
#     """

#     con = duckdb.connect()

#     con.execute("INSTALL spatial;")
#     con.execute("LOAD spatial;")

#     con.execute("INSTALL httpfs;")
#     con.execute("LOAD httpfs;")

#     con.execute(
#         """
#         CREATE OR REPLACE TABLE aoi AS
#         SELECT ST_GeomFromGeoJSON(?) AS geom
#     """,
#         [area_of_interest.geometry.model_dump_json()],
#     )

#     base_url = f"s3://overturemaps-us-west-2/release/{overture_release}/theme=places/type=place/*"

#     where_conditions = ["ST_Within(ST_GeomFromWKB(geometry), (SELECT geom FROM aoi))"]

#     if place_type:
#         where_conditions.append(f"categories.primary = '{place_type}'")

#     if place_name:
#         where_conditions.append(
#             f"jaro_winkler_similarity(LOWER(names.primary), LOWER('{place_name}')) >= {similarity_threshold}"
#         )

#     where_clause = " AND ".join(where_conditions)

#     query = f"""
#         SELECT
#             id,
#             ST_AsText(ST_GeomFromWKB(geometry)) as geometry_wkt,
#             names.primary as name,
#             categories.primary as primary_category,
#             confidence,
#             websites,
#             phones,
#             addresses
#         FROM read_parquet('{base_url}', filename=true, hive_partitioning=1)
#         WHERE {where_clause}
#     """

#     result = con.execute(query).fetchall()
#     columns = [desc[0] for desc in con.description]

#     locations = [dict(zip(columns, row)) for row in result]

#     # Convert locations to GeoJSON Features
#     features = []
#     for loc in locations:
#         # Parse WKT geometry to GeoJSON
#         geom_wkt = loc.get("geometry_wkt")
#         if geom_wkt:
#             shapely_geom = wkt.loads(geom_wkt)
#             geom_dict = mapping(shapely_geom)

#             # Create properties from location data
#             properties = {
#                 "id": loc.get("id"),
#                 "name": loc.get("name"),
#                 "primary_category": loc.get("primary_category"),
#                 "confidence": loc.get("confidence"),
#                 "websites": loc.get("websites"),
#                 "phones": loc.get("phones"),
#                 "addresses": loc.get("addresses"),
#             }

#             feature = Feature(geometry=geom_dict, properties=properties)
#             features.append(feature)

#     con.close()

#     tool_message = f"Found {len(features)} locations matching the criteria"

#     return Command(
#         update={
#             "features": features,
#             "messages": [ToolMessage(content=tool_message, tool_call_id=tool_call_id)],
#         },
#     )


# @tool
# def geocode_division(
#     query: str,
#     level: Optional[str] = None,
#     overture_release: str = "2024-11-13.0",
#     similarity_threshold: float = 0.6,
#     limit: int = 10,
#     tool_call_id: Annotated[str, InjectedToolCallId] = "",
# ) -> Command:
#     """
#     Geocode a place name using Overture divisions data.

#     Parameters
#     ----------
#     query : str
#         Place name to search for (e.g., "San Francisco", "California", "United States")
#     level : str, optional
#         Division level to filter by. Options:
#         - 'country'
#         - 'region' (states, provinces)
#         - 'county' (counties, districts)
#         - 'locality' (cities, towns)
#         - 'localadmin' (local administrative areas)
#         - 'neighborhood'
#     overture_release : str
#         Overture Maps release version
#     similarity_threshold : float
#         Minimum similarity score (0-1) for fuzzy name matching
#     limit : int
#         Maximum number of results to return

#     Returns
#     -------
#     Command
#         Command that updates state with division features
#     """

#     con = duckdb.connect()

#     con.execute("INSTALL spatial;")
#     con.execute("LOAD spatial;")

#     con.execute("INSTALL httpfs;")
#     con.execute("LOAD httpfs;")

#     base_url = f"s3://overturemaps-us-west-2/release/{overture_release}/theme=divisions/type=division/*"

#     where_conditions = [
#         f"jaro_winkler_similarity(LOWER(names.primary), LOWER('{query}')) >= {similarity_threshold}"
#     ]

#     if level:
#         where_conditions.append(f"subtype = '{level}'")

#     where_clause = " AND ".join(where_conditions)

#     query_sql = f"""
#         SELECT
#             id,
#             ST_AsText(ST_GeomFromWKB(geometry)) as geometry_wkt,
#             names.primary as name,
#             names.common as common_names,
#             subtype as division_level,
#             country,
#             region,
#             hierarchies,
#             population,
#             capital,
#             wikidata,
#             sources,
#             jaro_winkler_similarity(LOWER(names.primary), LOWER('{query}')) as similarity_score
#         FROM read_parquet('{base_url}', filename=true, hive_partitioning=1)
#         WHERE {where_clause}
#         ORDER BY similarity_score DESC
#         LIMIT {limit}
#     """

#     result = con.execute(query_sql).fetchall()
#     columns = [desc[0] for desc in con.description]

#     divisions = [dict(zip(columns, row)) for row in result]

#     # Convert divisions to GeoJSON Features
#     features = []
#     for div in divisions:
#         # Parse WKT geometry to GeoJSON
#         geom_wkt = div.get("geometry_wkt")
#         if geom_wkt:
#             shapely_geom = wkt.loads(geom_wkt)
#             geom_dict = mapping(shapely_geom)

#             # Create properties from division data
#             properties = {
#                 "id": div.get("id"),
#                 "name": div.get("name"),
#                 "common_names": div.get("common_names"),
#                 "division_level": div.get("division_level"),
#                 "country": div.get("country"),
#                 "region": div.get("region"),
#                 "hierarchies": div.get("hierarchies"),
#                 "population": div.get("population"),
#                 "capital": div.get("capital"),
#                 "wikidata": div.get("wikidata"),
#                 "sources": div.get("sources"),
#                 "similarity_score": div.get("similarity_score"),
#             }

#             feature = Feature(geometry=geom_dict, properties=properties)
#             features.append(feature)

#     con.close()

#     tool_message = f"Found {len(features)} divisions matching '{query}'"

#     return Command(
#         update={
#             "features": features,
#             "messages": [ToolMessage(content=tool_message, tool_call_id=tool_call_id)],
#         },
#     )
