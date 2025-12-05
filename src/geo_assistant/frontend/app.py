import json
import os
import uuid

import httpx
import streamlit as st
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# API configuration
API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")

st.set_page_config(page_title="Geo Assistant", page_icon="💬")

# Initialize session state
if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []


def stream_chat(user_message: str):
    """Send a message to the API and stream the response."""
    thread_id = st.session_state.thread_id

    # Prepare request body
    request_body = {
        "thread_id": thread_id,
        "agent_state_input": {
            "messages": [{"type": "human", "content": user_message}],
            "place": None,
            "search_area": None,
        },
    }

    with httpx.stream(
        "POST",
        f"{API_BASE_URL}/chat",
        json=request_body,
        timeout=360.0,
    ) as response:
        response.raise_for_status()

        for line in response.iter_lines():
            print("=" * 100)
            print(line)
            print("=" * 100)

            if not line:
                continue

            data = json.loads(line)
            print("=" * 100)
            print(data)
            print("=" * 100)
            state = data.get("state", {})
            messages = state.get("messages", [])

            if not messages:
                continue

            for msg in messages:
                msg_type = msg.get("type", "")
                content = msg.get("content", "")

                yield msg_type, content


# Main UI
st.title("Geo Assistant")

# Display chat history
for item in st.session_state.chat_history:
    role = item["role"]
    content = item["content"]

    with st.chat_message(role):
        if role == "assistant":
            # For assistant messages, check if it's a tool message
            if item.get("is_tool"):
                st.code(content, language="json")
            else:
                st.markdown(content)
        else:
            st.markdown(content)

# Chat input
if prompt := st.chat_input("Type your message..."):
    st.session_state.chat_history.append({"role": "user", "content": prompt})

    for msg_type, content in stream_chat(prompt):
        if msg_type == "tool":
            st.session_state.chat_history.append({"role": "tool", "content": content})
        elif msg_type in ["ai", "assistant"]:
            st.session_state.chat_history.append(
                {"role": "assistant", "content": content}
            )

    st.rerun()
