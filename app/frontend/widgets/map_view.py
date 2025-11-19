import json
import socket
import threading
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Dict, List, Optional

from PySide6.QtCore import QObject, QUrl, Signal, Slot
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QFrame, QVBoxLayout


@dataclass
class MapLayerPalette:
    name: str
    kind: str
    color: str
    line_width: float = 1.0


class _RangeRequestHandler(BaseHTTPRequestHandler):
    """Lightweight static file handler that supports Range requests."""

    base_dir: Path

    def log_message(self, format: str, *args) -> None:  # pragma: no cover - quiet server
        return

    def do_GET(self):  # type: ignore[override]
        root = self.base_dir
        if not self.path.startswith("/pmtiles/"):
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        rel = self.path[len("/pmtiles/") :]
        rel = rel.lstrip("/")
        file_path = (root / rel).resolve()
        if not str(file_path).startswith(str(root)):
            self.send_error(HTTPStatus.FORBIDDEN)
            return
        if not file_path.exists():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        try:
            size = file_path.stat().st_size
            range_header = self.headers.get("Range")
            start = 0
            end = size - 1
            if range_header:
                try:
                    _bytes, rng = range_header.split("=")
                    start_str, end_str = rng.split("-")
                    start = int(start_str)
                    if end_str:
                        end = int(end_str)
                except Exception:
                    self.send_error(HTTPStatus.REQUESTED_RANGE_NOT_SATISFIABLE)
                    return
                if end >= size:
                    end = size - 1
            length = end - start + 1
            with file_path.open("rb") as fh:
                fh.seek(start)
                data = fh.read(length)
            status = HTTPStatus.PARTIAL_CONTENT if range_header else HTTPStatus.OK
            self.send_response(status)
            self.send_header("Content-Type", "application/octet-stream")
            if range_header:
                self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        except OSError:
            self.send_error(HTTPStatus.INTERNAL_SERVER_ERROR)


class LocalTileServer:
    """Serves PMTiles files with HTTP Range support for the embedded webview."""

    def __init__(self, base_dir: Path):
        handler_cls = type("_Handler", (_RangeRequestHandler,), {})
        handler_cls.base_dir = base_dir  # type: ignore[attr-defined]
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(("127.0.0.1", 0))
        addr, port = sock.getsockname()
        sock.close()
        self._server = ThreadingHTTPServer(("127.0.0.1", port), handler_cls)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        self.base_url = f"http://127.0.0.1:{port}/pmtiles"

    def stop(self):
        self._server.shutdown()
        self._server.server_close()


class MapBridge(QObject):
    ready = Signal()
    markerClicked = Signal(str)

    @Slot()
    def requestConfig(self):
        self.ready.emit()

    @Slot(str)
    def handleMarkerClick(self, marker_id: str):
        self.markerClicked.emit(marker_id)


class MapView(QFrame):
    """Wraps a QWebEngineView running MapLibre + pmtiles for real offline maps."""

    marker_selected = Signal(str)

    def __init__(self, offline_dir: Path):
        super().__init__()
        self._config: Optional[Dict] = None
        self._tile_server = LocalTileServer(offline_dir)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.setLayout(layout)

        self.web = QWebEngineView()
        layout.addWidget(self.web)

        self.bridge = MapBridge()
        self.bridge.ready.connect(self._sync_state)
        self.bridge.markerClicked.connect(self.marker_selected)

        self.channel = QWebChannel()
        self.channel.registerObject("Bridge", self.bridge)
        self.web.page().setWebChannel(self.channel)

        html_path = Path(__file__).with_name("assets") / "map_view.html"
        self.web.setUrl(QUrl.fromLocalFile(str(html_path)))

    def update_map(self, config: Dict):
        """Persist config so it can be pushed once the webview is ready."""
        self._config = config
        self._sync_state()

    def _sync_state(self):
        if not self._config:
            return
        payload = dict(self._config)
        payload["tileBase"] = self._tile_server.base_url
        js = f"window.updateMap({json.dumps(payload)});"
        self.web.page().runJavaScript(js)

    def build_style(self, metadata: Optional[Dict]) -> Dict:
        """Generate a very small inlined style for whichever layers are available."""
        layers = metadata.get("vector_layers") if metadata else []
        available = {layer.get("id") for layer in layers if isinstance(layer, dict)}
        palettes: List[MapLayerPalette] = []
        if "earth" in available:
            palettes.append(MapLayerPalette("earth", "fill", "#0f172a"))
        if "landuse" in available or "landcover" in available:
            target = "landuse" if "landuse" in available else "landcover"
            palettes.append(MapLayerPalette(target, "fill", "#1c3d1f"))
        if "water" in available:
            palettes.append(MapLayerPalette("water", "fill", "#155e75"))
        if "roads" in available:
            palettes.append(MapLayerPalette("roads", "line", "#f97316", 1.5))
        if "railways" in available:
            palettes.append(MapLayerPalette("railways", "line", "#f87171", 1.0))
        if "boundaries" in available:
            palettes.append(MapLayerPalette("boundaries", "line", "#f1f5f9", 1.2))
        style_layers = []
        for layer in palettes:
            entry = {
                "id": f"{layer.name}-{layer.kind}",
                "type": layer.kind,
                "source": "pmtiles-source",
                "source-layer": layer.name,
            }
            if layer.kind == "fill":
                entry["paint"] = {"fill-color": layer.color, "fill-opacity": 0.8}
            else:
                entry["paint"] = {
                    "line-color": layer.color,
                    "line-width": layer.line_width,
                }
            style_layers.append(entry)
        return {
            "version": 8,
            "sources": {
                "pmtiles-source": {
                    "type": "vector",
                    "url": "",  # set on update
                }
            },
            "layers": style_layers or [
                {
                    "id": "background",
                    "type": "background",
                    "paint": {"background-color": "#0f172a"},
                }
            ],
        }
