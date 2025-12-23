import os
from pathlib import Path
from typing import Optional

from pydantic import BaseModel


class Settings(BaseModel):
    host: str = "127.0.0.1"
    port: int = 8000
    ws_path: str = "/ws"
    offline_assets_dir: Optional[Path] = None
    # TensorRT-LLM settings (OpenAI-compatible API)
    llm_base_url: str = "http://127.0.0.1:8000"
    llm_model: str = "gemma-3-1b-it"
    llm_timeout: float = 120.0


def get_settings() -> "Settings":
    assets_dir = os.environ.get("OFFLINE_ASSETS_DIR") or os.environ.get("PMTILES_DATA_DIR")
    offline_assets_dir: Optional[Path] = None
    if assets_dir:
        offline_assets_dir = Path(assets_dir).expanduser().resolve()

    # TensorRT-LLM OpenAI-compatible API configuration
    llm_base_url = (
        os.environ.get("LLM_BASE_URL")
        or os.environ.get("TENSORRT_LLM_URL")
        or "http://127.0.0.1:8000"
    )
    # Ensure base URL has no trailing slash
    llm_base_url = llm_base_url.rstrip("/")

    llm_model = os.environ.get("LLM_MODEL") or "gemma-3-1b-it"

    try:
        llm_timeout = float(os.environ.get("LLM_TIMEOUT", "120"))
    except ValueError:
        llm_timeout = 120.0

    return Settings(
        offline_assets_dir=offline_assets_dir,
        llm_base_url=llm_base_url,
        llm_model=llm_model,
        llm_timeout=llm_timeout,
    )


settings = get_settings()
