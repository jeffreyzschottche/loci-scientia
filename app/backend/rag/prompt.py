"""Prompt construction helpers."""

from .vectorMatch import MatchResult


def build_prompt(match: MatchResult) -> str:
    """Return a short Dutch description for the reversed pair."""

    return f"{match.preview}, is oorspronkelijk : {match.embedding.text}"
