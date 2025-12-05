import json
import os
import uuid

import folium
import httpx
import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# API configuration
API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")

st.set_page_config(page_title="Geo Assistant", page_icon="💬")

st.title("Geo Assistant")

# Initialize session state
if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []


def stream_chat(user_message: str):
    """Send a message to the API and stream the response."""
    thread_id = st.session_state.thread_id

    # Prepare request body
    request_body = {
        "thread_id": thread_id,
        "agent_state_input": {
            "messages": [{"type": "human", "content": user_message}],
            "place": None,
            "search_area": None,
        },
    }

    with httpx.stream(
        "POST",
        f"{API_BASE_URL}/chat",
        json=request_body,
        timeout=360.0,
    ) as response:
        response.raise_for_status()

        for line in response.iter_lines():
            if not line:
                continue

            data = json.loads(line)
            state = data.get("state", {})
            messages = state.pop("messages", [])

            for msg in messages:
                msg_type = msg.get("type", "")
                content = msg.get("content", "")
                if not content:
                    continue
                with st.chat_message(msg_type):
                    st.markdown(content)

            # Check for GeoJSON features and render map if present
            geojson_features = {}
            for key, value in state.items():
                if value and isinstance(value, dict) and value.get("type") == "Feature":
                    geojson_features[key] = value
                    # with st.chat_message("tool"):
                    #     st.code(json.dumps(value, indent=2), language="json")
                elif value:
                    with st.chat_message("tool"):
                        st.code(json.dumps(value, indent=2), language="json")

            # Render map if GeoJSON features are present
            if geojson_features:
                # Helper function to extract coordinates from geometry
                def get_coords_from_geometry(geom):
                    """Extract all coordinates from a GeoJSON geometry."""
                    geom_type = geom.get("type", "")
                    coords = geom.get("coordinates", [])

                    if geom_type == "Point":
                        return [coords]
                    elif geom_type == "LineString":
                        return coords
                    elif geom_type == "Polygon":
                        return coords[0] if coords else []
                    elif geom_type == "MultiPoint":
                        return coords
                    elif geom_type == "MultiLineString":
                        return [c for line in coords for c in line]
                    elif geom_type == "MultiPolygon":
                        return [c for poly in coords for c in poly[0]] if coords else []
                    return []

                # Calculate center from all features
                all_lons, all_lats = [], []
                for feature in geojson_features.values():
                    geom = feature.get("geometry", {})
                    coords = get_coords_from_geometry(geom)
                    for coord in coords:
                        if len(coord) >= 2:
                            all_lons.append(coord[0])
                            all_lats.append(coord[1])

                if all_lons and all_lats:
                    center_lat = sum(all_lats) / len(all_lats)
                    center_lon = sum(all_lons) / len(all_lons)
                else:
                    center_lat, center_lon = 0.0, 0.0

                m = folium.Map(location=[center_lat, center_lon], zoom_start=10)

                # Add features to map with different colors
                colors = {"place": "blue", "search_area": "red"}

                def make_style_function(color):
                    """Create a style function with the given color."""
                    return lambda x: {
                        "fillColor": color,
                        "color": color,
                        "weight": 2,
                        "fillOpacity": 0.3,
                    }

                for key, feature in geojson_features.items():
                    color = colors.get(key, "green")
                    folium.GeoJson(
                        feature,
                        style_function=make_style_function(color),
                        tooltip=key,
                    ).add_to(m)

                # Fit map to bounds if we have coordinates
                if all_lons and all_lats:
                    m.fit_bounds(
                        [[min(all_lats), min(all_lons)], [max(all_lats), max(all_lons)]]
                    )

                # Display the map
                with st.chat_message("tool"):
                    st.markdown("**Map View**")
                    map_html = m._repr_html_()
                    components.html(map_html, height=400)


if prompt := st.chat_input("Type your message..."):
    with st.chat_message("user"):
        st.markdown(prompt)
    stream_chat(prompt)
