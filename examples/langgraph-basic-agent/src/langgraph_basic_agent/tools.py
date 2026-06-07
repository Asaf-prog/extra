"""Deterministic local tools for the example graph."""

from __future__ import annotations

from langchain_core.tools import tool


@tool
def count_words(text: str) -> str:
    """Count whitespace-separated words in the provided text."""
    words = [word for word in text.split() if word]
    return f"word_count={len(words)}"
