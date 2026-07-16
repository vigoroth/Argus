"""Canonical Second Brain integration for Argus."""

from app.brain.service import (
    BrainError,
    capture_message,
    get_brain_status,
    list_stage_notes,
    prepare_context,
    query_brain,
)

__all__ = [
    "BrainError",
    "capture_message",
    "get_brain_status",
    "list_stage_notes",
    "prepare_context",
    "query_brain",
]
