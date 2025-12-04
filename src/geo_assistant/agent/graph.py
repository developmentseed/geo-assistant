import datetime

from langgraph.checkpoint.memory import InMemorySaver
from langchain.agents import create_agent
from geo_assistant.agent.state import AgentState
from geo_assistant.agent.llms import llm
from geo_assistant.tools.overture import get_overture_locations

SYSTEM_PROMPT = """
You are a helpful assistant that can answer questions and help with tasks.

You have location and division tools available to you. Only use this data if the user asks for it.

The current date and time is {now}.
"""


async def create_graph():
    checkpointer = InMemorySaver()
    graph = create_agent(
        model=llm,
        tools=[get_overture_locations],  # [get_overture_locations, geocode_division],
        system_prompt=SYSTEM_PROMPT.format(
            now=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ),
        state_schema=AgentState,
        checkpointer=checkpointer,
    )
    return graph
