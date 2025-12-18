import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import requests

from PySide6.QtCore import (
    Qt,
    QUrl,
    QObject,
    QRect,
    QSize,
    Signal,
    Slot,
    QEvent,
    QModelIndex,
)
from PySide6.QtGui import QColor, QLinearGradient, QMouseEvent, QPainter, QPixmap
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
    QAbstractItemView,
    QStyledItemDelegate,
    QStyle,
    QStyleOptionViewItem,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineWidgets import QWebEngineView

from app.frontend.config import (
    BACKEND_HTTP,
    BACKEND_TIMEOUT,
    MAP_GLYPHS_URL,
    MAP_SPRITE_URL,
    PMTILES_STATUS_HINT,
    PMTILES_TILE_TEMPLATE,
)
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


class ContactListDelegate(QStyledItemDelegate):
    """Custom delegate to mimic the softer list cards from the Figma design."""

    def __init__(self, icon: QPixmap, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._icon = icon

    def sizeHint(self, option: QStyleOptionViewItem, index: QModelIndex):
        _ = option
        _ = index
        return QSize(0, 78)

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex):
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)

        contact = index.data(Qt.UserRole) or {}
        name = contact.get("name") or "Onbekend"
        context_bits = [
            contact.get("location_label") or contact.get("location_street"),
            contact.get("location_city"),
            contact.get("location_country"),
        ]
        meta = ", ".join([bit for bit in context_bits if bit]) or "Geen locatie-informatie"
        is_checked = index.data(Qt.CheckStateRole) == Qt.Checked

        container = option.rect.adjusted(8, 4, -8, -4)
        base_color = QColor("#ffffff")
        if is_checked:
            base_color = QColor("#fff4d6")
        elif option.state & QStyle.State_MouseOver:
            base_color = QColor("#f8fafc")
        painter.setBrush(base_color)
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(container, 20, 20)

        if option.state & QStyle.State_Selected:
            painter.setPen(QColor("#facc15"))
            painter.setBrush(Qt.NoBrush)
            painter.drawRoundedRect(container.adjusted(0, 0, -1, -1), 20, 20)
            painter.setPen(Qt.NoPen)

        indicator = self._checkbox_rect(container)
        painter.setBrush(QColor("#facc15") if is_checked else QColor("#e5e7eb"))
        painter.drawEllipse(indicator)
        if is_checked:
            inner = indicator.adjusted(6, 6, -6, -6)
            painter.setBrush(QColor("#111111"))
            painter.drawEllipse(inner)

        icon_rect = QRect(indicator.right() + 12, container.center().y() - 16, 32, 32)
        if not self._icon.isNull():
            painter.drawPixmap(icon_rect, self._icon)

        text_left = icon_rect.right() + 12
        text_width = max(0, container.right() - text_left - 12)
        name_rect = QRect(text_left, container.top() + 10, text_width, 24)
        meta_rect = QRect(text_left, container.bottom() - 28, text_width, 20)

        name_font = painter.font()
        name_font.setBold(True)
        name_font.setPointSize(11)
        painter.setFont(name_font)
        painter.setPen(QColor("#0f172a"))
        painter.drawText(name_rect, Qt.AlignLeft | Qt.AlignVCenter, name)

        meta_font = painter.font()
        meta_font.setBold(False)
        meta_font.setPointSize(9)
        painter.setFont(meta_font)
        painter.setPen(QColor("#6b7280"))
        painter.drawText(meta_rect, Qt.AlignLeft | Qt.AlignVCenter, meta)

        painter.restore()

    def editorEvent(self, event, model, option, index):
        if isinstance(event, QMouseEvent) and event.type() == QEvent.MouseButtonRelease:
            if event.button() == Qt.LeftButton:
                container = option.rect.adjusted(8, 4, -8, -4)
                pos = event.position().toPoint() if hasattr(event, "position") else event.pos()
                if self._checkbox_rect(container).contains(pos):
                    current = index.data(Qt.CheckStateRole) or Qt.Unchecked
                    next_state = Qt.Unchecked if current == Qt.Checked else Qt.Checked
                    return model.setData(index, next_state, Qt.CheckStateRole)
        return super().editorEvent(event, model, option, index)

    def _checkbox_rect(self, outer: QRect) -> QRect:
        size = 22
        x = outer.left() + 12
        y = outer.center().y() - size // 2
        return QRect(x, y, size, size)


