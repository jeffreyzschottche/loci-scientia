import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

from PySide6.QtCore import Qt, QUrl, QObject, Signal, Slot
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QGridLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineWidgets import QWebEngineView

from app.frontend.config import BACKEND_HTTP, BACKEND_TIMEOUT
from app.frontend.widgets.contact_form import ContactFormDialog


class MapBridge(QObject):
    locationPinned = Signal(float, float, dict)

    @Slot(float, float, str)
    def handlePinnedLocation(self, lon: float, lat: float, info_json: str) -> None:
        try:
            info = json.loads(info_json) if info_json else {}
        except json.JSONDecodeError:
            info = {}
        info.setdefault("lon", lon)
        info.setdefault("lat", lat)
        self.locationPinned.emit(lon, lat, info)


class MapsPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._build_map_view(), 1)
        self._last_location: Optional[Dict[str, Any]] = None

    def _build_map_view(self) -> QFrame:
        area = QFrame()
        area.setObjectName("Card")
        layout = QGridLayout(area)
        layout.setContentsMargins(16, 16, 16, 16)

        self.webview = QWebEngineView()

        self.bridge = MapBridge(self)
        self.bridge.locationPinned.connect(self._on_location_pinned)
        self.web_channel = QWebChannel(self.webview.page())
        self.web_channel.registerObject("pyBridge", self.bridge)
        self.webview.page().setWebChannel(self.web_channel)

        style_path = Path(__file__).with_name("style.json")
        style_json = style_path.read_text(encoding="utf-8")

        html = f"""
<!DOCTYPE html>
<html lang=\"nl\">
<head>
  <meta charset=\"utf-8\" />
  <title>Offline Map (Europe)</title>
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />

  <link
    rel=\"stylesheet\"
    href=\"https://unpkg.com/maplibre-gl@3.6.2/dist/maplibre-gl.css\"
  />

  <style>
    html, body {{
      margin: 0;
      padding: 0;
      height: 100%;
      width: 100%;
      background: #020617;
    }}
    #map {{
      position: absolute;
      inset: 0;
    }}
    #status-overlay {{
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
    }}
    #status-overlay.hidden {{
      display: none;
    }}
    .maplibregl-ctrl-logo {{
      display: none !important;
    }}
    .loci-marker {{
      width: 16px;
      height: 16px;
      border-radius: 50%;
      border: 2px solid white;
      background: #f97316;
      cursor: pointer;
      box-shadow: 0 0 8px rgba(0, 0, 0, 0.65);
    }}
  </style>
</head>
<body>
  <div id=\"map\"></div>
  <div id=\"status-overlay\">Offline kaart wordt geladen…</div>

  <script src=\"https://unpkg.com/maplibre-gl@3.6.2/dist/maplibre-gl.js\"></script>
  <script src=\"qrc:///qtwebchannel/qwebchannel.js\"></script>
  <script>
    const style =
{style_json}
    ;

    let pyBridge = null;
    let pendingPin = false;
    let activePinMarker = null;

    const statusOverlay = document.getElementById("status-overlay");
    const showStatus = (message) => {{
      if (!statusOverlay) return;
      statusOverlay.textContent = message;
      statusOverlay.classList.remove("hidden");
    }};
    const hideStatus = () => {{
      if (!statusOverlay) return;
      statusOverlay.classList.add("hidden");
    }};

    const setPinMarker = (lngLat) => {{
      if (activePinMarker) {{
        activePinMarker.remove();
      }}
      const el = document.createElement("button");
      el.className = "loci-marker";
      activePinMarker = new maplibregl.Marker(el).setLngLat(lngLat).addTo(window.map);
    }};

    const describeLocation = (event) => {{
      const layers = [
        "roads_labels_major",
        "roads_labels_minor",
        "places_subplace",
        "places_locality",
        "places_region",
        "places_country"
      ];
      const features = window.map.queryRenderedFeatures(event.point, {{ layers }});
      const pick = (ids) => features.find((feat) => ids.includes(feat.layer.id));
      const road = pick(["roads_labels_major", "roads_labels_minor"]);
      const locality = pick(["places_subplace", "places_locality"]);
      const region = pick(["places_region"]);
      const country = pick(["places_country"]);
      const info = {{}};
      info.street = road?.properties?.name || null;
      info.city = locality?.properties?.name || null;
      info.region = region?.properties?.name || null;
      info.country = country?.properties?.name || locality?.properties?.country || null;
      info.label = info.street || info.city || info.region || info.country || "Gelabelde locatie";
      info.context = [info.city, info.region, info.country].filter(Boolean).join(", ");
      return info;
    }};

    const zoomAroundCenter = (delta) => {{
      if (!window.map) {{
        return;
      }}
      const nextZoom = window.map.getZoom() + delta;
      window.map.zoomTo(nextZoom, {{
        around: window.map.getCenter(),
        duration: 0,
      }});
    }};
    window.zoomAroundMapCenter = zoomAroundCenter;

    window.enablePinMode = () => {{
      if (!window.map) return;
      pendingPin = true;
      showStatus("Klik op de kaart om een locatie te pinnen…");
    }};

    const datasetBounds = [
      [-25, 34],
      [45, 72]
    ];
    const datasetCenter = [10, 50];

    window.map = new maplibregl.Map({{
      container: "map",
      style: style,
      center: datasetCenter,
      zoom: 3.5,
      minZoom: 3,
      maxZoom: 16,
      maxBounds: datasetBounds
    }});

    window.map.scrollZoom.disable();
    const mapCanvas = window.map.getCanvas();
    const handleCenteredScroll = (event) => {{
      if (!window.map) {{
        return;
      }}
      event.preventDefault();
      let delta = -event.deltaY / 300;
      if (event.deltaMode === WheelEvent.DOM_DELTA_LINE) {{
        delta *= 12;
      }} else if (event.deltaMode === WheelEvent.DOM_DELTA_PAGE) {{
        delta *= 60;
      }}
      if (event.ctrlKey) {{
        delta /= 2;
      }}
      if (delta === 0) {{
        return;
      }}
      zoomAroundCenter(delta);
    }};
    mapCanvas.addEventListener("wheel", handleCenteredScroll, {{ passive: false }});

    window.map.once("load", function() {{
      hideStatus();
      window.map.resize();
    }});

    window.map.on("error", function(event) {{
      console.error(event.error || event);
      showStatus("Kaartdata kon niet geladen worden. Controleer of de pmtiles-server draait op poort 8080.");
    }});

    const initBridge = () => {{
      if (window.qt && window.qt.webChannelTransport) {{
        new QWebChannel(window.qt.webChannelTransport, function(channel) {{
          pyBridge = channel.objects.pyBridge;
        }});
      }}
    }};

    window.map.on("click", function(event) {{
      if (!pendingPin) {{
        return;
      }}
      pendingPin = false;
      hideStatus();
      const info = describeLocation(event);
      info.lat = event.lngLat.lat;
      info.lon = event.lngLat.lng;
      setPinMarker(event.lngLat);
      if (pyBridge && pyBridge.handlePinnedLocation) {{
        pyBridge.handlePinnedLocation(event.lngLat.lng, event.lngLat.lat, JSON.stringify(info));
      }}
    }});

    window.addEventListener("resize", function() {{
      if (window.map) {{
        window.map.resize();
      }}
    }});

    initBridge();
  </script>
</body>
</html>
"""

        self.webview.setHtml(html, QUrl("http://localhost/"))
        layout.addWidget(self.webview, 0, 0, 1, 2)

        meta = QLabel("Europa\ncenter 10°E, 50°N")
        meta.setStyleSheet("background:#111827; padding:8px; border-radius:8px;")
        layout.addWidget(meta, 0, 0, Qt.AlignTop | Qt.AlignLeft)

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

        self.pin_button = QPushButton("Voeg locatie toe")
        self.pin_button.setStyleSheet(
            "background:#f97316; color:white; border-radius:8px; padding:8px;"
        )
        self.pin_button.clicked.connect(self._start_pin_mode)
        zoom_controls.addWidget(self.pin_button)

        layout.addLayout(zoom_controls, 0, 1, Qt.AlignTop | Qt.AlignRight)

        plus.clicked.connect(self.zoom_in)
        minus.clicked.connect(self.zoom_out)

        return area

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

    def _start_pin_mode(self) -> None:
        if not hasattr(self, "webview"):
            return
        self.webview.page().runJavaScript(
            "if (window.enablePinMode) { window.enablePinMode(); }"
        )

    def _on_location_pinned(self, lon: float, lat: float, info: Dict[str, Any]) -> None:
        self._last_location = {
            "lon": lon,
            "lat": lat,
            "label": info.get("label"),
            "street": info.get("street"),
            "city": info.get("city"),
            "region": info.get("region"),
            "country": info.get("country"),
            "context": info.get("context"),
        }
        self._open_location_dialog()

    def _open_location_dialog(self) -> None:
        location = self._last_location or {}
        contacts = self._fetch_contacts()

        dialog = QDialog(self)
        dialog.setWindowTitle("Locatie koppelen aan contact")
        form = QFormLayout(dialog)
        form.setContentsMargins(16, 16, 16, 16)
        form.setSpacing(12)

        label = location.get("label") or location.get("street") or "Onbekende locatie"
        city = location.get("city")
        country = location.get("country")
        summary_text = label
        if city or country:
            summary_text = f"{label} — {', '.join([bit for bit in [city, country] if bit])}"
        summary = QLabel(summary_text)
        summary.setWordWrap(True)
        form.addRow("Locatie", summary)

        lat = location.get("lat")
        lon = location.get("lon")
        if lat is not None and lon is not None:
            coords_value = f"{lat:.5f}, {lon:.5f}"
        else:
            coords_value = "Onbekend"
        coords = QLabel(coords_value)
        form.addRow("GPS", coords)

        combo = QComboBox()
        combo.addItem("Selecteer contact", None)
        for person in contacts:
            combo.addItem(person.get("name", "Onbekend"), person)
        form.addRow("Contact", combo)

        new_btn = QPushButton("Nieuw contact…")
        form.addRow(new_btn)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        form.addRow(buttons)

        def create_new_contact() -> None:
            contact = self._create_contact_with_location(location)
            if contact:
                combo.addItem(contact.get("name", "Onbekend"), contact)
                combo.setCurrentIndex(combo.count() - 1)

        def save_location() -> None:
            selected = combo.currentData()
            if selected is None:
                QMessageBox.warning(dialog, "Geen contact", "Selecteer een contact.")
                return
            dialog.done(1)
            self._update_contact_location(selected, location)

        new_btn.clicked.connect(create_new_contact)
        buttons.accepted.connect(save_location)
        buttons.rejected.connect(dialog.reject)

        dialog.exec()

    def _fetch_contacts(self) -> List[dict]:
        try:
            resp = requests.get(f"{BACKEND_HTTP}/contacts", timeout=BACKEND_TIMEOUT)
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Fout",
                f"Kon contacten niet laden:\n{exc}",
            )
            return []

    def _location_payload(self, location: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "location_label": location.get("label") or location.get("street"),
            "location_street": location.get("street"),
            "location_city": location.get("city"),
            "location_region": location.get("region"),
            "location_country": location.get("country"),
            "location_context": location.get("context"),
            "location_lat": location.get("lat"),
            "location_lon": location.get("lon"),
        }

    def _update_contact_location(self, contact: dict, location: Dict[str, Any]) -> None:
        payload = self._location_payload(location)
        try:
            resp = requests.patch(
                f"{BACKEND_HTTP}/contacts/{contact['id']}",
                json=payload,
                timeout=BACKEND_TIMEOUT,
            )
            resp.raise_for_status()
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Fout",
                f"Locatie kon niet opgeslagen worden:\n{exc}",
            )
            return

        QMessageBox.information(
            self,
            "Locatie opgeslagen",
            f"Locatie is gekoppeld aan {contact.get('name', 'contact')}.",
        )

    def _create_contact_with_location(self, location: Dict[str, Any]) -> Optional[dict]:
        dialog = ContactFormDialog(
            self,
            location_defaults={
                "label": location.get("label"),
                "street": location.get("street"),
                "city": location.get("city"),
                "region": location.get("region"),
                "country": location.get("country"),
                "lat": location.get("lat"),
                "lon": location.get("lon"),
            },
        )
        if dialog.exec() != QDialog.Accepted:
            return None

        payload = dialog.payload()
        try:
            resp = requests.post(
                f"{BACKEND_HTTP}/contacts",
                json=payload,
                timeout=BACKEND_TIMEOUT,
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Fout",
                f"Contact kon niet aangemaakt worden:\n{exc}",
            )
            return None
