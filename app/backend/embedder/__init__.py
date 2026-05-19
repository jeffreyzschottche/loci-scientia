"""Aitje embedder: document ingestion, chunking and Qdrant-sync.

Ported van de Laravel `app/embedder/backend/` naar FastAPI zodat het hele
device één proces vormt. Single-tenant, lokaal op de LAN.
"""

from .routes import router

__all__ = ["router"]
