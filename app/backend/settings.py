import os
from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel, Field

KV_CACHE_TYPES = {"f16", "q8_0", "q4_0"}

LLMProvider = Literal["ollama", "lemonade"]


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


def _parse_timeout(value: Optional[str], default: float) -> float:
    try:
        return float(value) if value else default
    except ValueError:
        return default


def _parse_bool(value: Optional[str], default: bool) -> bool:
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return default


def _normalize_provider(value: Optional[str]) -> LLMProvider:
    normalized = (value or "").strip().lower()
    if normalized == "lemonade":
        return "lemonade"
    return "ollama"


class Settings(BaseModel):
    host: str = "127.0.0.1"
    port: int = 8000
    ws_path: str = "/ws"
    offline_assets_dir: Optional[Path] = None
    llm_provider: LLMProvider = "ollama"
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "gemma3:4b"
    ollama_models: list[str] = ["gemma3:4b"]
    ollama_kv_cache_type: Optional[str] = None
    ollama_max_context: dict[str, Optional[int]] = Field(default_factory=dict)
    ollama_timeout: float = 180.0
    lemonade_base_url: str = "http://127.0.0.1:8020"
    lemonade_model: str = ""
    lemonade_models: list[str] = Field(default_factory=list)
    lemonade_timeout: float = 180.0
    lemonade_max_context: dict[str, Optional[int]] = Field(default_factory=dict)
    lemonade_vision_enabled: bool = False
    admin_usernames: list[str] = ["ADMIN"]
    chat_summary_idle_minutes: int = 0
    prompt_modes: list[str] = ["Developer", "Finance", "Law", "Child"]

    @property
    def active_model(self) -> str:
        if self.llm_provider == "lemonade":
            return self.lemonade_model or (self.lemonade_models[0] if self.lemonade_models else "")
        return self.ollama_model

    @property
    def active_models(self) -> list[str]:
        if self.llm_provider == "lemonade":
            return list(self.lemonade_models)
        return list(self.ollama_models)

    @property
    def active_base_url(self) -> str:
        if self.llm_provider == "lemonade":
            return self.lemonade_base_url
        return self.ollama_base_url

    @property
    def active_timeout(self) -> float:
        if self.llm_provider == "lemonade":
            return self.lemonade_timeout
        return self.ollama_timeout

    @property
    def active_max_context(self) -> dict[str, Optional[int]]:
        if self.llm_provider == "lemonade":
            return self.lemonade_max_context
        return self.ollama_max_context


def get_settings() -> "Settings":
    assets_dir = os.environ.get("OFFLINE_ASSETS_DIR") or os.environ.get("PMTILES_DATA_DIR")
    offline_assets_dir: Optional[Path] = None
    if assets_dir:
        offline_assets_dir = Path(assets_dir).expanduser().resolve()

    llm_provider = _normalize_provider(os.environ.get("LLM_PROVIDER"))

    ollama_base_url = (
        os.environ.get("OLLAMA_BASE_URL")
        or os.environ.get("OLLAMA_HOST")
        or "http://127.0.0.1:11434"
    )
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
    ollama_timeout = _parse_timeout(os.environ.get("OLLAMA_TIMEOUT"), 180.0)

    lemonade_base_url = (
        os.environ.get("LEMONADE_BASE_URL")
        or os.environ.get("LEMONADE_HOST")
        or "http://127.0.0.1:8020"
    ).rstrip("/")
    lemonade_model = (os.environ.get("LEMONADE_MODEL") or "").strip()
    raw_lemonade_models = os.environ.get("LEMONADE_MODELS", "")
    lemonade_models = [m.strip() for m in raw_lemonade_models.split(",") if m.strip()]
    if lemonade_model and lemonade_model not in lemonade_models:
        lemonade_models.insert(0, lemonade_model)
    lemonade_timeout = _parse_timeout(os.environ.get("LEMONADE_TIMEOUT"), 180.0)
    raw_lemonade_context = _split_env_list(os.environ.get("LEMONADE_MAX_CONTEXT", ""))
    lemonade_max_context = _map_max_context(lemonade_models, raw_lemonade_context)
    lemonade_vision_enabled = _parse_bool(os.environ.get("LEMONADE_VISION_ENABLED"), False)

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
    return Settings(
        offline_assets_dir=offline_assets_dir,
        llm_provider=llm_provider,
        ollama_base_url=ollama_base_url,
        ollama_model=ollama_model,
        ollama_models=ollama_models,
        ollama_kv_cache_type=ollama_kv_cache_type,
        ollama_max_context=ollama_max_context,
        ollama_timeout=ollama_timeout,
        lemonade_base_url=lemonade_base_url,
        lemonade_model=lemonade_model,
        lemonade_models=lemonade_models,
        lemonade_timeout=lemonade_timeout,
        lemonade_max_context=lemonade_max_context,
        lemonade_vision_enabled=lemonade_vision_enabled,
        admin_usernames=admin_usernames or ["ADMIN"],
        chat_summary_idle_minutes=chat_summary_idle_minutes,
        prompt_modes=prompt_modes,
    )


settings = get_settings()
