from langchain_core.tools.base import ToolCall
from geo_assistant.tools.overture import get_place


def test_get_place():
    command = get_place.invoke(
        ToolCall(
            name="get_place",
            type="tool_call",
            id="test_id",
            args={"place_name": "Neighboourhood Cafe Lisbon"},
        )
    )
    assert "place" in command.update
