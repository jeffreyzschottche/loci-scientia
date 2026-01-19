import os
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

KV_CACHE_TYPES = {"f16", "q8_0", "q4_0"}


def _split_env_list(raw: str) -> list[str]:
    if not raw:
        return []
    return [item.strip() for item in raw.split(",")]


def _normalize_kv_quant(value: str) -> Optional[str]:
    if not value:
        return None
    normalized = value.strip().lower()
    if normalized in KV_CACHE_TYPES:
        return normalized
    return None


def _parse_max_context(value: str) -> Optional[int]:
    if not value:
        return None
    try:
        parsed = int(value.strip())
    except ValueError:
        return None
    if parsed <= 0:
        return None
    return parsed


def _map_max_context(models: list[str], values: list[str]) -> dict[str, Optional[int]]:
    mapping: dict[str, Optional[int]] = {}
    for idx, model in enumerate(models):
        raw = values[idx] if idx < len(values) else ""
        mapping[model] = _parse_max_context(raw)
    return mapping


class Settings(BaseModel):
    host: str = "127.0.0.1"
    port: int = 8000
    ws_path: str = "/ws"
    offline_assets_dir: Optional[Path] = None
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "gemma3:4b"
    ollama_models: list[str] = ["gemma3:4b"]
    ollama_kv_cache_type: Optional[str] = None
    ollama_max_context: dict[str, Optional[int]] = Field(default_factory=dict)
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
    raw_kv = os.environ.get("OLLAMA_KV_CACHE_TYPE")
    if raw_kv is None:
        raw_kv = os.environ.get("OLLAMA_KV_QUANT", "")
    raw_kv = (raw_kv or "").split(",")[0]
    ollama_kv_cache_type = _normalize_kv_quant(raw_kv)
    raw_context = _split_env_list(os.environ.get("OLLAMA_MAX_CONTEXT", ""))
    ollama_models = [model.strip() for model in raw_models.split(",") if model.strip()]
    if ollama_model not in ollama_models:
        ollama_models.insert(0, ollama_model)
        raw_context.insert(0, "")
    ollama_max_context = _map_max_context(ollama_models, raw_context)
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
        ollama_kv_cache_type=ollama_kv_cache_type,
        ollama_max_context=ollama_max_context,
        ollama_timeout=ollama_timeout,
        admin_usernames=admin_usernames or ["ADMIN"],
    )


settings = get_settings()
