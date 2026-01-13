import os
from pathlib import Path
from typing import Optional

from pydantic import BaseModel


class Settings(BaseModel):
    host: str = "127.0.0.1"
    port: int = 8000
    ws_path: str = "/ws"
    offline_assets_dir: Optional[Path] = None
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "gemma3:4b"
    ollama_models: list[str] = ["gemma3:4b"]
    ollama_timeout: float = 60.0
    admin_usernames: list[str] = ["ADMIN"]


def get_settings() -> "Settings":
    assets_dir = os.environ.get("OFFLINE_ASSETS_DIR") or os.environ.get("PMTILES_DATA_DIR")
    offline_assets_dir: Optional[Path] = None
    if assets_dir:
        offline_assets_dir = Path(assets_dir).expanduser().resolve()
    ollama_base_url = (
        os.environ.get("OLLAMA_BASE_URL")
        or os.environ.get("OLLAMA_HOST")
        or "http://127.0.0.1:11434"
    )
    # Zorg dat de base URL geen trailing slash heeft, zodat joinen voorspelbaar is.
    ollama_base_url = ollama_base_url.rstrip("/")
    ollama_model = os.environ.get("OLLAMA_MODEL") or "gemma3:4b"
    raw_models = os.environ.get("OLLAMA_MODELS", "")
    ollama_models = [model.strip() for model in raw_models.split(",") if model.strip()]
    if ollama_model not in ollama_models:
        ollama_models.insert(0, ollama_model)
    try:
        ollama_timeout = float(os.environ.get("OLLAMA_TIMEOUT", "60"))
    except ValueError:
        ollama_timeout = 60.0
    raw_admins = os.environ.get("ADMIN_USERS", "ADMIN")
    admin_usernames = [name.strip() for name in raw_admins.split(",") if name.strip()]
    return Settings(
        offline_assets_dir=offline_assets_dir,
        ollama_base_url=ollama_base_url,
        ollama_model=ollama_model,
        ollama_models=ollama_models,
        ollama_timeout=ollama_timeout,
        admin_usernames=admin_usernames or ["ADMIN"],
    )


settings = get_settings()
