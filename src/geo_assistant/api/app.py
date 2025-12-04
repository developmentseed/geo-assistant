import json
from contextlib import aclosing, asynccontextmanager
from typing import Any, AsyncGenerator, Dict

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import logging
from pydantic import UUID4

from geo_assistant.agent.graph import create_graph
from geo_assistant.agent.state import GeoAssistantState
from geo_assistant.api.schemas.chat import ChatRequestBody, ChatResponse

logger = logging.getLogger(__name__)

# Whitelist state fields that can be set by the user.
# Note that these attrs need to be pydantic Fields and
# need a description in the GeoAssistantState model.
UI_SET_FIELDS_WHITELIST = ["point", "messages"]


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.chatbot = await create_graph()
    yield


app = FastAPI(title="Geo Assistant", lifespan=lifespan)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all HTTP methods (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"],  # Allows all headers
)


async def stream_chat(
    ui_state_update: GeoAssistantState,
    thread_id: UUID4,
    chatbot: Any,
    request: Request,
) -> AsyncGenerator[bytes, None]:
    config: Dict[str, Any] = {
        "configurable": {
            "thread_id": str(thread_id),
        }
    }

    state_updates = {}

    vars_to_update = {
        key: val
        for key, val in ui_state_update.items()
        if val and key in UI_SET_FIELDS_WHITELIST
    }
    logger.debug(f"State variables to update: {vars_to_update}")

    ui_messages = []
    for key in vars_to_update.keys():
        if hasattr(GeoAssistantState, key):
            field_info = getattr(GeoAssistantState, key)
            description = field_info.description if field_info else f"Field {key}"
            if description:
                ui_messages.append(
                    {
                        "content": f"Manually selected data for field {key}: {description}",
                        "type": "human",
                    }
                )

    # Add UI messages to the existing messages if they exist
    existing_messages = vars_to_update.get("messages", [])
    vars_to_update["messages"] = ui_messages + existing_messages

    state_updates.update(vars_to_update)

    stream = chatbot.astream(
        input=state_updates,
        config=config,
        stream_mode="updates",
    )

    try:
        async with aclosing(stream):
            async for update in stream:
                if await request.is_disconnected():
                    logger.info("Client disconnected; stopping stream.")
                    break

                agent = next(iter(update.keys()))
                payload = update[agent]
                if "feature_collection" not in payload:  # TODO
                    payload["feature_collection"] = None
                state_payload = GeoAssistantState(**payload)

                resp = ChatResponse(thread_id=str(thread_id), state=state_payload)

                line = json.dumps(resp.model_dump()) + "\n"
                yield line.encode("utf-8")

    except Exception as e:
        logger.warning("stream_chat error: %r", e)


@app.post("/chat")
async def chat(request: ChatRequestBody, http_request: Request) -> StreamingResponse:
    generator = stream_chat(
        ui_state_update=request.agent_state_input,
        thread_id=request.thread_id,
        chatbot=http_request.app.state.chatbot,
        request=http_request,
    )
    return StreamingResponse(
        generator,
        media_type="application/x-ndjson; charset=utf-8",
        headers={
            "Cache-Control": "no-cache",
            # If you run behind nginx, this prevents buffering of the stream:
            "X-Accel-Buffering": "no",
        },
    )
