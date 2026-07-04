from langchain_core.tools import tool
from app.memory.long_term import remember, recall_all


@tool
def save_memory(key: str, value: str) -> str:
    """Save a durable fact about the user for future conversations.
    Use this when the user shares lasting information about themselves:
    their name, goals, preferences, location, ongoing projects.
    Example: save_memory("job_search", "looking for ML roles in Athens").
    """
    remember(key, value)
    return f"Saved: {key} = {value}"


@tool
def load_memory() -> str:
    """Load everything known about the user from past conversations.
    Use this at the start of a conversation, or when you need context
    about the user's goals, preferences, or situation.
    """
    facts = recall_all()
    if not facts:
        return "No stored facts about the user yet."
    return "\n".join(f"- {k}: {v}" for k, v in facts.items())