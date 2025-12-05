"""Tests for the satellite image summarization tool."""

import base64
import uuid

import pytest
import requests
from langchain_core.tools.base import ToolCall

from geo_assistant.agent.state import GeoAssistantState
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
    # Load the image from the supplied URL and encode it in base64
    resp = requests.get(img_url)
    resp.raise_for_status()
    img_base64 = base64.b64encode(resp.content).decode("utf-8")
    command = summarize_sat_img.invoke(
        ToolCall(
            name="summarize_sat_img",
            type="tool_call",
            args={
                "state": GeoAssistantState(naip_img_bytes=img_base64),
                "tool_call_id": str(uuid.uuid4()),
            },
            id=str(uuid.uuid4()),
        ),
    )

    print(command.update.get("messages"))
    assert summary in command.update.get("messages")[-1].content
