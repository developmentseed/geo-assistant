from pydantic import BaseModel
from geo_assistant.agent.state import GeoAssistantState


class ChatRequestBody(BaseModel):
    agent_state_input: GeoAssistantState
    thread_id: str


class ChatResponse(BaseModel):
    thread_id: str
    state: GeoAssistantState
