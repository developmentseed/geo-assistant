from pytest import fixture
from geo_assistant.agent.state import GeoAssistantState
from geo_assistant.tools.buffer import get_search_area
from geojson_pydantic import Feature, Point
from langchain_core.tools.base import ToolCall


@fixture
def geo_assistant_fixture():
    place_geojson = Feature(
        type="Feature",
        geometry=Point(type="Point", coordinates=[-9.1393, 38.7223]),
        properties={"name": "Neighbourhood Cafe Lisbon"},
    )
    return GeoAssistantState(place=place_geojson, search_area=None, messages=[])


async def test_get_search_area(geo_assistant_fixture):
    # Call the underlying function directly to test the logic
    # This bypasses the injection framework which is better suited for integration tests
    command = await get_search_area.ainvoke(
        ToolCall(
            name="get_search_area",
            type="tool_call",
            id="test_id_search_area",
            args={
                "buffer_size_km": 10.0,
                "state": geo_assistant_fixture,
                "tool_call_id": "test_id_search_area",
            },
        ),
    )

    # Verify the state was used correctly
    assert "search_area" in command.update
    assert "messages" in command.update

    # Verify the buffer was created around the correct place
    search_area = command.update["search_area"]
    assert search_area["type"] == "Polygon"

    # Verify the message confirms the buffer was created
    assert len(command.update["messages"]) == 1
    assert "10" in command.update["messages"][0].content
