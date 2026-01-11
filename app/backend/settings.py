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
    ollama_models: list[str] = ["gemma2:2b", "gemma3:1b", "gemma3:4b"]
    ollama_timeout: float = 60.0


def _parse_ollama_models(raw: Optional[str], current: str) -> list[str]:
    if raw:
        models = [part.strip() for part in raw.split(",") if part.strip()]
    else:
        models = []
    if not models:
        models = ["gemma2:2b", "gemma3:1b", "gemma3:4b"]
    if current not in models:
        models.append(current)
    return models


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
    ollama_models = _parse_ollama_models(os.environ.get("OLLAMA_MODELS"), ollama_model)
    try:
        ollama_timeout = float(os.environ.get("OLLAMA_TIMEOUT", "60"))
    except ValueError:
        ollama_timeout = 60.0
    return Settings(
        offline_assets_dir=offline_assets_dir,
        ollama_base_url=ollama_base_url,
        ollama_model=ollama_model,
        ollama_models=ollama_models,
        ollama_timeout=ollama_timeout,
    )


settings = get_settings()
