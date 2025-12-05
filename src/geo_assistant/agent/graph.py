import datetime

from langgraph.checkpoint.memory import InMemorySaver
from langchain.agents import create_agent
from geo_assistant.agent.state import GeoAssistantState
from geo_assistant.agent.llms import llm
from geo_assistant.tools.overture import get_place
from geo_assistant.tools.buffer import get_search_area
from geo_assistant.tools.summarize import summarize_sat_img

SYSTEM_PROMPT = """
You are a helpful assistant that can answer questions and help with tasks.

You have the following tools available to you.

- get_place: Get a place from the Overture Maps database
- get_search_area: Get a search area buffer in km around the place defined in the agent state
- summarize_sat_img: Summarize the contents of a satellite image using an LLM

For places if you have links to social media, include them in the response.

The current date and time is {now}.
"""


async def create_graph():
    checkpointer = InMemorySaver()
    graph = create_agent(
        model=llm,
        tools=[get_place, get_search_area, summarize_sat_img],
        system_prompt=SYSTEM_PROMPT.format(
            now=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ),
        state_schema=GeoAssistantState,
        checkpointer=checkpointer,
    )
    return graph
