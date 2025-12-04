from langchain_core.tools.base import ToolCall

from geo_assistant.tools.overture import get_place


async def test_get_place():
    command = await get_place.ainvoke(
        ToolCall(
            name="get_place",
            type="tool_call",
            id="test_id",
            args={"place_name": "Neighbourhood Cafe Lisbon"},
        )
    )
    assert "place" in command.update
