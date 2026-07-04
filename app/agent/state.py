from typing import Annotated
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage
from typing_extensions import TypedDict


class AgentState(TypedDict):
    """The state that flows through every node in the graph.

    messages is the full conversation history — system prompt, human
    input, assistant replies, tool calls, tool results. Every node
    reads from it and writes back to it.
    """

    messages: Annotated[list[BaseMessage], add_messages]