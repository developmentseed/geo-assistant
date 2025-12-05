# Geo Assistant 

The Geo Assistant agent is a LangGraph-based [ReAct agent](https://arxiv.org/abs/2210.03629) that can answer questions and perform tasks related to locations and geographic data.

## Architecture

The agent follows the ReAct (Reasoning + Acting) pattern, which interleaves reasoning traces and task-specific actions to solve queries. It uses LangGraph to manage state transitions and tool execution.

## Available Tools

The agent has access to the following [tools](tools/index.md):

- **get_place**: Retrieve place information from the Overture Maps database
- **get_search_area**: Create a buffer area (in km) around a place defined in the agent state
- **fetch_naip_img**: Fetch NAIP aerial imagery for a given area and date range
- **summarize_sat_img**: Analyze and summarize satellite image contents using an LLM

## State Management

The agent maintains the following state throughout the conversation:

- **messages**: The conversation history (always updated with each interaction)
- **place**: Current place feature from Overture Maps (updated by `get_place` tool)
- **search_area**: Buffer area around the place (updated by `get_search_area` tool)
- **naip_img_bytes**: NAIP imagery data (updated by `fetch_naip_img` tool)

Tools update the state based on user queries, and these state changes are reflected in the `Streamlit` frontend in real-time.