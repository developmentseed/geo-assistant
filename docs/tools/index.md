# Tools

List of tools available to the agent. Each tool can be used independently or as part of the agent workflow.

## Overview

The geo-assistant provides four main tools for geospatial operations:

- **`get_place`**: Search for locations using Overture Maps data
- **`get_search_area`**: Create buffer zones around locations
- **`fetch_naip_img`**: Retrieve and process NAIP satellite imagery
- **`summarize_sat_img`**: Generate AI-powered descriptions of satellite images

---

## `get_place`

Search for a place location from Overture Maps based on a place name.

**Location**: `src/geo_assistant/tools/overture.py`

### Inputs

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `place_name` | `str` | Yes | Name of the place to search for |
| `tool_call_id` | `str` | No | Injected tool call ID for tracking (auto-injected by LangGraph) |

### Outputs

Returns a `Command` object that updates the agent state with:

- **`place`**: A GeoJSON `Feature` object containing:
  - `geometry`: Point geometry of the location (EPSG:4326)
  - `properties`:
    - `overture_id`: Overture Maps identifier
    - `name`: Primary name of the place
    - `socials`: Social media links (if available)
- **`messages`**: Tool message with place information

### Independent Usage

```python
from geo_assistant.tools.overture import get_place

# Call the tool directly
result = await get_place(place_name="Central Park")

# Access the place feature from the command update
place_feature = result.update["place"]
print(f"Found: {place_feature.properties['name']}")
print(f"Geometry: {place_feature.geometry}")
```

### Configuration

Requires environment variables:

- `OVERTURE_SOURCE`: Either `"local"` or `"s3"` (default: `"local"`)
- `OVERTURE_LOCAL_PATH`: Path to local Overture parquet files (if using local source)
- `OVERTURE_S3_PATH`: S3 path to Overture data (if using S3 source)

---

## `get_search_area`

Create a buffer zone around a place defined in the agent state.

**Location**: `src/geo_assistant/tools/buffer.py`

### Inputs

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `buffer_size_km` | `float` | Yes | Buffer radius in kilometers |
| `state` | `GeoAssistantState` | Yes | Agent state containing the place (auto-injected by LangGraph) |
| `tool_call_id` | `str` | No | Injected tool call ID for tracking (auto-injected by LangGraph) |

### Outputs

Returns a `Command` object that updates the agent state with:

- **`search_area`**: A GeoJSON `Feature` object with buffered polygon geometry (EPSG:4326)
- **`messages`**: Tool message confirming buffer creation

### Independent Usage

```python
from geo_assistant.tools.buffer import get_search_area
from geo_assistant.agent.state import GeoAssistantState
from geojson_pydantic import Feature

# Create a state with a place
state = GeoAssistantState(
    place=Feature(
        type="Feature",
        geometry={"type": "Point", "coordinates": [-73.9654, 40.7829]},
        properties={"name": "Central Park"}
    )
)

# Call the tool with state injection
result = await get_search_area(
    buffer_size_km=2.5,
    state=state
)

# Access the search area from the command update
search_area = result.update["search_area"]
print(f"Buffer geometry: {search_area.geometry}")
```

**Note**: This tool requires a `place` to be set in the agent state. When used independently, you must provide a properly configured state object.

---

## `fetch_naip_img`

Query and download NAIP (National Agriculture Imagery Program) satellite imagery for a given area and date range.

**Location**: `src/geo_assistant/tools/naip.py`

### Inputs

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `aoi_geojson` | `dict[str, Any]` | Yes | GeoJSON Polygon/MultiPolygon in EPSG:4326 defining the area of interest |
| `start_date` | `str` | Yes | Start date in `YYYY-MM-DD` format |
| `end_date` | `str` | Yes | End date in `YYYY-MM-DD` format |
| `tool_call_id` | `str` | No | Injected tool call ID for tracking (auto-injected by LangGraph) |

### Outputs

Returns a `Command` object that updates the agent state with:

- **`naip_png_path`**: Path to the saved RGB composite PNG image (or `None` if no imagery found)
- **`messages`**: Tool message with status and file path

### Independent Usage

```python
from geo_assistant.tools.naip import fetch_naip_img

# Define an area of interest
aoi = {
    "type": "Polygon",
    "coordinates": [[
        [-73.9654, 40.7829],
        [-73.9654, 40.7929],
        [-73.9554, 40.7929],
        [-73.9554, 40.7829],
        [-73.9654, 40.7829]
    ]]
}

# Fetch NAIP imagery
result = await fetch_naip_img(
    aoi_geojson=aoi,
    start_date="2022-01-01",
    end_date="2022-12-31"
)

# Access the image path
image_path = result.update["naip_png_path"]
if image_path:
    print(f"Image saved to: {image_path}")
```

### Details

- Uses Element84's Earth Search STAC API
- Loads RGB bands (Red, Green, Blue) at 1m resolution
- Applies 2-98 percentile contrast stretch
- Saves output as `naip_rgb.png` in the current directory
- Uses multi-threaded loading for performance

---

## `summarize_sat_img`

Generate an AI-powered natural language description of a satellite image.

**Location**: `src/geo_assistant/tools/summarize.py`

### Inputs

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `img_url` | `str` | Yes | URL or file path to the satellite image |
| `tool_call_id` | `str` | No | Injected tool call ID for tracking (auto-injected by LangGraph) |

### Outputs

Returns a `Command` object that updates the agent state with:

- **`messages`**: Tool message containing:
  - `content`: Natural language description of the image
  - `artifact`: Dictionary with `img_url` key

### Independent Usage

```python
from geo_assistant.tools.summarize import summarize_sat_img

# Summarize a satellite image
result = await summarize_sat_img(
    img_url="naip_rgb.png"
)

# Access the summary
message = result.update["messages"][0]
print(f"Image description: {message.content}")
print(f"Image URL: {message.artifact['img_url']}")
```

### Configuration

Requires environment variables:

- `OLLAMA_IMAGE_MODEL`: Model name for image analysis (default: `"ministral-3:14b-cloud"`)
- `OLLAMA_BASE_URL`: Ollama API endpoint (default: `"http://localhost:11434"`)

### Details

- Uses DSPy with Ollama for vision-language model inference
- Singleton pattern ensures model is loaded only once
- Supports both local file paths and remote URLs
- Configurable temperature and max tokens

---

## Using Tools in Agent Workflows

All tools are designed to work seamlessly with LangGraph agents. They use the `@tool` decorator and return `Command` objects that update the agent state.

### Example Agent Integration

```python
from langgraph.prebuilt import create_react_agent
from geo_assistant.tools.overture import get_place
from geo_assistant.tools.buffer import get_search_area
from geo_assistant.tools.naip import fetch_naip_img
from geo_assistant.tools.summarize import summarize_sat_img

# Create an agent with all tools
agent = create_react_agent(
    model=llm,
    tools=[get_place, get_search_area, fetch_naip_img, summarize_sat_img],
    state_schema=GeoAssistantState
)

# Run the agent
result = await agent.ainvoke({
    "messages": [("user", "Show me satellite imagery of Central Park")]
})
```

---

## Tool Dependencies

### Python Packages

- **Overture tool**: `duckdb`, `geojson-pydantic`
- **Buffer tool**: `geopandas`
- **NAIP tool**: `pystac-client`, `odc-stac`, `xarray`, `matplotlib`, `numpy`
- **Summarize tool**: `dspy-ai`

### External Services

- **NAIP imagery**: Element84 Earth Search STAC API (no authentication required)
- **Image summarization**: Ollama instance with vision-capable model
- **Overture data**: Local parquet files or S3 access