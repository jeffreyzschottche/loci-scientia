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
    ollama_timeout: float = 180.0
    admin_usernames: list[str] = ["ADMIN"]
    chat_summary_idle_minutes: int = 0
    prompt_modes: list[str] = ["Developer", "Finance", "Law", "Child"]
    searxng_url: Optional[str] = None
    searxng_timeout: float = 8.0
    searxng_max_results: int = 5
    searxng_language: str = "nl"
    searxng_safesearch: int = 1
    embedder_admin_email: Optional[str] = None
    embedder_admin_password: Optional[str] = None
    embedder_admin_name: str = "Aitje Admin"
    embedder_db_path: Optional[Path] = None
    embedder_upload_dir: Optional[Path] = None


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
        ollama_timeout = float(os.environ.get("OLLAMA_TIMEOUT", "180"))
    except ValueError:
        ollama_timeout = 180.0
    raw_admins = os.environ.get("ADMIN_USERS", "ADMIN")
    admin_usernames = [name.strip() for name in raw_admins.split(",") if name.strip()]
    raw_idle_summary = os.environ.get("CHAT_SUMMARY_IDLE_MINUTES", "").strip()
    try:
        chat_summary_idle_minutes = int(raw_idle_summary) if raw_idle_summary else 0
    except ValueError:
        chat_summary_idle_minutes = 0
    if chat_summary_idle_minutes < 0:
        chat_summary_idle_minutes = 0
    raw_prompt_modes = os.environ.get("PROMPT_MODES", "Developer,Finance,Law,Child")
    prompt_modes = [mode.strip() for mode in raw_prompt_modes.split(",") if mode.strip()]
    if not prompt_modes:
        prompt_modes = ["Developer", "Finance", "Law", "Child"]

    raw_searxng_url = (os.environ.get("SEARXNG_URL") or "").strip().rstrip("/")
    searxng_url = raw_searxng_url or None
    try:
        searxng_timeout = float(os.environ.get("SEARXNG_TIMEOUT", "8"))
    except ValueError:
        searxng_timeout = 8.0
    try:
        searxng_max_results = int(os.environ.get("SEARXNG_MAX_RESULTS", "5"))
    except ValueError:
        searxng_max_results = 5
    if searxng_max_results <= 0:
        searxng_max_results = 5
    searxng_language = (os.environ.get("SEARXNG_LANGUAGE") or "nl").strip() or "nl"
    try:
        searxng_safesearch = int(os.environ.get("SEARXNG_SAFESEARCH", "1"))
    except ValueError:
        searxng_safesearch = 1
    if searxng_safesearch not in (0, 1, 2):
        searxng_safesearch = 1

    project_root = Path(__file__).resolve().parents[2]
    devices_db_dir = project_root / "devices_db"
    embedder_db_path = devices_db_dir / "embedder.db"
    embedder_upload_dir = devices_db_dir / "embedder_uploads"
    embedder_admin_email = (os.environ.get("EMBEDDER_USER_EMAIL") or "").strip() or None
    embedder_admin_password = os.environ.get("EMBEDDER_USER_PASSWORD") or None
    embedder_admin_name = (os.environ.get("EMBEDDER_USER_NAME") or "").strip() or "Aitje Admin"

    return Settings(
        offline_assets_dir=offline_assets_dir,
        ollama_base_url=ollama_base_url,
        ollama_model=ollama_model,
        ollama_models=ollama_models,
        ollama_kv_cache_type=ollama_kv_cache_type,
        ollama_max_context=ollama_max_context,
        ollama_timeout=ollama_timeout,
        admin_usernames=admin_usernames or ["ADMIN"],
        chat_summary_idle_minutes=chat_summary_idle_minutes,
        prompt_modes=prompt_modes,
        searxng_url=searxng_url,
        searxng_timeout=searxng_timeout,
        searxng_max_results=searxng_max_results,
        searxng_language=searxng_language,
        searxng_safesearch=searxng_safesearch,
        embedder_admin_email=embedder_admin_email,
        embedder_admin_password=embedder_admin_password,
        embedder_admin_name=embedder_admin_name,
        embedder_db_path=embedder_db_path,
        embedder_upload_dir=embedder_upload_dir,
    )


settings = get_settings()
