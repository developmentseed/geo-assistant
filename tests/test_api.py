from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from geo_assistant.agent.graph import create_graph
from geo_assistant.api.app import app


@pytest_asyncio.fixture
async def initialized_app():
    """Initialize the app's chatbot before testing"""
    # Manually initialize the chatbot as the lifespan would
    app.state.chatbot = await create_graph()
    yield app
    # Cleanup if needed
    if hasattr(app.state, "chatbot"):
        del app.state.chatbot


@pytest.mark.xfail
async def test_call_api(initialized_app):
    async with AsyncClient(
        transport=ASGITransport(app=initialized_app),
        base_url="http://test",
    ) as client:
        thread_id = uuid4()
        response = await client.post(
            "/chat",
            json={
                "agent_state_input": {
                    "messages": [
                        {
                            "content": "Find The Whitney Hotel Boston and buffer 0.1km around it, then fetch the NAIP imagery for the area from 2021 and summarize the contents of the image.",
                            "type": "human",
                        },
                    ],
                    "place": None,
                    "search_area": None,
                },
                "thread_id": str(thread_id),
            },
        )
        print(response)

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/x-ndjson; charset=utf-8"

        # Read the streaming response
        content = response.text
        assert content is not None
        assert len(content) > 0
