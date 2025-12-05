import os
import pytest
from langchain_core.tools.base import ToolCall

from geo_assistant.tools.overture import get_place


@pytest.fixture(autouse=True)
def setup_ci_env():
    """Configure S3 source for CI environments."""
    # Detect CI environment (GitHub Actions, GitLab CI, etc.)
    if os.getenv("CI") or os.getenv("GITHUB_ACTIONS"):
        os.environ["OVERTURE_SOURCE"] = "s3"
        os.environ["OVERTURE_S3_PATH"] = (
            "s3://overturemaps-us-west-2/release/2025-11-19.0/theme=places/type=place/*"
        )
    yield


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
