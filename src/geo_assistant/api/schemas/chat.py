"""Chat API schemas."""

from pydantic import BaseModel

from geo_assistant.agent.state import GeoAssistantState


class ChatRequestBody(BaseModel):
    thread_id: str
    agent_state_input: GeoAssistantState


class ChatResponse(BaseModel):
    thread_id: str
    state: GeoAssistantState
