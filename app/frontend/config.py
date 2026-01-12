import os


def _default_backend_http(host: str, port: int) -> str:
    return f"http://{host}:{port}"


def _http_to_ws(url: str) -> str:
    if url.startswith("https://"):
        return "wss://" + url[len("https://") :]
    if url.startswith("http://"):
        return "ws://" + url[len("http://") :]
    return url


DEVICE_NAME_PREFIX = os.environ.get("DEVICE_NAME_PREFIX", "aitje").strip() or "aitje"
DEVICE_NUMBER = os.environ.get("DEVICE_NUMBER", "1").strip() or "1"
DEVICE_HOSTNAME = os.environ.get("DEVICE_HOSTNAME")
if not DEVICE_HOSTNAME:
    DEVICE_HOSTNAME = f"{DEVICE_NAME_PREFIX}-{DEVICE_NUMBER}".strip("-")
DEVICE_MDNS = os.environ.get("DEVICE_MDNS") or f"{DEVICE_HOSTNAME}.local"

_ENV_BACKEND_HOST = os.environ.get("BACKEND_HOST")
if _ENV_BACKEND_HOST and _ENV_BACKEND_HOST not in {"0.0.0.0", "127.0.0.1"}:
    BACKEND_HOST = _ENV_BACKEND_HOST
else:
    BACKEND_HOST = DEVICE_MDNS
BACKEND_PORT = int(os.environ.get("BACKEND_PORT", "8000"))
BACKEND_HTTP = os.environ.get("BACKEND_HTTP", _default_backend_http(BACKEND_HOST, BACKEND_PORT)).rstrip("/")
BACKEND_WS = os.environ.get("BACKEND_WS") or _http_to_ws(BACKEND_HTTP)
BACKEND_TIMEOUT = int(os.environ.get("BACKEND_TIMEOUT", "6"))
PUBLIC_BASE_URL = os.environ.get("PUBLIC_BASE_URL", _default_backend_http(DEVICE_MDNS, BACKEND_PORT)).rstrip("/")
_ENV_BEARER_TOKEN = (
    os.environ.get("AITJE_BEARER_TOKEN")
    or os.environ.get("BACKEND_BEARER_TOKEN")
    or ""
)
BACKEND_BEARER_TOKEN = _ENV_BEARER_TOKEN.strip()

API_ROUTES_DEFAULT_PORT = int(os.environ.get("API_ROUTES_DEFAULT_PORT", str(BACKEND_PORT)))

OLLAMA_MODELS = [
    model.strip()
    for model in os.environ.get("OLLAMA_MODELS", "").split(",")
    if model.strip()
]

PMTILES_HOST = os.environ.get("PMTILES_HOST", "127.0.0.1")
PMTILES_PORT = int(os.environ.get("PMTILES_PORT", "8080"))
PMTILES_BASE_URL = os.environ.get("PMTILES_BASE_URL", f"http://{PMTILES_HOST}:{PMTILES_PORT}").rstrip("/")
PMTILES_TILESET = os.environ.get("PMTILES_TILESET", "europe").strip("/") or "europe"
PMTILES_TILE_TEMPLATE = f"{PMTILES_BASE_URL}/{PMTILES_TILESET}/{{z}}/{{x}}/{{y}}.mvt"

MAP_GLYPHS_URL = os.environ.get("MAP_GLYPHS_URL") or f"{BACKEND_HTTP}/fonts/{{fontstack}}/{{range}}.pbf"
MAP_SPRITE_URL = os.environ.get("MAP_SPRITE_URL") or f"{BACKEND_HTTP}/sprites/v4/light"
PMTILES_STATUS_HINT = os.environ.get(
    "PMTILES_STATUS_HINT",
    f"Kaartdata kon niet geladen worden. Controleer of de pmtiles-server draait op {PMTILES_HOST}:{PMTILES_PORT} en dat {PMTILES_TILESET}.pmtiles beschikbaar is.",
)
