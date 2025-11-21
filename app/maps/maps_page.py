from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from PySide6.QtWebEngineWidgets import QWebEngineView


class MapsPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        layout.addWidget(self._build_sidebar(), 0)
        layout.addWidget(self._build_map_view(), 1)

    # ---------------------------------------------------------
    # SIDEBAR
    # ---------------------------------------------------------
    def _build_sidebar(self) -> QFrame:
        side = QFrame()
        side.setObjectName("Card")
        side_layout = QVBoxLayout(side)
        side_layout.setContentsMargins(16, 16, 16, 16)
        side_layout.setSpacing(16)

        search = QLineEdit()
        search.setPlaceholderText("Zoek locatie…")
        side_layout.addWidget(search)

        combo_layout = QHBoxLayout()
        combo_layout.setContentsMargins(0, 0, 0, 0)
        combo_layout.setSpacing(8)

        layer_label = QLabel("Kaartlaag")
        layer_label.setStyleSheet("color:#9ca3af;")
        self.layer_combo = QComboBox()
        self.layer_combo.addItems(["Standaard", "Satelliet", "Hoogte"])
        combo_layout.addWidget(layer_label)
        combo_layout.addStretch(1)
        combo_layout.addWidget(self.layer_combo)
        side_layout.addLayout(combo_layout)

        current_btn = QPushButton("Huidige Locatie")
        current_btn.setStyleSheet(
            "background:#2563eb; color:white; border-radius:8px; padding:8px;"
        )
        side_layout.addWidget(current_btn)

        side_layout.addWidget(QLabel("Gedownloade Regio's"))
        region_list = QListWidget()
        for name, size, status in [
            ("Nederland", "1.2 GB", "Offline"),
            ("België", "890 MB", "Offline"),
            ("Duitsland", "3.4 GB", "Download beschikbaar"),
        ]:
            item = QListWidgetItem(f"{name} • {size} • {status}")
            region_list.addItem(item)
        side_layout.addWidget(region_list, 1)

        download_btn = QPushButton("Nieuwe Regio Downloaden")
        download_btn.setStyleSheet(
            "border:1px solid #374151; color:white; border-radius:8px; padding:8px;"
        )
        side_layout.addWidget(download_btn)

        storage = QFrame()
        storage_layout = QVBoxLayout(storage)
        storage_layout.setContentsMargins(0, 0, 0, 0)
        storage_label = QLabel("Kaartdata Opslag: 2.1 / 256 GB")
        storage_label.setStyleSheet("color:#9ca3af;")
        storage_bar = QLabel("████░░░░░░░░░░░░")
        storage_bar.setStyleSheet("font-family: monospace; color:#2563eb;")
        storage_layout.addWidget(storage_label)
        storage_layout.addWidget(storage_bar)
        side_layout.addWidget(storage)

        return side

    # ---------------------------------------------------------
    # MAP VIEW (QWebEngineView + MapLibre + style.json van schijf)
    # ---------------------------------------------------------
    def _build_map_view(self) -> QFrame:
        area = QFrame()
        area.setObjectName("Card")
        layout = QGridLayout(area)
        layout.setContentsMargins(16, 16, 16, 16)

        self.webview = QWebEngineView()

        # style.json ligt in dezelfde map als deze widget
        style_path = Path(__file__).with_name("style.json")
        style_json = style_path.read_text(encoding="utf-8")

        # HTML: we plakken de JSON letterlijk in de <script>-tag
        html = """
<!DOCTYPE html>
<html lang="nl">
<head>
  <meta charset="utf-8" />
  <title>Offline Map (Europe)</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />

  <link
    rel="stylesheet"
    href="https://unpkg.com/maplibre-gl@3.6.2/dist/maplibre-gl.css"
  />

  <style>
    html, body {
      margin: 0;
      padding: 0;
      height: 100%;
      width: 100%;
      background: #020617;
    }
    #map {
      position: absolute;
      inset: 0;
    }
    #status-overlay {
      position: absolute;
      inset: 0;
      display: flex;
      align-items: center;
      justify-content: center;
      text-align: center;
      padding: 16px;
      font-size: 14px;
      background: rgba(2, 6, 23, 0.85);
      color: #fcd34d;
      pointer-events: none;
    }
    #status-overlay.hidden {
      display: none;
    }
    .maplibregl-ctrl-logo {
      display: none !important;
    }
  </style>
</head>
<body>
  <div id="map"></div>
  <div id="status-overlay">Offline kaart wordt geladen…</div>

  <script src="https://unpkg.com/maplibre-gl@3.6.2/dist/maplibre-gl.js"></script>
  <script>
    // Volledige style.json, direct als JS-object
    const style =
""" + style_json + """
    ;

    const statusOverlay = document.getElementById("status-overlay");
    const showStatus = (message) => {
      if (!statusOverlay) return;
      statusOverlay.textContent = message;
      statusOverlay.classList.remove("hidden");
    };
    const hideStatus = () => {
      if (!statusOverlay) return;
      statusOverlay.classList.add("hidden");
    };

    const zoomAroundCenter = (delta) => {
      if (!window.map) {
        return;
      }
      const nextZoom = window.map.getZoom() + delta;
      window.map.zoomTo(nextZoom, {
        around: window.map.getCenter(),
        duration: 0,
      });
    };
    window.zoomAroundMapCenter = zoomAroundCenter;

    // Kaart voor Europa
    window.map = new maplibregl.Map({
      container: "map",
      style: style,
      center: [10, 50],
      zoom: 3.5,
      minZoom: 3,
      maxZoom: 16,
      maxBounds: [
        [-25, 34],
        [45, 72]
      ]
    });

    // Scroll-wheel zoom altijd rond het midden houden voor een rustiger gevoel
    window.map.scrollZoom.disable();
    const mapCanvas = window.map.getCanvas();
    const handleCenteredScroll = (event) => {
      if (!window.map) {
        return;
      }
      event.preventDefault();
      let delta = -event.deltaY / 300;
      if (event.deltaMode === WheelEvent.DOM_DELTA_LINE) {
        delta *= 12;
      } else if (event.deltaMode === WheelEvent.DOM_DELTA_PAGE) {
        delta *= 60;
      }
      if (event.ctrlKey) {
        delta /= 2;
      }
      if (delta === 0) {
        return;
      }
      zoomAroundCenter(delta);
    };
    mapCanvas.addEventListener("wheel", handleCenteredScroll, { passive: false });

    window.map.on("load", function() {
      hideStatus();
      window.map.resize();
    });

    window.map.on("error", function(event) {
      console.error(event.error || event);
      showStatus("Kaartdata kon niet geladen worden. Controleer of de pmtiles-server draait op poort 8080.");
    });

    window.addEventListener("resize", function() {
      if (window.map) {
        window.map.resize();
      }
    });
  </script>
</body>
</html>
"""

        # BaseUrl is niet heel belangrijk hier, maar moet iets zijn
        self.webview.setHtml(html, QUrl("http://localhost/"))
        layout.addWidget(self.webview, 0, 0, 1, 2)

        # Info overlay
        meta = QLabel("Europa\ncenter 10°E, 50°N")
        meta.setStyleSheet("background:#111827; padding:8px; border-radius:8px;")
        layout.addWidget(meta, 0, 0, Qt.AlignTop | Qt.AlignLeft)

        # Zoomknoppen
        zoom_controls = QVBoxLayout()
        plus = QPushButton("+")
        minus = QPushButton("-")
        for btn in (plus, minus):
            btn.setFixedSize(32, 32)
            btn.setStyleSheet(
                "background:#111827; border-radius:8px; border:1px solid #1f2937;"
            )
            zoom_controls.addWidget(btn)
        zoom_controls.addStretch(1)
        layout.addLayout(zoom_controls, 0, 1, Qt.AlignTop | Qt.AlignRight)

        plus.clicked.connect(self.zoom_in)
        minus.clicked.connect(self.zoom_out)

        return area

    # ---------------------------------------------------------
    # Zoom-acties → JavaScript in WebView
    # ---------------------------------------------------------
    def zoom_in(self):
        if hasattr(self, "webview"):
            self.webview.page().runJavaScript(
                "if (window.zoomAroundMapCenter) { window.zoomAroundMapCenter(0.65); }"
            )

    def zoom_out(self):
        if hasattr(self, "webview"):
            self.webview.page().runJavaScript(
                "if (window.zoomAroundMapCenter) { window.zoomAroundMapCenter(-0.65); }"
            )
