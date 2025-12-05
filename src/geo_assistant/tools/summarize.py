"""Tools for summarizing satellite images using LLM-based analysis."""

import os
from typing import Annotated

import dotenv
import dspy
from langchain_core.messages import ToolMessage
from langchain_core.tools import tool
from langchain_core.tools.base import InjectedToolCallId
from langgraph.prebuilt import InjectedState
from langgraph.types import Command

from geo_assistant.agent.state import GeoAssistantState

dotenv.load_dotenv()


class SatImgSummary(dspy.Signature):
    "Describe things you see in the satellite image."

    img: dspy.Image = dspy.InputField(desc="A satellite image")
    answer: str = dspy.OutputField(desc="Description of the image")


class SatImgSummaryAgent(dspy.Module):
    """Agent for generating summaries of satellite images using an LLM."""

    def __init__(
        self,
        model: str = os.environ.get("OLLAMA_IMAGE_MODEL", "ministral-3:14b-cloud"),
        api_base: str = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434"),
        temperature: float = 0.5,
        max_tokens: int = 4_096,
    ) -> None:
        """Initialize the satellite image summary agent.

        Args:
            model: The Ollama model to use for summarization
            api_base: Base URL for the Ollama API
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens to generate
        """
        super().__init__()
        self.ollama_model = dspy.LM(
            model=f"ollama/{model}",
            api_base=api_base,
            api_key="",
            temperature=temperature,
            max_tokens=max_tokens,
        )
        dspy.configure(lm=self.ollama_model)
        self.summarizer = dspy.Predict(SatImgSummary)

    def forward(self, img_url: str) -> dspy.Prediction:
        """Generate a summary for the given image URL.

        Args:
            img_url: URL of the image to summarize

        Returns:
            dspy.Prediction containing the image summary
        """
        return self.summarizer(img=dspy.Image(img_url))


# Singleton instance to avoid repeated initialization
_SUMMARIZER_AGENT = SatImgSummaryAgent()


@tool
async def summarize_sat_img(
    state: Annotated[GeoAssistantState, InjectedState],
    tool_call_id: Annotated[str | None, InjectedToolCallId] = None,
) -> Command:
    """Summarize the contents of a satellite image using an LLM.

    Args:
        img_url: URL of the satellite image to analyze
        tool_call_id: Optional ID for tracking the tool call

    Returns:
        Command containing the image summary and metadata

    Raises:
        ValueError: If the image URL is invalid or the image cannot be processed
    """
    if not state["naip_img_bytes"]:
        return Command(
            update={
                "messages": [
                    ToolMessage(
                        content="No NAIP image bytes available yet",
                        tool_call_id=tool_call_id,
                    ),
                ],
            },
        )
    img_url = f"data:image/jpeg;base64,{state['naip_img_bytes']}"
    summary = _SUMMARIZER_AGENT(img_url)
    message_content = summary.answer
    return Command(
        update={
            "messages": [
                ToolMessage(content=message_content, tool_call_id=tool_call_id),
            ],
        },
    )