class MapsPage(QWidget):
    contact_changed = Signal(str)

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
        self._contact_icon = self._build_contact_icon()
        self._contact_icon = self._build_contact_icon()

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

    def _build_contact_icon(self) -> QPixmap:
        size = 32
        pix = QPixmap(size, size)
        pix.fill(Qt.transparent)
        painter = QPainter(pix)
        painter.setRenderHint(QPainter.Antialiasing)

        gradient = QLinearGradient(0, 0, size, size)
        gradient.setColorAt(0, QColor("#f97316"))
        gradient.setColorAt(1, QColor("#f43f5e"))
        painter.setBrush(gradient)
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(0, 0, size, size)

        painter.setBrush(QColor("#ffffff"))
        painter.drawEllipse(size // 2 - 6, size // 2 - 6, 12, 12)
        painter.setBrush(QColor("#f97316"))
        painter.drawEllipse(size // 2 - 3, size // 2 - 3, 6, 6)

        painter.end()
        return pix

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
        raw_style = json.loads(style_path.read_text(encoding="utf-8"))
        raw_style["glyphs"] = MAP_GLYPHS_URL
        raw_style["sprite"] = MAP_SPRITE_URL
        try:
            raw_style["sources"]["protomaps"]["tiles"] = [PMTILES_TILE_TEMPLATE]
        except (KeyError, TypeError):
            pass
        style_json = json.dumps(raw_style)
        tile_hint = PMTILES_STATUS_HINT

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
    const tileErrorHint = {json.dumps(tile_hint)};

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
      showStatus(tileErrorHint);
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
        meta.setObjectName("MapMeta")
        layout.addWidget(meta, 0, 0, Qt.AlignTop | Qt.AlignLeft)

        controls_box = QFrame()
        controls_box.setObjectName("MapControls")
        controls_layout = QVBoxLayout(controls_box)
        controls_layout.setContentsMargins(12, 12, 12, 12)
        controls_layout.setSpacing(10)

        plus = QPushButton("+")
        minus = QPushButton("-")
        for btn in (plus, minus):
            btn.setFixedSize(44, 44)
            btn.setObjectName("MapZoomButton")
            btn.setCursor(Qt.PointingHandCursor)
            controls_layout.addWidget(btn)

        controls_layout.addStretch(1)

        self.pin_button = QPushButton("Voeg locatie toe")
        self.pin_button.setObjectName("MapPrimaryButton")
        self.pin_button.setFixedHeight(46)
        self.pin_button.setCursor(Qt.PointingHandCursor)
        self.pin_button.clicked.connect(self._start_pin_mode)
        controls_layout.addWidget(self.pin_button)

        layout.addWidget(controls_box, 0, 1, Qt.AlignTop | Qt.AlignRight)

        plus.clicked.connect(self.zoom_in)
        minus.clicked.connect(self.zoom_out)

        return area

    def _build_contacts_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("Card")
        panel.setFixedWidth(320)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(18)

        header = QVBoxLayout()
        title = QLabel("Locaties")
        title.setObjectName("ContactPanelTitle")
        header.addWidget(title)
        subtitle = QLabel("Bekijk contactlocaties op de kaart")
        subtitle.setObjectName("ContactPanelSubtitle")
        header.addWidget(subtitle)
        layout.addLayout(header)

        filter_row = QHBoxLayout()
        self.select_all_checkbox = QCheckBox("Alle contacten tonen")
        self.select_all_checkbox.setObjectName("ContactSelectAll")
        self.select_all_checkbox.setTristate(True)
        self.select_all_checkbox.setEnabled(False)
        self.select_all_checkbox.stateChanged.connect(self._toggle_select_all)
        filter_row.addWidget(self.select_all_checkbox, 1)
        reload = QPushButton("Herlaad")
        reload.setObjectName("ContactReloadButton")
        reload.setFixedHeight(36)
        reload.setToolTip("Herlaad contacten")
        reload.clicked.connect(self._load_contacts_for_map)
        filter_row.addWidget(reload)
        layout.addLayout(filter_row)

        self.contacts_empty = QLabel(
            "Nog geen contacten met GPS-coördinaten. Koppel een locatie om deze hier te tonen."
        )
        self.contacts_empty.setWordWrap(True)
        self.contacts_empty.setObjectName("ContactEmptyState")
        layout.addWidget(self.contacts_empty)

        self.contacts_list = QListWidget()
        self.contacts_list.setObjectName("ContactList")
        self.contacts_list.setAlternatingRowColors(False)
        self.contacts_list.setSpacing(6)
        self.contacts_list.setMouseTracking(True)
        self.contacts_list.setSelectionMode(QAbstractItemView.SingleSelection)
        self.contacts_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.contacts_list.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self._contacts_delegate = ContactListDelegate(self._contact_icon, self.contacts_list)
        self.contacts_list.setItemDelegate(self._contacts_delegate)
        self.contacts_list.itemChanged.connect(self._handle_contact_toggle)
        self.contacts_list.currentItemChanged.connect(
            lambda *_: self._update_contact_action_state()
        )
        layout.addWidget(self.contacts_list, 1)

        actions = QGridLayout()
        actions.setHorizontalSpacing(12)
        actions.setVerticalSpacing(10)
        actions.setColumnStretch(0, 1)
        actions.setColumnStretch(1, 1)
        self.edit_contact_btn = QPushButton("Bewerk contact")
        self.pin_contact_btn = QPushButton("Nieuwe locatie pinnen")
        self.clear_location_btn = QPushButton("Verwijder locatie")
        self.delete_contact_btn = QPushButton("Verwijder contact")
        self.edit_contact_btn.setObjectName("ContactSecondaryButton")
        self.pin_contact_btn.setObjectName("ContactSecondaryButton")
        self.clear_location_btn.setObjectName("ContactSecondaryButton")
        self.delete_contact_btn.setObjectName("ContactDangerButton")
        self.edit_contact_btn.clicked.connect(self._edit_selected_contact)
        self.pin_contact_btn.clicked.connect(self._pin_selected_contact)
        self.clear_location_btn.clicked.connect(self._clear_selected_location)
        self.delete_contact_btn.clicked.connect(self._delete_selected_contact)
        actions.addWidget(self.edit_contact_btn, 0, 0)
        actions.addWidget(self.pin_contact_btn, 0, 1)
        actions.addWidget(self.clear_location_btn, 1, 0)
        actions.addWidget(self.delete_contact_btn, 1, 1)
        layout.addLayout(actions)
        for button in (
            self.edit_contact_btn,
            self.pin_contact_btn,
            self.clear_location_btn,
            self.delete_contact_btn,
        ):
            button.setEnabled(False)

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

    def _load_contacts_for_map(self, focus_contact_id: Optional[str] = None) -> None:
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
        if focus_contact_id:
            self._set_contact_checked(focus_contact_id, True)
            item = self._find_contact_item(focus_contact_id)
            if item:
                self.contacts_list.setCurrentItem(item)
                self.contacts_list.scrollToItem(item)
        self._update_contact_action_state()

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

    def _selected_contact(self) -> Optional[dict]:
        if not hasattr(self, "contacts_list"):
            return None
        item = self.contacts_list.currentItem()
        return item.data(Qt.UserRole) if item else None

    def _update_contact_action_state(self) -> None:
        contact = self._selected_contact()
        has_contact = contact is not None
        has_location = bool(
            contact
            and contact.get("location_lat") is not None
            and contact.get("location_lon") is not None
        )
        for button in (
            getattr(self, "edit_contact_btn", None),
            getattr(self, "pin_contact_btn", None),
            getattr(self, "delete_contact_btn", None),
        ):
            if button:
                button.setEnabled(has_contact)
        if getattr(self, "clear_location_btn", None):
            self.clear_location_btn.setEnabled(has_location)

    def _edit_selected_contact(self) -> None:
        contact = self._selected_contact()
        if not contact:
            return
        contact_id = contact.get("id")
        if contact_id is None:
            return
        dialog = ContactFormDialog(self, title="Contact bewerken", initial=contact)
        if dialog.exec() != QDialog.Accepted:
            return
        payload = dialog.payload()
        mode = dialog.save_mode()
        try:
            resp = requests.patch(
                f"{BACKEND_HTTP}/contacts/{contact_id}",
                json=payload,
                timeout=BACKEND_TIMEOUT,
            )
            resp.raise_for_status()
            updated = resp.json()
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Fout",
                f"Contact kon niet worden bijgewerkt:\n{exc}",
            )
            return
        contact_key = str(contact_id)
        self.contact_changed.emit(contact_key)
        self._load_contacts_for_map(focus_contact_id=contact_key)
        if mode == "save_and_map":
            self.request_location_for_contact(updated, force_pin=True)

    def _pin_selected_contact(self) -> None:
        contact = self._selected_contact()
        if not contact:
            return
        self.request_location_for_contact(contact, force_pin=True)

    def _clear_selected_location(self) -> None:
        contact = self._selected_contact()
        if not contact:
            return
        contact_id = contact.get("id")
        if contact_id is None:
            return
        confirm = QMessageBox.question(
            self,
            "Locatie verwijderen",
            "Weet je zeker dat je de locatie voor dit contact wilt verwijderen?",
        )
        if confirm != QMessageBox.Yes:
            return
        payload = {
            "location_label": None,
            "location_street": None,
            "location_city": None,
            "location_region": None,
            "location_country": None,
            "location_context": None,
            "location_lat": None,
            "location_lon": None,
        }
        try:
            resp = requests.patch(
                f"{BACKEND_HTTP}/contacts/{contact_id}",
                json=payload,
                timeout=BACKEND_TIMEOUT,
            )
            resp.raise_for_status()
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Fout",
                f"Locatie kon niet worden verwijderd:\n{exc}",
            )
            return
        contact_key = str(contact_id)
        self.contact_changed.emit(contact_key)
        self._load_contacts_for_map(focus_contact_id=contact_key)

    def _delete_selected_contact(self) -> None:
        contact = self._selected_contact()
        if not contact:
            return
        contact_id = contact.get("id")
        if contact_id is None:
            return
        confirm = QMessageBox.question(
            self,
            "Contact verwijderen",
            f"Weet je zeker dat je {contact.get('name', 'dit contact')} wilt verwijderen?",
        )
        if confirm != QMessageBox.Yes:
            return
        try:
            resp = requests.delete(
                f"{BACKEND_HTTP}/contacts/{contact_id}",
                timeout=BACKEND_TIMEOUT,
            )
            resp.raise_for_status()
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Fout",
                f"Contact kon niet worden verwijderd:\n{exc}",
            )
            return
        self.contact_changed.emit(str(contact_id))
        self._load_contacts_for_map()

    def handle_external_contact_change(self, contact_id: Optional[str]) -> None:
        self._load_contacts_for_map(focus_contact_id=contact_id)

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

    def request_location_for_contact(self, contact: dict, force_pin: bool = False) -> None:
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
        if lat is not None and lon is not None and not force_pin:
            self.focus_on_contact(contact)
            return
        self._pending_contact_id_for_pin = contact_id
        name = contact.get("name") or "dit contact"
        if force_pin:
            message = f"Selecteer op de kaart een nieuwe locatie voor {name}."
        else:
            message = f"Selecteer op de kaart een locatie voor {name}."
        QMessageBox.information(self, "Locatie koppelen", message)
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
        contact_id = contact.get("id")
        if contact_id is not None:
            contact_key = str(contact_id)
            self.contact_changed.emit(contact_key)
            self._load_contacts_for_map(focus_contact_id=contact_key)

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
            created = resp.json()
            contact_id = created.get("id")
            if contact_id is not None:
                self.contact_changed.emit(str(contact_id))
            return created
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Fout",
                f"Contact kon niet aangemaakt worden:\n{exc}",
            )
            return None
