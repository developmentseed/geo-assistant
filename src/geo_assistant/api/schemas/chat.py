from pydantic import BaseModel
from geo_assistant.agent.state import AgentState


class ChatRequestBody(BaseModel):
    agent_state_input: AgentState
    thread_id: str


class ChatResponse(BaseModel):
    thread_id: str
    state: AgentState
