from .schemas import ChatRequest


def handle_ask(_: ChatRequest) -> dict:
    """Return a fixed acknowledgement for /api/v1/ask requests."""
    return {"message": "bericht ontvangen"}
