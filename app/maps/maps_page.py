import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import requests

from PySide6.QtCore import Qt, QUrl, QObject, Signal, Slot
from PySide6.QtWidgets import (
    QHBoxLayout,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QGridLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
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

        self._active_contact_ids: Set[str] = set()
        self._block_contact_signals = False
        self._contacts_by_id: Dict[str, dict] = {}
        self._updating_select_all = False
        self._pending_contact_id_for_pin: Optional[str] = None

        content = QWidget()
        content_layout = QHBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(16)

        content_layout.addWidget(self._build_map_view(), 1)
        content_layout.addWidget(self._build_contacts_panel())

        self.webview.loadFinished.connect(self._handle_map_ready)

        layout.addWidget(content, 1)
        self._last_location: Optional[Dict[str, Any]] = None
        self._load_contacts_for_map()

    def _build_map_view(self) -> QFrame:
        area = QFrame()
        area.setObjectName("Card")
        layout = QGridLayout(area)
        layout.setContentsMargins(16, 16, 16, 16)

        self.webview = QWebEngineView()
        self._project_root = Path(__file__).resolve().parents[2]
        self._assets_dir = self._project_root / "app" / "frontend" / "assets"

        self.bridge = MapBridge(self)
        self.bridge.locationPinned.connect(self._on_location_pinned)
        self.web_channel = QWebChannel(self.webview.page())
        self.web_channel.registerObject("pyBridge", self.bridge)
        self.webview.page().setWebChannel(self.web_channel)

        style_path = Path(__file__).with_name("style.json")
        style_json = style_path.read_text(encoding="utf-8")

        css_inline = (self._assets_dir / "maplibre-gl.css").read_text(encoding="utf-8")
        js_inline = (self._assets_dir / "maplibre-gl.js").read_text(encoding="utf-8")

        html_template = f"""
<!DOCTYPE html>
<html lang=\"nl\">
<head>
  <meta charset=\"utf-8\" />
  <title>Offline Map (Europe)</title>
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />

  <style>
  /*__MAPLIBRE_CSS__*/
  </style>

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
    .loci-marker.contact {{
      background: #2563eb;
    }}
  </style>
</head>
<body>
  <div id=\"map\"></div>
  <div id=\"status-overlay\">Offline kaart wordt geladen…</div>

  <script>
  /*__MAPLIBRE_JS__*/
  </script>
  <script src=\"qrc:///qtwebchannel/qwebchannel.js\"></script>
  <script>
    const style =
{style_json}
    ;

    let pyBridge = null;
    let pendingPin = false;
    let activePinMarker = null;
    let contactMarkers = new Map();

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

    window.setActiveContacts = (contacts, focusId) => {{
      if (!window.map) {{
        return;
      }}
      const normalizeId = (value) => (value == null ? null : String(value));
      const active = Array.isArray(contacts) ? contacts : [];
      const nextIds = new Set(
        active
          .map((contact) => normalizeId(contact.id))
          .filter((value) => value !== null)
      );
      for (const [id, marker] of contactMarkers.entries()) {{
        if (!nextIds.has(id)) {{
          marker.remove();
          contactMarkers.delete(id);
        }}
      }}
      active.forEach((contact) => {{
        if (contact?.lat == null || contact?.lon == null) {{
          return;
        }}
        const contactId = normalizeId(contact.id);
        if (!contactId) {{
          return;
        }}
        let marker = contactMarkers.get(contactId);
        if (!marker) {{
          const el = document.createElement("button");
          el.className = "loci-marker contact";
          el.title = contact.name || contact.label || "Contact";
          marker = new maplibregl.Marker(el)
            .setLngLat([contact.lon, contact.lat])
            .addTo(window.map);
          if (contact.info) {{
            marker.setPopup(
              new maplibregl.Popup({{ offset: 18 }}).setText(contact.info)
            );
          }}
          contactMarkers.set(contactId, marker);
        }} else {{
          marker.setLngLat([contact.lon, contact.lat]);
        }}
      }});
      const focusKey = normalizeId(focusId);
      if (focusKey && nextIds.has(focusKey)) {{
        const focusContact = active.find(
          (c) => normalizeId(c.id) === focusKey
        );
        if (focusContact) {{
          window.map.easeTo({{
            center: [focusContact.lon, focusContact.lat],
            zoom: Math.max(window.map.getZoom(), 9),
            duration: 800,
          }});
          const marker = contactMarkers.get(focusKey);
          if (marker?.getPopup && marker.getPopup()) {{
            marker.getPopup().addTo(window.map);
          }}
        }}
      }}
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

        html = html_template.replace("/*__MAPLIBRE_CSS__*/", css_inline).replace(
            "/*__MAPLIBRE_JS__*/", js_inline
        )
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

    def _build_contacts_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("Card")
        panel.setFixedWidth(300)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        header = QHBoxLayout()
        title = QLabel("Contacten op kaart")
        title.setStyleSheet("font-weight:600;")
        header.addWidget(title)
        header.addStretch(1)
        reload = QPushButton("Herlaad")
        reload.setFixedSize(72, 28)
        reload.setToolTip("Herlaad contacten")
        reload.clicked.connect(self._load_contacts_for_map)
        header.addWidget(reload)
        layout.addLayout(header)

        self.contacts_hint = QLabel(
            "Selecteer welke contacten met opgeslagen locatie zichtbaar zijn op de kaart."
        )
        self.contacts_hint.setWordWrap(True)
        self.contacts_hint.setStyleSheet("color:#9ca3af; font-size:12px;")
        layout.addWidget(self.contacts_hint)

        self.select_all_checkbox = QCheckBox("Alle contacten tonen")
        self.select_all_checkbox.setTristate(True)
        self.select_all_checkbox.setEnabled(False)
        self.select_all_checkbox.stateChanged.connect(self._toggle_select_all)
        layout.addWidget(self.select_all_checkbox)

        self.contacts_empty = QLabel(
            "Nog geen contacten met GPS-coördinaten. Koppel een locatie om deze hier te tonen."
        )
        self.contacts_empty.setWordWrap(True)
        self.contacts_empty.setStyleSheet("color:#9ca3af; font-size:12px;")
        layout.addWidget(self.contacts_empty)

        self.contacts_list = QListWidget()
        self.contacts_list.setAlternatingRowColors(True)
        self.contacts_list.itemChanged.connect(self._handle_contact_toggle)
        layout.addWidget(self.contacts_list, 1)

        self.contacts_empty.hide()

        return panel

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

    def _handle_map_ready(self, _ok: bool) -> None:
        self._sync_contact_markers()

    def _start_pin_mode(self) -> None:
        if not hasattr(self, "webview"):
            return
        self.webview.page().runJavaScript(
            "if (window.enablePinMode) { window.enablePinMode(); }"
        )

    def _handle_contact_toggle(self, item: QListWidgetItem) -> None:
        if self._block_contact_signals:
            return
        contact = item.data(Qt.UserRole)
        if not contact:
            return
        contact_id_value = contact.get("id")
        if contact_id_value is None:
            return
        contact_id = str(contact_id_value)
        checked = item.checkState() == Qt.Checked
        if checked:
            self._active_contact_ids.add(contact_id)
        else:
            self._active_contact_ids.discard(contact_id)
        focus_id = contact_id if checked else None
        self._sync_contact_markers(focus_contact_id=focus_id)
        self._update_select_all_state()

    def _toggle_select_all(self, state: int) -> None:
        if self._updating_select_all:
            return
        if not hasattr(self, "contacts_list"):
            return
        if self.contacts_list.count() == 0:
            self._update_select_all_state()
            return
        if state == Qt.PartiallyChecked:
            return
        checked = state == Qt.Checked
        target_state = Qt.Checked if checked else Qt.Unchecked
        self._block_contact_signals = True
        for index in range(self.contacts_list.count()):
            item = self.contacts_list.item(index)
            item.setCheckState(target_state)
        self._block_contact_signals = False
        if checked:
            selected_ids: Set[str] = set()
            for index in range(self.contacts_list.count()):
                contact = self.contacts_list.item(index).data(Qt.UserRole) or {}
                contact_id_value = contact.get("id")
                if contact_id_value is not None:
                    selected_ids.add(str(contact_id_value))
            self._active_contact_ids = selected_ids
        else:
            self._active_contact_ids.clear()
        self._sync_contact_markers()
        self._update_select_all_state()

    def _update_select_all_state(self) -> None:
        if not hasattr(self, "select_all_checkbox") or not hasattr(
            self, "contacts_list"
        ):
            return
        total = self.contacts_list.count()
        checked = 0
        for index in range(self.contacts_list.count()):
            if self.contacts_list.item(index).checkState() == Qt.Checked:
                checked += 1
        if total == 0:
            state = Qt.Unchecked
            enabled = False
        elif checked == 0:
            state = Qt.Unchecked
            enabled = True
        elif checked == total:
            state = Qt.Checked
            enabled = True
        else:
            state = Qt.PartiallyChecked
            enabled = True
        self._updating_select_all = True
        self.select_all_checkbox.setEnabled(enabled)
        self.select_all_checkbox.setCheckState(state)
        self._updating_select_all = False

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

        preferred_contact_id = self._pending_contact_id_for_pin
        if preferred_contact_id is not None:
            for index in range(combo.count()):
                payload = combo.itemData(index)
                if not payload:
                    continue
                payload_id = payload.get("id")
                if payload_id is not None and str(payload_id) == preferred_contact_id:
                    combo.setCurrentIndex(index)
                    break

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
            self._pending_contact_id_for_pin = None

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

    def _load_contacts_for_map(self) -> None:
        contacts = self._fetch_contacts()
        geocoded = [
            contact
            for contact in contacts
            if contact.get("location_lat") is not None
            and contact.get("location_lon") is not None
        ]
        geocoded.sort(key=lambda person: (person.get("name") or "").lower())
        self._contacts_by_id = {}
        previous_selection = set(self._active_contact_ids)

        self._block_contact_signals = True
        self.contacts_list.clear()
        for person in geocoded:
            person_id_value = person.get("id")
            person_key = str(person_id_value) if person_id_value is not None else None
            if person_key:
                self._contacts_by_id[person_key] = person
            item = QListWidgetItem(self._contact_list_label(person))
            item.setData(Qt.UserRole, person)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            if person_key and person_key in previous_selection:
                item.setCheckState(Qt.Checked)
            else:
                item.setCheckState(Qt.Unchecked)
            tooltip = self._contact_tooltip(person)
            if tooltip:
                item.setToolTip(tooltip)
            self.contacts_list.addItem(item)
        self._block_contact_signals = False

        has_contacts = bool(geocoded)
        self.contacts_list.setVisible(has_contacts)
        self.contacts_empty.setVisible(not has_contacts)
        self._active_contact_ids = {
            person_id
            for person_id in previous_selection
            if person_id in self._contacts_by_id
        }
        self._update_select_all_state()
        self._sync_contact_markers()

    def _contact_list_label(self, contact: dict) -> str:
        name = contact.get("name") or "Onbekend"
        context_bits = [
            contact.get("location_label") or contact.get("location_street"),
            contact.get("location_city"),
            contact.get("location_country"),
        ]
        context = ", ".join([bit for bit in context_bits if bit])
        return f"{name}\n{context}" if context else name

    def _contact_tooltip(self, contact: dict) -> str:
        lat = contact.get("location_lat")
        lon = contact.get("location_lon")
        if lat is None or lon is None:
            return ""
        label = contact.get("location_label") or contact.get("location_city") or ""
        coords = f"GPS: {lat:.5f}, {lon:.5f}"
        return f"{label}\n{coords}" if label else coords

    def _contact_marker_payload(self, contact: dict) -> Optional[Dict[str, Any]]:
        contact_id_value = contact.get("id")
        if contact_id_value is None:
            return None
        try:
            lat = float(contact.get("location_lat"))
            lon = float(contact.get("location_lon"))
        except (TypeError, ValueError):
            return None
        name = contact.get("name") or "Contact"
        location_bits = [
            contact.get("location_label") or contact.get("location_street"),
            contact.get("location_city"),
            contact.get("location_country"),
        ]
        location_text = ", ".join([bit for bit in location_bits if bit])
        popup_text = name if not location_text else f"{name}\n{location_text}"
        return {
            "id": str(contact_id_value),
            "name": contact.get("name"),
            "label": contact.get("location_label"),
            "lat": lat,
            "lon": lon,
            "info": popup_text,
        }

    def _sync_contact_markers(self, *, focus_contact_id: Optional[str] = None) -> None:
        if not hasattr(self, "webview") or not hasattr(self, "contacts_list"):
            return
        active_payloads: List[Dict[str, Any]] = []
        for index in range(self.contacts_list.count()):
            item = self.contacts_list.item(index)
            if item.checkState() != Qt.Checked:
                continue
            contact = item.data(Qt.UserRole)
            payload = self._contact_marker_payload(contact or {})
            if payload:
                active_payloads.append(payload)
        contacts_json = json.dumps(active_payloads)
        focus_arg = "null" if focus_contact_id is None else json.dumps(focus_contact_id)
        script = (
            f"if (window.setActiveContacts) {{ window.setActiveContacts({contacts_json}, {focus_arg}); }}"
        )
        self.webview.page().runJavaScript(script)

    def _find_contact_item(self, contact_id: str) -> Optional[QListWidgetItem]:
        for index in range(self.contacts_list.count()):
            item = self.contacts_list.item(index)
            contact = item.data(Qt.UserRole) or {}
            contact_id_value = contact.get("id")
            if contact_id_value is None:
                continue
            if str(contact_id_value) == contact_id:
                return item
        return None

    def _set_contact_checked(self, contact_id: str, checked: bool) -> None:
        item = self._find_contact_item(contact_id)
        if not item:
            return
        state = Qt.Checked if checked else Qt.Unchecked
        if item.checkState() == state:
            return
        self._block_contact_signals = True
        item.setCheckState(state)
        self._block_contact_signals = False
        if checked:
            self._active_contact_ids.add(contact_id)
        else:
            self._active_contact_ids.discard(contact_id)

    def _append_contact_item(self, contact: dict) -> None:
        contact_id_value = contact.get("id")
        if contact_id_value is not None:
            self._contacts_by_id[str(contact_id_value)] = contact
        item = QListWidgetItem(self._contact_list_label(contact))
        item.setData(Qt.UserRole, contact)
        item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
        item.setCheckState(Qt.Unchecked)
        tooltip = self._contact_tooltip(contact)
        if tooltip:
            item.setToolTip(tooltip)
        self.contacts_list.addItem(item)
        self.contacts_list.show()
        self.contacts_empty.hide()
        self._update_select_all_state()

    def focus_on_contact(self, contact: dict) -> None:
        if not contact:
            return
        contact_id_value = contact.get("id")
        if contact_id_value is None:
            return
        contact_id = str(contact_id_value)
        if contact.get("location_lat") is None or contact.get("location_lon") is None:
            QMessageBox.information(
                self,
                "Geen locatie",
                "Dit contact heeft geen GPS-locatie om te tonen.",
            )
            return
        self._load_contacts_for_map()
        if self._find_contact_item(contact_id) is None:
            self._append_contact_item(contact)
        self._set_contact_checked(contact_id, True)
        item = self._find_contact_item(contact_id)
        if item:
            self.contacts_list.scrollToItem(item)
        self._sync_contact_markers(focus_contact_id=contact_id)

    def request_location_for_contact(self, contact: dict) -> None:
        if not contact:
            return
        contact_id_value = contact.get("id")
        if contact_id_value is None:
            QMessageBox.warning(
                self,
                "Contact onbekend",
                "Dit contact kan niet gekoppeld worden omdat het geen ID heeft.",
            )
            return
        contact_id = str(contact_id_value)
        lat = contact.get("location_lat")
        lon = contact.get("location_lon")
        if lat is not None and lon is not None:
            self.focus_on_contact(contact)
            return
        self._pending_contact_id_for_pin = contact_id
        name = contact.get("name") or "dit contact"
        QMessageBox.information(
            self,
            "Locatie koppelen",
            f"Selecteer op de kaart een locatie voor {name}.",
        )
        self._start_pin_mode()

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
