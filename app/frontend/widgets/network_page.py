from __future__ import annotations

import os
from pathlib import Path

import psutil
import requests
from PySide6.QtCore import Qt, QProcess, QTimer
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
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

        self._resource_heading = QLabel(t("network_resources_title"))
        self._resource_heading.setStyleSheet("font-size:18px; font-weight:800; color:#111111;")
        layout.addWidget(self._resource_heading)

        self.resource_cards = {}
        self._resource_headings = {}
        resources_row = QHBoxLayout()
        resources_row.setSpacing(16)
        for key, heading_key, caption_key in [
            ("ram_now", "network_ram_now", "network_ram_caption"),
            ("cpu_now", "network_cpu_now", "network_cpu_caption"),
            ("power_now", "network_power_now", "network_power_caption"),
        ]:
            card, metric_label, caption_label, heading_label = self._build_stat_card(
                t(heading_key), t("network_na"), t(caption_key)
            )
            self._resource_headings[key] = {
                "heading_key": heading_key,
                "caption_key": caption_key,
                "heading_label": heading_label,
            }
            self.resource_cards[key] = {
                "metric": metric_label,
                "caption": caption_label,
            }
            resources_row.addWidget(card)
        layout.addLayout(resources_row)

        self._performance_card = self._card()
        performance_layout = QVBoxLayout(self._performance_card)
        performance_layout.setContentsMargins(20, 18, 20, 18)
        performance_layout.setSpacing(14)

        self._performance_title = QLabel(t("network_performance_title"))
        self._performance_title.setStyleSheet("font-size:16px; font-weight:800; color:#111111;")
        performance_layout.addWidget(self._performance_title)

        self._performance_caption = QLabel(t("network_performance_caption"))
        self._performance_caption.setStyleSheet("color:#6b7280; font-size:12px;")
        self._performance_caption.setWordWrap(True)
        performance_layout.addWidget(self._performance_caption)

        self._performance_bars: dict[str, dict[str, QWidget | QLabel]] = {}
        for key, label_key in [
            ("ram", "network_ram_now"),
            ("cpu", "network_cpu_now"),
            ("power", "network_power_now"),
        ]:
            row = self._build_usage_bar(t(label_key))
            self._performance_bars[key] = row
            performance_layout.addLayout(row["layout"])

        layout.addWidget(self._performance_card)

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
        self._refresh_timer = QTimer(self)
        self._refresh_timer.setInterval(5000)
        self._refresh_timer.timeout.connect(self._reload)
        self._refresh_timer.start()
        self._reload()

        register_language_change_callback(self._update_translations)

    def _update_translations(self) -> None:
        """Update UI elements when language changes."""
        self._wifi_button.setText(t("network_open_wifi_config"))
        for key, data in self._stat_headings.items():
            data["heading_label"].setText(t(data["heading_key"]))
        self._resource_heading.setText(t("network_resources_title"))
        for key, data in self._resource_headings.items():
            data["heading_label"].setText(t(data["heading_key"]))
        self._performance_title.setText(t("network_performance_title"))
        self._performance_caption.setText(t("network_performance_caption"))
        self._update_stats([])
        self._update_resource_stats()

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

    def _build_usage_bar(self, label: str) -> dict[str, QWidget | QLabel]:
        layout = QGridLayout()
        layout.setHorizontalSpacing(12)
        layout.setVerticalSpacing(4)

        title = QLabel(label)
        title.setStyleSheet("font-weight:700; color:#111111;")
        value = QLabel(t("network_na"))
        value.setStyleSheet("font-weight:700; color:#111111;")
        value.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        track = QFrame()
        track.setFixedHeight(10)
        track.setStyleSheet("background:#f3f4f6; border-radius:5px;")
        track_layout = QHBoxLayout(track)
        track_layout.setContentsMargins(0, 0, 0, 0)
        fill = QFrame()
        fill.setFixedHeight(10)
        fill.setMinimumWidth(8)
        fill.setStyleSheet("background:#facc15; border-radius:5px;")
        track_layout.addWidget(fill, 0)
        track_layout.addStretch(1)

        detail = QLabel("")
        detail.setStyleSheet("color:#6b7280; font-size:12px;")
        detail.setWordWrap(True)

        layout.addWidget(title, 0, 0)
        layout.addWidget(value, 0, 1)
        layout.addWidget(track, 1, 0, 1, 2)
        layout.addWidget(detail, 2, 0, 1, 2)

        return {
            "layout": layout,
            "title": title,
            "value": value,
            "track": track,
            "fill": fill,
            "detail": detail,
        }

    def _set_usage_bar(self, key: str, percent: float | None, value_text: str, detail_text: str) -> None:
        bar = self._performance_bars[key]
        safe_percent = 0 if percent is None else max(0, min(100, int(percent)))
        track_width = 280
        fill_width = max(8, int(track_width * (safe_percent / 100))) if percent is not None else 8
        fill = bar["fill"]
        assert isinstance(fill, QFrame)
        fill.setFixedWidth(fill_width)
        if percent is None:
            fill.setStyleSheet("background:#d1d5db; border-radius:5px;")
        elif safe_percent >= 85:
            fill.setStyleSheet("background:#ef4444; border-radius:5px;")
        elif safe_percent >= 65:
            fill.setStyleSheet("background:#f59e0b; border-radius:5px;")
        else:
            fill.setStyleSheet("background:#facc15; border-radius:5px;")
        value = bar["value"]
        detail = bar["detail"]
        assert isinstance(value, QLabel)
        assert isinstance(detail, QLabel)
        value.setText(value_text)
        detail.setText(detail_text)

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
        self._update_resource_stats()

    @staticmethod
    def _linux_power_now_watts() -> float | None:
        base = Path("/sys/class/power_supply")
        if not base.exists():
            return None
        for entry in base.iterdir():
            try:
                type_value = (entry / "type").read_text(encoding="utf-8").strip().lower()
            except OSError:
                continue
            if type_value != "battery":
                continue
            for filename, divisor in (("power_now", 1_000_000), ("current_now", 1_000_000)):
                path = entry / filename
                if not path.exists():
                    continue
                try:
                    raw_value = float(path.read_text(encoding="utf-8").strip())
                except (OSError, ValueError):
                    continue
                if filename == "power_now":
                    return raw_value / divisor
                voltage_path = entry / "voltage_now"
                if voltage_path.exists():
                    try:
                        voltage = float(voltage_path.read_text(encoding="utf-8").strip()) / 1_000_000
                    except (OSError, ValueError):
                        continue
                    return (raw_value / divisor) * voltage
        return None

    def _device_power_now_watts(self) -> float | None:
        return self._linux_power_now_watts()

    def _update_resource_stats(self) -> None:
        memory = psutil.virtual_memory()
        cpu_percent = psutil.cpu_percent(interval=None)
        ram_label = f"{memory.used / (1024**3):.1f} / {memory.total / (1024**3):.1f} GB"
        ram_caption = t("network_ram_caption", percent=int(memory.percent))
        cpu_label = f"{cpu_percent:.0f}%"
        cpu_caption = t("network_cpu_caption")

        watts = self._device_power_now_watts()
        if watts is None:
            power_label = t("network_na")
            power_caption = t("network_power_unavailable")
        else:
            power_label = f"{watts:.1f} W".replace(".", ",")
            power_caption = t("network_power_live")

        self.resource_cards["ram_now"]["metric"].setText(ram_label)
        self.resource_cards["ram_now"]["caption"].setText(ram_caption)
        self.resource_cards["cpu_now"]["metric"].setText(cpu_label)
        self.resource_cards["cpu_now"]["caption"].setText(cpu_caption)
        self.resource_cards["power_now"]["metric"].setText(power_label)
        self.resource_cards["power_now"]["caption"].setText(power_caption)
        self._set_usage_bar("ram", memory.percent, ram_label, ram_caption)
        self._set_usage_bar("cpu", cpu_percent, cpu_label, cpu_caption)
        power_percent = None if watts is None else min(100.0, (watts / 65.0) * 100.0)
        self._set_usage_bar("power", power_percent, power_label, power_caption)

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
