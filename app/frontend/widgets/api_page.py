import requests
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..config import (
    BACKEND_BEARER_TOKEN,
    BACKEND_HTTP,
    DEVICE_MDNS,
    PUBLIC_BASE_URL,
)
from .dialog_style import OverlayDialog

API_BASE = BACKEND_HTTP


class ApiPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        self.stats_cards = {}
        stats_row = QHBoxLayout()
        stats_row.setSpacing(16)
        for key, heading, caption in [
            ("requests_today", "TOTAAL VANDAAG", "Hoe vaak de API is gebruikt."),
            ("active_users", "ACTIEVE GEBRUIKERS", "Aantal klanten of apps vandaag."),
            ("avg_response", "GEM. REACTIETIJD", "Gemiddelde wachttijd."),
        ]:
            card, metric_label, caption_label = self._build_stat_card(
                heading, "n.v.t.", caption
            )
            self.stats_cards[key] = {
                "metric": metric_label,
                "caption": caption_label,
            }
            stats_row.addWidget(card)
        layout.addLayout(stats_row)

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
        detail.setStyleSheet("color:#6b7280; font-size:12px;")
        card_layout.addWidget(heading)
        card_layout.addWidget(metric)
        card_layout.addWidget(detail)
        return card, metric, detail

    @staticmethod
    def _card():
        card = QFrame()
        card.setObjectName("Card")
        return card

    def _update_stats(self, routes: list[dict]):
        def fmt_int(value: int) -> str:
            return f"{value:,}".replace(",", ".")

        total_requests = None
        avg_response_ms = None
        active_users = None

        stats = self._fetch_stats()
        if stats:
            if isinstance(stats.get("requests_today"), int):
                total_requests = stats["requests_today"]
            if isinstance(stats.get("active_users_today"), int):
                active_users = stats["active_users_today"]
            avg_response_ms = stats.get("avg_response_ms")
            if isinstance(avg_response_ms, int):
                avg_response_ms = float(avg_response_ms)
            if not isinstance(avg_response_ms, (int, float)):
                avg_response_ms = None

        if total_requests is None:
            request_values = [
                route.get("requests_today")
                for route in routes
                if isinstance(route.get("requests_today"), (int, float))
            ]
            if request_values:
                total_requests = int(sum(request_values))

        if avg_response_ms is None:
            response_values = [
                route.get("avg_response_ms")
                for route in routes
                if isinstance(route.get("avg_response_ms"), (int, float))
            ]
            if response_values:
                avg_response_ms = sum(response_values) / len(response_values)

        if active_users is None:
            active_ids = []
            for route in routes:
                if route.get("active"):
                    key = route.get("api_key") or route.get("id")
                    if key:
                        active_ids.append(key)
            active_users = len(set(active_ids))

        if avg_response_ms is None:
            avg_label = "n.v.t."
            avg_caption = "Nog geen metingen."
        elif avg_response_ms >= 1000:
            avg_label = f"{avg_response_ms / 1000:.1f}s".replace(".", ",")
            avg_caption = "Gemiddelde wachttijd."
        else:
            avg_label = f"{int(avg_response_ms)} ms"
            avg_caption = "Gemiddelde wachttijd."

        if total_requests is None:
            req_label = "n.v.t."
            req_caption = "Nog geen metingen."
        else:
            req_label = fmt_int(total_requests)
            req_caption = "Hoe vaak de API is gebruikt."

        active_caption = "Aantal klanten of apps vandaag."

        self.stats_cards["requests_today"]["metric"].setText(req_label)
        self.stats_cards["requests_today"]["caption"].setText(req_caption)
        self.stats_cards["active_users"]["metric"].setText(str(active_users))
        self.stats_cards["active_users"]["caption"].setText(active_caption)
        self.stats_cards["avg_response"]["metric"].setText(avg_label)
        self.stats_cards["avg_response"]["caption"].setText(avg_caption)

    def _reload(self):
        self._update_stats([])

    def _fetch_stats(self):
        try:
            resp = requests.get(
                f"{API_BASE}/api/stats",
                timeout=3,
                headers=self._auth_headers(),
            )
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, dict):
                return data
        except requests.RequestException:
            return None
        except ValueError:
            return None
        return None

    def showEvent(self, event):
        super().showEvent(event)
        self._update_stats([])

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
        dialog = OverlayDialog(self)
        dialog.setWindowTitle(title)
        layout = dialog.card_layout
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
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setFixedSize(120, 36)
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn, 0, Qt.AlignCenter)
        dialog.exec()
