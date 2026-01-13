import requests
from datetime import datetime
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QPlainTextEdit,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ..config import (
    API_ROUTES_DEFAULT_PORT,
    BACKEND_BEARER_TOKEN,
    BACKEND_HTTP,
    DEVICE_MDNS,
    PUBLIC_BASE_URL,
)
from .dialog_style import MODAL_QSS, show_error_dialog

API_BASE = BACKEND_HTTP


class ApiDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Nieuwe API Route")
        self.setStyleSheet(MODAL_QSS)
        wrapper = QVBoxLayout(self)
        wrapper.setContentsMargins(0, 0, 0, 0)
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QScrollArea.NoFrame)
        wrapper.addWidget(scroll_area)
        form_host = QWidget()
        scroll_area.setWidget(form_host)
        form = QFormLayout(form_host)
        form.setContentsMargins(24, 24, 24, 24)
        self.name = QLineEdit()
        self.method = QComboBox()
        self.method.addItems(["GET", "POST", "PUT", "DELETE"])
        self.path = QLineEdit("/api/example")
        self.port = QSpinBox()
        self.port.setRange(1, 65535)
        self.port.setValue(API_ROUTES_DEFAULT_PORT)
        self.kb = QLineEdit("Algemene Kennisbank")
        self.api_key = QLineEdit("aitje_sk_xxx")

        form.addRow("Naam", self.name)
        form.addRow("Methode", self.method)
        form.addRow("Pad", self.path)
        form.addRow("Port", self.port)
        form.addRow("Kennisbank", self.kb)
        form.addRow("API Key", self.api_key)

        buttons = QHBoxLayout()
        save = QPushButton("Opslaan")
        cancel = QPushButton("Annuleren")
        save.clicked.connect(self.accept)
        cancel.clicked.connect(self.reject)
        buttons.addWidget(save)
        buttons.addWidget(cancel)
        form.addRow(buttons)

    def payload(self) -> dict:
        return {
            "name": self.name.text(),
            "method": self.method.currentText(),
            "path": self.path.text(),
            "port": int(self.port.value()),
            "knowledge_base": self.kb.text() or None,
            "api_key": self.api_key.text() or None,
            "active": True,
        }


class ApiPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        self.stats_cards = []
        stats_row = QHBoxLayout()
        stats_row.setSpacing(16)
        for heading, caption in [
            ("Vandaag", "+12% vs gisteren"),
            ("Deze week", "+8% vs vorige week"),
            ("Deze maand", "+15% vs vorige maand"),
            ("Actieve keys", "van 10 mogelijk"),
        ]:
            card, metric_label, caption_label = self._build_stat_card(
                heading, "0", caption
            )
            self.stats_cards.append(
                {"metric": metric_label, "caption": caption_label, "title": heading}
            )
            stats_row.addWidget(card)
        layout.addLayout(stats_row)

        self.chart_card = self._card()
        chart_layout = QVBoxLayout(self.chart_card)
        chart_layout.setContentsMargins(20, 16, 20, 20)
        chart_layout.setSpacing(12)
        chart_title = QLabel("API Verkeer vandaag")
        chart_title.setStyleSheet("font-size:18px; font-weight:700;")
        chart_layout.addWidget(chart_title)
        self.chart_placeholder = QFrame()
        self.chart_placeholder.setMinimumHeight(220)
        self.chart_placeholder.setStyleSheet(
            "background:#f9fafb; border:1px solid #f2f2f2; border-radius:18px;"
        )
        chart_layout.addWidget(self.chart_placeholder)
        layout.addWidget(self.chart_card)

        self.keys_card = self._card()
        keys_layout = QVBoxLayout(self.keys_card)
        keys_layout.setContentsMargins(20, 20, 20, 20)
        keys_layout.setSpacing(16)

        keys_header = QHBoxLayout()
        keys_title = QLabel("API Keys")
        keys_title.setStyleSheet("font-size:20px; font-weight:700;")
        keys_sub = QLabel("Toegangssleutels per omgeving")
        keys_sub.setStyleSheet("color:#9ca3af; letter-spacing:0.08em;")
        title_group = QVBoxLayout()
        title_group.setContentsMargins(0, 0, 0, 0)
        title_group.setSpacing(2)
        title_group.addWidget(keys_title)
        title_group.addWidget(keys_sub)
        keys_header.addLayout(title_group)
        keys_header.addStretch(1)
        new_key = QPushButton("Nieuwe key aanmaken")
        new_key.setCursor(Qt.PointingHandCursor)
        new_key.setStyleSheet(
            "QPushButton { background:#facc15; color:#050505; padding:10px 26px;"
            "border-radius:20px; font-weight:600; }"
            "QPushButton:hover { background:#050505; color:#facc15; }"
        )
        new_key.setFixedHeight(40)
        new_key.clicked.connect(self._add_route)
        keys_header.addWidget(new_key)
        keys_layout.addLayout(keys_header)

        self.keys_list = QVBoxLayout()
        self.keys_list.setContentsMargins(0, 0, 0, 0)
        self.keys_list.setSpacing(12)
        keys_layout.addLayout(self.keys_list)

        self.doc_card = self._card()
        doc_layout = QVBoxLayout(self.doc_card)
        doc_layout.setContentsMargins(20, 20, 20, 20)
        doc_layout.setSpacing(12)
        doc_title = QLabel("API Documentatie")
        doc_title.setStyleSheet("font-size:20px; font-weight:700;")
        doc_header = QHBoxLayout()
        doc_header.addWidget(doc_title)
        doc_header.addStretch(1)
        url_button = QPushButton("Toon API URL")
        url_button.setCursor(Qt.PointingHandCursor)
        url_button.setStyleSheet(
            "QPushButton { border:1px solid #d1d5db; border-radius:18px; padding:6px 16px; }"
            "QPushButton:hover { border-color:#111111; }"
        )
        url_button.clicked.connect(self._show_url_hint)
        doc_header.addWidget(url_button)
        doc_layout.addLayout(doc_header)
        endpoint_label = QLabel("Publieke endpoints (mDNS):")
        endpoint_label.setStyleSheet("color:#6b7280; font-weight:600;")
        endpoint_value = QLabel(
            f"{PUBLIC_BASE_URL}/api/v1/signon\n{PUBLIC_BASE_URL}/api/v1/ask"
        )
        endpoint_value.setStyleSheet(
            "font-family:'SFMono-Regular','Menlo','Courier New',monospace; font-size:13px;"
        )
        endpoint_value.setTextInteractionFlags(Qt.TextSelectableByMouse)
        mdns_hint = QLabel(f"Device hostname: {DEVICE_MDNS}")
        mdns_hint.setStyleSheet("color:#4b5563;")
        example_label = QLabel("Voorbeeld request")
        example_label.setStyleSheet("color:#6b7280; font-weight:600;")
        example = QPlainTextEdit()
        example.setReadOnly(True)
        example.setPlainText(
            f"# 1) Bearer token ophalen (3 maanden geldig)\n"
            f"curl -X POST {PUBLIC_BASE_URL}/api/v1/signon \\\n"
            '  -H "Content-Type: application/json" \\\n'
            "  -d '{\n"
            '    \"user_name\": \"<gebruikersnaam>\",\n'
            '    \"password\": \"<wachtwoord>\"\n'
            "  }'\n\n"
            "# 2) Vraag stellen met Authorization header\n"
            f"curl -X POST {PUBLIC_BASE_URL}/api/v1/ask \\\n"
            '  -H "Authorization: Bearer <token>" \\\n'
            '  -H "Content-Type: application/json" \\\n'
            "  -d '{\n"
            '    \"prompt\": \"Hoi vanaf mijn telefoon\"\n'
            "  }'\n"
        )
        doc_layout.addWidget(endpoint_label)
        doc_layout.addWidget(endpoint_value)
        doc_layout.addWidget(mdns_hint)
        doc_layout.addWidget(example_label)
        doc_layout.addWidget(example)
        layout.addWidget(self.keys_card)
        layout.addWidget(self.doc_card)

        self._reload()

    def _build_stat_card(self, title: str, value: str, caption: str):
        card = self._card()
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 16, 20, 16)
        card_layout.setSpacing(6)
        heading = QLabel(title)
        heading.setStyleSheet("color:#6b7280; letter-spacing:0.2em; font-size:11px;")
        metric = QLabel(value)
        metric.setStyleSheet("font-size:32px; font-weight:800;")
        detail = QLabel(caption)
        detail.setStyleSheet("color:#16a34a; font-size:12px;")
        card_layout.addWidget(heading)
        card_layout.addWidget(metric)
        card_layout.addWidget(detail)
        return card, metric, detail

    @staticmethod
    def _card():
        card = QFrame()
        card.setObjectName("Card")
        return card

    def _clear_layout(self, layout: QVBoxLayout):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def _render_empty_state(self, message: str):
        placeholder = QLabel(message)
        placeholder.setStyleSheet("color:#9ca3af; font-style:italic;")
        placeholder.setAlignment(Qt.AlignCenter)
        placeholder.setMinimumHeight(80)
        self.keys_list.addWidget(placeholder)

    def _render_route(self, route: dict):
        entry = QFrame()
        entry.setStyleSheet("background:#fdfdfd; border:none; border-radius:18px;")
        row = QHBoxLayout(entry)
        row.setContentsMargins(16, 12, 16, 12)
        row.setSpacing(16)

        icon = QLabel("🔐")
        icon.setFixedSize(40, 40)
        icon.setAlignment(Qt.AlignCenter)
        row.addWidget(icon, 0, Qt.AlignTop)

        info = QVBoxLayout()
        info.setSpacing(4)
        name = QLabel(route.get("name", "Onbekende route"))
        name.setStyleSheet("font-size:16px; font-weight:600;")
        details = QLabel(
            f"{route.get('method', 'POST')} {route.get('path', '')}  •  Port {route.get('port', '-')}"
        )
        details.setStyleSheet("color:#6b7280;")
        info.addWidget(name)
        info.addWidget(details)
        info.addWidget(
            QLabel(
                f"Laatst gebruikt: {datetime.now().strftime('%d-%m-%Y, %H:%M')}  •  API Key: {route.get('api_key') or '-'}"
            )
        )
        row.addLayout(info, 1)

        actions = QVBoxLayout()
        actions.setSpacing(6)
        is_active = bool(route.get("active"))
        status = QLabel("Actief" if is_active else "Inactief")
        active_styles = ("#fef9c3", "#facc15", "#111111")
        inactive_styles = ("#f5f5f5", "#d4d4d8", "#6b7280")
        bg, border, text_color = active_styles if is_active else inactive_styles
        status.setAlignment(Qt.AlignCenter)
        status.setStyleSheet(
            f"background:{bg}; border:1px solid {border}; border-radius:14px;"
            f"padding:4px 16px; color:{text_color}; font-weight:600;"
        )
        status.setFixedHeight(28)
        actions.addWidget(status, 0, Qt.AlignRight)

        buttons = QHBoxLayout()
        edit = QPushButton("Bewerken")
        edit.setCursor(Qt.PointingHandCursor)
        edit.setStyleSheet(
            "QPushButton { border:1px solid #d4d4d8; border-radius:20px; padding:6px 18px; }"
            "QPushButton:hover { border-color:#111111; }"
        )
        edit.setFixedHeight(40)
        delete = QPushButton("Verwijderen")
        delete.setCursor(Qt.PointingHandCursor)
        delete.setStyleSheet(
            "QPushButton { background:#111111; color:#ffffff; border-radius:20px; padding:6px 18px; }"
            "QPushButton:hover { background:#facc15; color:#050505; }"
        )
        delete.setFixedHeight(40)
        edit.clicked.connect(lambda _=False, rid=route["id"]: self._edit_route(rid))
        delete.clicked.connect(lambda _=False, rid=route["id"]: self._delete_route(rid))
        buttons.addWidget(edit)
        buttons.addWidget(delete)
        actions.addLayout(buttons)
        row.addLayout(actions)

        self.keys_list.addWidget(entry)

    def _update_stats(self, count: int, active: int):
        today = str(300 + count * 7)
        week = f"{2.4 + count * 0.1:.1f}k"
        month = f"{19 + count * 0.2:.1f}k"
        active_caption = f"{active} van 10 mogelijk"
        values = [today, week, month, str(active)]
        captions = [
            "+12% vs gisteren",
            "+8% vs vorige week",
            "+15% vs vorige maand",
            active_caption,
        ]
        for idx, card in enumerate(self.stats_cards):
            card["metric"].setText(values[idx])
            card["caption"].setText(captions[idx])

    def _reload(self):
        self._clear_layout(self.keys_list)
        try:
            resp = requests.get(
                f"{API_BASE}/routes",
                timeout=3,
                headers=self._auth_headers(),
            )
            resp.raise_for_status()
        except requests.RequestException as exc:  # pragma: no cover - UI feedback only
            self._render_empty_state(f"Kan routes niet laden: {exc}")
            return

        if not resp.content.strip():
            data = []
        else:
            try:
                data = resp.json()
            except ValueError:  # pragma: no cover - UI feedback only
                self._render_empty_state("Kan routes niet laden: ongeldige JSON.")
                return

        if not isinstance(data, list):  # pragma: no cover - UI feedback only
            self._render_empty_state("Kan routes niet laden: onverwacht antwoordtype.")
            return

        if not data:
            self._render_empty_state("Nog geen API keys ingesteld.")
        else:
            for route in data:
                self._render_route(route)

        active = sum(1 for route in data if route.get("active"))
        self._update_stats(len(data), active)

    def _add_route(self):
        dialog = ApiDialog(self)
        if dialog.exec():
            try:
                requests.post(
                    f"{API_BASE}/routes",
                    json=dialog.payload(),
                    timeout=3,
                    headers=self._auth_headers(),
                )
                self._reload()
            except Exception as exc:
                show_error_dialog(self, "Fout", str(exc))

    def _edit_route(self, rid: str):
        try:
            requests.patch(
                f"{API_BASE}/routes/{rid}",
                json={"active": True},
                timeout=3,
                headers=self._auth_headers(),
            )
            self._reload()
        except Exception as exc:
            show_error_dialog(self, "Fout", str(exc))

    def _delete_route(self, rid: str):
        try:
            requests.delete(
                f"{API_BASE}/routes/{rid}",
                timeout=3,
                headers=self._auth_headers(),
            )
            self._reload()
        except Exception as exc:
            show_error_dialog(self, "Fout", str(exc))

    @staticmethod
    def _auth_headers() -> dict:
        if BACKEND_BEARER_TOKEN:
            return {"Authorization": f"Bearer {BACKEND_BEARER_TOKEN}"}
        return {}

    def _show_url_hint(self):
        curl_cmd = (
            f"# Haal token op\n"
            f"curl -X POST {PUBLIC_BASE_URL}/api/v1/signon \\\n"
            '  -H "Content-Type: application/json" \\\n'
            "  -d '{\"user_name\":\"<naam>\",\"password\":\"<wachtwoord>\"}'\n\n"
            "# Stel vraag met Authorization header\n"
            f"curl -X POST {PUBLIC_BASE_URL}/api/v1/ask \\\n"
            '  -H "Authorization: Bearer <token>" \\\n'
            '  -H "Content-Type: application/json" \\\n'
            "  -d '{\"prompt\":\"Hoi vanaf mijn telefoon\"}'"
        )
        body = [
            f"Basis-URL: {PUBLIC_BASE_URL}",
            f"Sign-on endpoint: {PUBLIC_BASE_URL}/api/v1/signon",
            f"Ask endpoint: {PUBLIC_BASE_URL}/api/v1/ask",
            "",
            "Gebruik dit voorbeeld vanaf de client:",
        ]
        self._show_styled_popup("API URL", body, curl_cmd)

    def _show_styled_popup(self, title: str, lines: list[str], code_block: str):
        dialog = QDialog(self)
        dialog.setWindowTitle(title)
        dialog.setStyleSheet(MODAL_QSS)
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)
        for line in lines:
            label = QLabel(line)
            label.setWordWrap(True)
            layout.addWidget(label)
        code = QPlainTextEdit()
        code.setReadOnly(True)
        code.setPlainText(code_block)
        code.setStyleSheet("font-family:'SFMono-Regular','Menlo','Courier New',monospace;")
        layout.addWidget(code)
        close_btn = QPushButton("Sluiten")
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn, 0, Qt.AlignRight)
        dialog.exec()
