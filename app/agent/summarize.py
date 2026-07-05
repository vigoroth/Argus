"""Pure helpers for long-thread summarization — no LLM or DB imports, so the
render/cut/prune logic is unit-testable in isolation. The stateful node that
actually calls the model lives in app/agent/graph.py (summarize_node)."""


def render_messages(messages: list) -> str:
    """Flatten messages into a compact transcript for the summarizer."""
    lines = []
    for m in messages:
        role = {"HumanMessage": "user", "AIMessage": "assistant",
                "ToolMessage": "tool", "SystemMessage": "system"}.get(
                    type(m).__name__, "msg")
        content = m.content if isinstance(m.content, str) else str(m.content)
        tool_calls = getattr(m, "tool_calls", None)
        if tool_calls:
            names = ", ".join(tc.get("name", "?") for tc in tool_calls)
            content = (content + f" [called: {names}]").strip()
        if content:
            lines.append(f"{role}: {content}")
    return "\n".join(lines)


def count_tokens(messages: list) -> int:
    """Approximate token count of the thread, provider-agnostic and keyless.
    Uses tiktoken's cl100k_base; falls back to a chars/4 heuristic if unavailable.
    Good enough to drive a summarization threshold, not for billing."""
    text = render_messages(messages)
    try:
        import tiktoken
        return len(tiktoken.get_encoding("cl100k_base").encode(text))
    except Exception:
        return len(text) // 4


def choose_cut(messages: list, keep_recent: int) -> int:
    """Index where the kept-verbatim window starts: the last `keep_recent`
    messages, pushed forward so it never begins on a ToolMessage orphaned from
    the AIMessage tool_calls that produced it."""
    cut = max(0, len(messages) - keep_recent)
    while cut < len(messages) and type(messages[cut]).__name__ == "ToolMessage":
        cut += 1
    return cut


def prunable(messages: list, cut: int) -> list:
    """The older prefix eligible for pruning — only messages carrying an id
    (RemoveMessage needs one)."""
    return [m for m in messages[:cut] if getattr(m, "id", None)]
