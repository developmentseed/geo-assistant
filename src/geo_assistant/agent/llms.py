import os
from dotenv import load_dotenv

from langchain_ollama import ChatOllama

# Load environment variables from env file
load_dotenv()

# Get model name from environment variable, default to llama3.2
MODEL_NAME = os.environ.get("OLLAMA_AGENT_MODEL", "llama3.2")
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")

llm = ChatOllama(
    model=MODEL_NAME,
    base_url=OLLAMA_BASE_URL,
)
