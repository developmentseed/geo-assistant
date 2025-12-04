import datetime

from langgraph.checkpoint.memory import InMemorySaver
from langchain.agents import create_agent
from geo_assistant.agent.state import GeoAssistantState
from geo_assistant.agent.llms import llm
from geo_assistant.tools.overture import get_place
from geo_assistant.tools.buffer import get_search_area

SYSTEM_PROMPT = """
You are a helpful assistant that can answer questions and help with tasks.

You have location and division tools available to you. Only use this data if the user asks for it.

The current date and time is {now}.
"""


async def create_graph():
    checkpointer = InMemorySaver()
    graph = create_agent(
        model=llm,
        tools=[get_place, get_search_area],
        system_prompt=SYSTEM_PROMPT.format(
            now=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ),
        state_schema=GeoAssistantState,
        checkpointer=checkpointer,
    )
    return graph
