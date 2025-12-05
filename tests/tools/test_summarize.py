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


@pytest.mark.xfail
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "img_url,summary",
    [
        (TEST_IMAGE_URL, "building"),
    ],
)
async def test_summarize_sat_img(img_url, summary):
    # Load the image from the supplied URL and encode it in base64
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    }
    resp = requests.get(img_url, headers=headers)
    resp.raise_for_status()
    img_base64 = base64.b64encode(resp.content).decode("utf-8")
    command = await summarize_sat_img.ainvoke(
        ToolCall(
            name="summarize_sat_img",
            type="tool_call",
            args={
                "state": GeoAssistantState(naip_img_bytes=img_base64, messages=[]),
                "tool_call_id": str(uuid.uuid4()),
            },
            id=str(uuid.uuid4()),
        ),
    )

    print(command.update.get("messages"))
    assert summary in command.update.get("messages")[-1].content
