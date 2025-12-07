"""Chat API schemas."""

from pydantic import BaseModel

from geo_assistant.agent.state import GeoAssistantState


class ChatRequestBody(BaseModel):
    """Schema for the request to the Chat API."""

    thread_id: str
    agent_state_input: GeoAssistantState


class ChatResponse(BaseModel):
    """Schema for the response from the Chat API."""

    thread_id: str
    state: GeoAssistantState
