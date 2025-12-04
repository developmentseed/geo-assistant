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


def send_message(user_message: str, message_container):
    """Send a message to the API and stream the response."""
    thread_id = st.session_state.thread_id

    # Prepare request body
    request_body = {
        "thread_id": thread_id,
        "agent_state": {
            "messages": [{"type": "human", "content": user_message}],
            "features": [],
        },
    }

    # Create a placeholder for streaming response
    response_placeholder = message_container.empty()
    last_messages = []

    try:
        with httpx.stream(
            "POST",
            f"{API_BASE_URL}/chat",
            json=request_body,
            timeout=60.0,
        ) as response:
            response.raise_for_status()

            for line in response.iter_lines():
                if line:
                    try:
                        data = json.loads(line)
                        state = data.get("state", {})
                        messages = state.get("messages", [])

                        # Display the latest messages
                        if messages:
                            display_parts = []
                            for msg in messages:
                                msg_type = msg.get("type", "")
                                content = msg.get("content", "")

                                if msg_type == "tool":
                                    # Display tool messages as JSON code blocks
                                    if isinstance(content, (dict, list)):
                                        content_str = json.dumps(content, indent=2)
                                    else:
                                        content_str = str(content)
                                    display_parts.append(
                                        f"**Tool:**\n```json\n{content_str}\n```"
                                    )
                                elif msg_type in ["ai", "assistant"]:
                                    # Display AI messages as normal text
                                    display_parts.append(f"**AI:** {content}")

                            if display_parts:
                                full_response = "\n\n".join(display_parts)
                                response_placeholder.markdown(full_response)
                                last_messages = messages
                    except json.JSONDecodeError:
                        continue

            # Return the final messages for history
            return last_messages

    except httpx.HTTPError as e:
        message_container.error(f"Error connecting to API: {e}")
        return []
    except Exception as e:
        message_container.error(f"Error: {e}")
        return []


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
    # Add user message to history
    st.session_state.chat_history.append({"role": "user", "content": prompt})

    # Send message and get response
    with st.chat_message("assistant"):
        final_messages = send_message(prompt, st.container())

    # Add response to history
    if final_messages:
        for msg in final_messages:
            msg_type = msg.get("type", "")
            content = msg.get("content", "")

            if msg_type == "tool":
                if isinstance(content, (dict, list)):
                    content_str = json.dumps(content, indent=2)
                else:
                    content_str = str(content)
                st.session_state.chat_history.append(
                    {"role": "assistant", "content": content_str, "is_tool": True}
                )
            elif msg_type in ["ai", "assistant"]:
                st.session_state.chat_history.append(
                    {"role": "assistant", "content": content, "is_tool": False}
                )

    st.rerun()
