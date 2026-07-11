import json
import os
from pathlib import Path


def _default_backend_http(host: str, port: int) -> str:
    return f"http://{host}:{port}"


def _default_public_base(host: str) -> str:
    """LAN-facing URL served by Caddy.

    Defaults to https on the implicit port 443; override via PUBLIC_BASE_URL
    if Caddy isn't running or is on a non-standard port (then it falls back
    to plain http://host:BACKEND_PORT)."""
    port = (os.environ.get("CADDY_HTTPS_PORT") or "443").strip() or "443"
    if port == "443":
        return f"https://{host}"
    return f"https://{host}:{port}"


def _default_setup_url(host: str) -> str:
    """First-time onboarding URL served over plain HTTP by Caddy on port 80.

    This is what the QR codes encode — the page installs the local CA and
    then forwards the client to the HTTPS app."""
    port = (os.environ.get("CADDY_HTTP_PORT") or "80").strip() or "80"
    if port == "80":
        return f"http://{host}/connect"
    return f"http://{host}:{port}/connect"


def _load_local_admin_token() -> str:
    token_path = Path(__file__).resolve().parents[2] / "devices_db" / "admin_token.json"
    try:
        raw = token_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return ""
    token = payload.get("token", "")
    if not isinstance(token, str):
        return ""
    return token.strip()


DEVICE_NAME_PREFIX = os.environ.get("DEVICE_NAME_PREFIX", "aitje").strip() or "aitje"
DEVICE_NUMBER = os.environ.get("DEVICE_NUMBER", "1").strip() or "1"
DEVICE_HOSTNAME = os.environ.get("DEVICE_HOSTNAME")
if not DEVICE_HOSTNAME:
    DEVICE_HOSTNAME = f"{DEVICE_NAME_PREFIX}-{DEVICE_NUMBER}".strip("-")
DEVICE_MDNS = os.environ.get("DEVICE_MDNS") or f"{DEVICE_HOSTNAME}.local"

_ENV_BACKEND_HOST = os.environ.get("BACKEND_HOST")
if _ENV_BACKEND_HOST and _ENV_BACKEND_HOST not in {"0.0.0.0"}:
    # 127.0.0.1 is a legitimate value now (uvicorn binds loopback when Caddy
    # terminates TLS); preserve it. 0.0.0.0 only makes sense as a *bind* host,
    # never as a connect target.
    BACKEND_HOST = _ENV_BACKEND_HOST
else:
    # Default: talk to uvicorn over loopback. The Qt UI runs on the device
    # itself, so there's never a reason to go through Caddy or the LAN name.
    BACKEND_HOST = "127.0.0.1"
BACKEND_PORT = int(os.environ.get("BACKEND_PORT", "8000"))
BACKEND_HTTP = os.environ.get("BACKEND_HTTP", _default_backend_http(BACKEND_HOST, BACKEND_PORT)).rstrip("/")
BACKEND_TIMEOUT = int(os.environ.get("BACKEND_TIMEOUT", "6"))
PUBLIC_BASE_URL = os.environ.get("PUBLIC_BASE_URL", _default_public_base(DEVICE_MDNS)).rstrip("/")
SETUP_URL = os.environ.get("SETUP_URL", _default_setup_url(DEVICE_MDNS)).rstrip("/")
_ENV_BEARER_TOKEN = (
    os.environ.get("AITJE_BEARER_TOKEN")
    or os.environ.get("BACKEND_BEARER_TOKEN")
    or _load_local_admin_token()
    or ""
)
BACKEND_BEARER_TOKEN = _ENV_BEARER_TOKEN.strip()

API_ROUTES_DEFAULT_PORT = int(os.environ.get("API_ROUTES_DEFAULT_PORT", str(BACKEND_PORT)))

OLLAMA_MODELS = [
    model.strip()
    for model in os.environ.get("OLLAMA_MODELS", "").split(",")
    if model.strip()
]

PROMPT_MODES = [
    mode.strip()
    for mode in os.environ.get("PROMPT_MODES", "Developer,Finance,Law,Child").split(",")
    if mode.strip()
]
