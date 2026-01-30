import requests
from PySide6.QtCore import Qt, QProcess
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..config import BACKEND_BEARER_TOKEN, BACKEND_HTTP
from ..translations import t, register_language_change_callback

API_BASE = BACKEND_HTTP


class NetworkStatusPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        self.stats_cards = {}
        self._stat_headings = {}
        stats_row = QHBoxLayout()
        stats_row.setSpacing(16)
        for key, heading_key, caption_key in [
            ("requests_today", "network_total_today", "network_api_usage"),
            ("active_users", "network_active_users", "network_customers_apps"),
            ("avg_response", "network_avg_response_time", "network_avg_wait_time"),
        ]:
            card, metric_label, caption_label, heading_label = self._build_stat_card(
                t(heading_key), t("network_na"), t(caption_key)
            )
            self._stat_headings[key] = {"heading_key": heading_key, "caption_key": caption_key, "heading_label": heading_label}
            self.stats_cards[key] = {
                "metric": metric_label,
                "caption": caption_label,
            }
            stats_row.addWidget(card)
        layout.addLayout(stats_row)

        layout.addStretch(1)

        self._wifi_button = QPushButton(t("network_open_wifi_config"))
        self._wifi_button.setFixedHeight(56)
        self._wifi_button.setStyleSheet(
            "QPushButton {"
            "  background:#facc15;"
            "  color:#050505;"
            "  border-radius:24px;"
            "  padding:8px 28px;"
            "  font-weight:700;"
            "  font-size:16px;"
            "}"
            "QPushButton:hover { background:#050505; color:#facc15; }"
        )
        self._wifi_button.clicked.connect(self._open_wifi_settings)
        layout.addWidget(self._wifi_button, 0, Qt.AlignCenter)
        layout.addStretch(1)
        self._reload()

        register_language_change_callback(self._update_translations)

    def _update_translations(self) -> None:
        """Update UI elements when language changes."""
        self._wifi_button.setText(t("network_open_wifi_config"))
        for key, data in self._stat_headings.items():
            data["heading_label"].setText(t(data["heading_key"]))
        self._update_stats([])

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
        return card, metric, detail, heading

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
            avg_label = t("network_na")
            avg_caption = t("network_no_measurements")
        elif avg_response_ms >= 1000:
            avg_label = f"{avg_response_ms / 1000:.1f}s".replace(".", ",")
            avg_caption = t("network_avg_wait_time")
        else:
            avg_label = f"{int(avg_response_ms)} ms"
            avg_caption = t("network_avg_wait_time")

        if total_requests is None:
            req_label = t("network_na")
            req_caption = t("network_no_measurements")
        else:
            req_label = fmt_int(total_requests)
            req_caption = t("network_api_usage")

        active_caption = t("network_customers_apps")

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

    def _open_wifi_settings(self):
        if QProcess.startDetached("iwgtk"):
            return
        if QProcess.startDetached("x-terminal-emulator", ["-e", "nmtui"]):
            return
        if QProcess.startDetached("gnome-terminal", ["--", "nmtui"]):
            return
        QProcess.startDetached("xterm", ["-e", "nmtui"])
