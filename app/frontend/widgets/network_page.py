from __future__ import annotations

import os
import platform
from pathlib import Path

import psutil
import requests
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
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
NETWORK_HISTORY_LIMIT = 50


class SparklineWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._points: list[float] = []
        self._y_labels = ("", "", "")
        self._x_labels = ("Eerder", "Nu")
        self._empty_message = ""
        self.setMinimumHeight(92)
        self.setMaximumHeight(92)

    def set_series(
        self,
        points: list[float],
        *,
        y_labels: tuple[str, str, str],
        x_labels: tuple[str, str] = ("Eerder", "Nu"),
        empty_message: str = "",
    ) -> None:
        self._points = points[-NETWORK_HISTORY_LIMIT:]
        self._y_labels = y_labels
        self._x_labels = x_labels
        self._empty_message = empty_message
        self.update()

    def paintEvent(self, event):  # noqa: N802
        del event
        if len(self._points) < 2:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        label_color = QColor("#9ca3af")
        grid_color = QColor("#ececec")
        line_color = QColor("#facc15")
        point_color = QColor("#eab308")

        left_pad = 42
        right_pad = 10
        top_pad = 8
        bottom_pad = 22
        rect = self.rect().adjusted(left_pad, top_pad, -right_pad, -bottom_pad)
        min_value = min(self._points)
        max_value = max(self._points)
        is_flat = abs(max_value - min_value) < 1e-6
        span = max(max_value - min_value, 1e-6)
        step_x = rect.width() / max(1, len(self._points) - 1)

        painter.setPen(QPen(grid_color, 1))
        for fraction in (0.0, 0.5, 1.0):
            y = rect.bottom() - fraction * rect.height()
            painter.drawLine(rect.left(), int(y), rect.right(), int(y))

        painter.setPen(label_color)
        font = painter.font()
        font.setPointSize(8)
        painter.setFont(font)
        painter.drawText(4, rect.top() + 6, 34, 12, Qt.AlignRight | Qt.AlignVCenter, self._y_labels[0])
        painter.drawText(4, rect.center().y() - 6, 34, 12, Qt.AlignRight | Qt.AlignVCenter, self._y_labels[1])
        painter.drawText(4, rect.bottom() - 6, 34, 12, Qt.AlignRight | Qt.AlignVCenter, self._y_labels[2])
        painter.drawText(rect.left(), rect.bottom() + 6, 40, 14, Qt.AlignLeft | Qt.AlignVCenter, self._x_labels[0])
        painter.drawText(rect.right() - 28, rect.bottom() + 6, 28, 14, Qt.AlignRight | Qt.AlignVCenter, self._x_labels[1])

        if self._empty_message:
            painter.drawText(rect, Qt.AlignCenter, self._empty_message)
            return

        path = QPainterPath()
        plot_points: list[tuple[float, float]] = []
        for index, value in enumerate(self._points):
            normalized = 0.5 if is_flat else (value - min_value) / span
            x = rect.left() + index * step_x
            y = rect.bottom() - normalized * rect.height()
            plot_points.append((x, y))
            if index == 0:
                path.moveTo(x, y)
            else:
                path.lineTo(x, y)

        painter.setPen(QPen(line_color, 2.5, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        painter.drawPath(path)
        painter.setPen(Qt.NoPen)
        painter.setBrush(point_color)
        for x, y in plot_points:
            painter.drawEllipse(int(x - 2.5), int(y - 2.5), 5, 5)


class NetworkStatusPage(QWidget):
    open_settings_tab_requested = Signal(str)

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
            card, metric_label, caption_label, heading_label, chart_widget, _ = self._build_stat_card(
                t(heading_key), t("network_na"), t(caption_key), with_chart=True
            )
            self._stat_headings[key] = {"heading_key": heading_key, "caption_key": caption_key, "heading_label": heading_label}
            self.stats_cards[key] = {
                "metric": metric_label,
                "caption": caption_label,
                "chart": chart_widget,
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
            card, metric_label, caption_label, heading_label, _, usage_bar = self._build_stat_card(
                t(heading_key), t("network_na"), t(caption_key), with_chart=False, with_usage_bar=True
            )
            self._resource_headings[key] = {
                "heading_key": heading_key,
                "caption_key": caption_key,
                "heading_label": heading_label,
            }
            self.resource_cards[key] = {
                "metric": metric_label,
                "caption": caption_label,
                "bar": usage_bar,
            }
            resources_row.addWidget(card)
        layout.addLayout(resources_row)

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
        self._update_stats([])
        self._update_resource_stats()

    def _build_stat_card(self, title: str, value: str, caption: str, *, with_chart: bool, with_usage_bar: bool = False):
        card = self._card()
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 16, 20, 16)
        card_layout.setSpacing(8)
        heading = QLabel(title)
        heading.setStyleSheet("color:#6b7280; letter-spacing:0.2em; font-size:11px;")
        if with_usage_bar:
            heading.setFixedHeight(20)
            heading.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        metric = QLabel(value)
        metric.setStyleSheet("font-size:32px; font-weight:800;")
        if with_usage_bar:
            metric.setMinimumWidth(230)
            metric.setFixedHeight(60)
            metric.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        chart = SparklineWidget() if with_chart else None
        usage_bar = self._build_inline_usage_bar() if with_usage_bar else None
        detail = QLabel(caption)
        detail.setStyleSheet("color:#6b7280; font-size:12px;")
        detail.setWordWrap(True)
        card_layout.addWidget(heading)
        card_layout.addWidget(metric)
        if chart is not None:
            card_layout.addWidget(chart)
        if usage_bar is not None:
            card_layout.addWidget(usage_bar["track"])
        card_layout.addWidget(detail)
        return card, metric, detail, heading, chart, usage_bar

    @staticmethod
    def _card():
        card = QFrame()
        card.setObjectName("Card")
        return card

    def _build_inline_usage_bar(self) -> dict[str, QWidget]:
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

        return {
            "track": track,
            "fill": fill,
        }

    def _set_usage_bar(self, key: str, percent: float | None) -> None:
        bar = self.resource_cards[key]["bar"]
        assert isinstance(bar, dict)
        safe_percent = 0 if percent is None else max(0, min(100, int(percent)))
        track = bar["track"]
        assert isinstance(track, QFrame)
        track_width = max(40, track.width() if track.width() > 0 else 260)
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
        self._update_stat_history_charts()

    def _update_stat_history_charts(self) -> None:
        history = self._fetch_stats_history()
        samples = history.get("samples", []) if isinstance(history, dict) else []
        if not isinstance(samples, list):
            samples = []

        series_map = {
            "requests_today": [],
            "active_users": [],
            "avg_response": [],
        }
        for sample in samples[-NETWORK_HISTORY_LIMIT:]:
            series_map["requests_today"].append(float(sample.get("requests_today") or 0))
            series_map["active_users"].append(float(sample.get("active_users_today") or 0))
            series_map["avg_response"].append(float(sample.get("avg_response_ms") or 0))

        for key, points in series_map.items():
            has_real_data = any(point > 0 for point in points)
            if not points:
                points = [0.0, 0.0]
            min_value = min(points)
            max_value = max(points)
            mid_value = (min_value + max_value) / 2
            chart = self.stats_cards[key]["chart"]
            assert isinstance(chart, SparklineWidget)
            chart.set_series(
                points,
                y_labels=(
                    self._format_chart_value(key, max_value),
                    self._format_chart_value(key, mid_value),
                    self._format_chart_value(key, min_value),
                ),
                x_labels=("Eerder", "Nu"),
                empty_message="" if has_real_data else t("network_no_measurements"),
            )

    def _format_chart_value(self, key: str, value: float) -> str:
        if key == "avg_response":
            return f"{int(round(value))} ms"
        return str(int(round(value)))

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

    @staticmethod
    def _battery_info() -> dict[str, object] | None:
        try:
            battery = psutil.sensors_battery()
        except Exception:
            battery = None
        if battery is None:
            return None
        return {
            "percent": float(battery.percent),
            "plugged": bool(battery.power_plugged),
        }

    @staticmethod
    def _linux_power_source() -> str | None:
        base = Path("/sys/class/power_supply")
        if not base.exists():
            return None
        found_battery = False
        for entry in base.iterdir():
            try:
                type_value = (entry / "type").read_text(encoding="utf-8").strip().lower()
            except OSError:
                continue
            if type_value == "battery":
                found_battery = True
                continue
            if type_value not in {"mains", "usb", "usb_c", "usb_pd"}:
                continue
            try:
                online = (entry / "online").read_text(encoding="utf-8").strip()
            except OSError:
                online = ""
            if online == "1":
                if type_value == "mains":
                    return t("network_power_source_ac")
                if type_value in {"usb", "usb_c", "usb_pd"}:
                    return t("network_power_source_usb")
        if found_battery:
            return t("network_power_source_battery")
        return None

    @staticmethod
    def _generic_power_source(battery: dict[str, object] | None) -> str:
        system_name = platform.system().lower()
        if system_name == "linux":
            source = NetworkStatusPage._linux_power_source()
            if source:
                return source
        if battery is None:
            return t("network_power_source_unknown")
        return (
            t("network_power_source_ac")
            if bool(battery.get("plugged"))
            else t("network_power_source_battery")
        )

    def _update_resource_stats(self) -> None:
        memory = psutil.virtual_memory()
        cpu_percent = psutil.cpu_percent(interval=None)
        ram_label = f"{memory.used / (1024**3):.1f} / {memory.total / (1024**3):.1f} GB"
        ram_caption = t("network_ram_caption", percent=int(memory.percent))
        cpu_label = f"{cpu_percent:.0f}%"
        cpu_caption = t("network_cpu_caption")

        watts = self._device_power_now_watts()
        battery = self._battery_info()
        if battery is not None:
            power_label = f"{int(round(float(battery['percent'])))}%"
        elif watts is not None:
            power_label = f"{watts:.1f} W".replace(".", ",")
        else:
            power_label = t("network_na")

        charging_text = t("network_power_plugged_yes") if battery and bool(battery.get("plugged")) else (
            t("network_power_plugged_no") if battery else t("network_power_unknown_short")
        )
        battery_text = (
            f"{int(round(float(battery['percent'])))}%"
            if battery is not None
            else t("network_power_no_battery")
        )
        source_text = self._generic_power_source(battery)
        watt_text = f"{watts:.1f} W".replace(".", ",") if watts is not None else t("network_power_unknown_short")
        power_caption = "\n".join(
            [
                t("network_power_battery_line", value=battery_text),
                t("network_power_plugged_line", value=charging_text),
                t("network_power_source_line", value=source_text),
                t("network_power_live_line", value=watt_text),
            ]
        )

        self.resource_cards["ram_now"]["metric"].setText(ram_label)
        self.resource_cards["ram_now"]["caption"].setText(ram_caption)
        self.resource_cards["cpu_now"]["metric"].setText(cpu_label)
        self.resource_cards["cpu_now"]["caption"].setText(cpu_caption)
        self.resource_cards["power_now"]["metric"].setText(power_label)
        self.resource_cards["power_now"]["caption"].setText(power_caption)
        self._set_usage_bar("ram_now", memory.percent)
        self._set_usage_bar("cpu_now", cpu_percent)
        power_percent = None if watts is None else min(100.0, (watts / 65.0) * 100.0)
        if battery is not None:
            power_percent = float(battery["percent"])
        self._set_usage_bar("power_now", power_percent)

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

    def _fetch_stats_history(self):
        try:
            resp = requests.get(
                f"{API_BASE}/api/stats/history",
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
        self.open_settings_tab_requested.emit("wifi")
