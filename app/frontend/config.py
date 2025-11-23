import os


def _default_backend_http(host: str, port: int) -> str:
    return f"http://{host}:{port}"


def _http_to_ws(url: str) -> str:
    if url.startswith("https://"):
        return "wss://" + url[len("https://") :]
    if url.startswith("http://"):
        return "ws://" + url[len("http://") :]
    return url


BACKEND_HOST = os.environ.get("BACKEND_HOST", "127.0.0.1")
BACKEND_PORT = int(os.environ.get("BACKEND_PORT", "8000"))
BACKEND_HTTP = os.environ.get("BACKEND_HTTP", _default_backend_http(BACKEND_HOST, BACKEND_PORT)).rstrip("/")
BACKEND_WS = os.environ.get("BACKEND_WS") or _http_to_ws(BACKEND_HTTP)
BACKEND_TIMEOUT = int(os.environ.get("BACKEND_TIMEOUT", "6"))

API_ROUTES_DEFAULT_PORT = int(os.environ.get("API_ROUTES_DEFAULT_PORT", str(BACKEND_PORT)))

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
