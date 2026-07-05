"""Conversation persistence for the chat UI.

Two tables:
  conversations — one row per chat thread (id, title, timestamps)
  messages      — one row per message, linked to a conversation
The conversation id doubles as the LangGraph checkpointer thread_id,
so each conversation also gets its own memory.

Run the demo:  python -m app.web.conversations
"""
import uuid

import psycopg

from app.core.config import get_settings


def _conn():
    url = get_settings().database_url.replace("postgresql+psycopg://", "postgresql://")
    return psycopg.connect(url)


def init_tables() -> None:
    """Create the conversations and messages tables if they don't exist."""
    with _conn() as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS conversations ("
            "id TEXT PRIMARY KEY, "
            "title TEXT NOT NULL, "
            "created_at TIMESTAMPTZ DEFAULT now(), "
            "updated_at TIMESTAMPTZ DEFAULT now())"
        )
        conn.execute(
            "CREATE TABLE IF NOT EXISTS messages ("
            "id SERIAL PRIMARY KEY, "
            "conversation_id TEXT REFERENCES conversations(id) ON DELETE CASCADE, "
            "role TEXT NOT NULL, "
            "content TEXT NOT NULL, "
            "created_at TIMESTAMPTZ DEFAULT now())"
        )


def create_conversation(first_message: str) -> str:
    """Create a new conversation, titled from its first message. Returns its id."""
    conv_id = str(uuid.uuid4())
    title = first_message.strip()[:40] or "New chat"
    if len(first_message.strip()) > 40:
        title += "…"
    with _conn() as conn:
        conn.execute(
            "INSERT INTO conversations (id, title) VALUES (%s, %s)",
            (conv_id, title),
        )
    return conv_id


def list_conversations() -> list[dict]:
    """Return all conversations, newest activity first."""
    with _conn() as conn:
        rows = conn.execute(
            "SELECT id, title, updated_at FROM conversations ORDER BY updated_at DESC"
        ).fetchall()
    return [{"id": r[0], "title": r[1], "updated_at": str(r[2])} for r in rows]


def add_message(conversation_id: str, role: str, content: str) -> None:
    """Save a single message and bump the conversation's updated_at."""
    with _conn() as conn:
        conn.execute(
            "INSERT INTO messages (conversation_id, role, content) VALUES (%s, %s, %s)",
            (conversation_id, role, content),
        )
        conn.execute(
            "UPDATE conversations SET updated_at = now() WHERE id = %s",
            (conversation_id,),
        )


def get_messages(conversation_id: str) -> list[dict]:
    """Return all messages in a conversation, oldest first."""
    with _conn() as conn:
        rows = conn.execute(
            "SELECT role, content, created_at FROM messages "
            "WHERE conversation_id = %s ORDER BY created_at",
            (conversation_id,),
        ).fetchall()
    return [{"role": r[0], "content": r[1], "created_at": str(r[2])} for r in rows]


