from typing import Annotated, NotRequired, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """The state that flows through every node in the graph.

    messages is the full conversation history — system prompt, human
    input, assistant replies, tool calls, tool results. Every node
    reads from it and writes back to it.

    summary is a running condensation of older turns that have been pruned
    from `messages` to keep the model's context bounded on long threads.
    """

    messages: Annotated[list[BaseMessage], add_messages]
    summary: NotRequired[str]
    brain_context: NotRequired[str]
