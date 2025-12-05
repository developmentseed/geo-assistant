"""Tests for the satellite image summarization tool."""

import uuid

import pytest
from langchain_core.tools.base import ToolCall

from geo_assistant.tools.summarize import summarize_sat_img

# Sample test data
TEST_IMAGE_URL = "https://petapixel.com/assets/uploads/2022/08/French-Officials-Use-Satellite-Photos-and-AI-to-Spot-Unregistered-Pools-1536x806.jpg"


@pytest.mark.parametrize(
    "img_url,summary",
    [
        (TEST_IMAGE_URL, "building"),
    ],
)
@pytest.mark.xfail
def test_summarize_sat_img(img_url, summary):
    command = summarize_sat_img.invoke(
        ToolCall(
            name="summarize_sat_img",
            type="tool_call",
            args={"img_url": img_url},
            id=str(uuid.uuid4()),
        ),
    )

    print(command.update.get("messages"))
    assert summary in command.update.get("messages")[-1].content
