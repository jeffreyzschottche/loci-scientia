"""Fake LLM wrapper used by the RAG pipeline."""


def run_llm(prompt: str, original_text: str) -> str:
    """Append the length of the recovered string to the prompt."""

    length = len(original_text)
    return f"{prompt}. Dat is {length} letters"
