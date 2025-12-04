import datetime

from langgraph.checkpoint.memory import InMemorySaver
from langchain.agents import create_agent
from geo_assistant.agent.state import GeoAssistantState
from geo_assistant.agent.llms import llm
from geo_assistant.tools.overture import get_overture_locations
from geo_assistant.tools.naip import fetch_naip_img

SYSTEM_PROMPT = """
You are a helpful assistant that can answer questions and help with tasks.

You have access to the following tools:
- Overture location lookup tool: use this to get geographic information about locations in the US based on the user's query
- NAIP imagery fetch tool: use this to fetch NAIP aerial imagery for a given area of interest returned by the overture location lookup tool and date range (do your best to extract the date range from the user's query if provided, otherwise ask the user to specify a date range)

The current date and time is {now}.
"""


async def create_graph():
    checkpointer = InMemorySaver()
    graph = create_agent(
        model=llm,
        tools=[
            get_overture_locations,
            fetch_naip_img,
        ],  # [get_overture_locations, geocode_division],
        system_prompt=SYSTEM_PROMPT.format(
            now=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ),
        state_schema=GeoAssistantState,
        checkpointer=checkpointer,
    )
    return graph
