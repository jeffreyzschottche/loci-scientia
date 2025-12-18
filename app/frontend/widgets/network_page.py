import platform
import socket
import time

import psutil
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


def _format_bytes(num: float) -> str:
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if num < 1024.0:
            return f"{num:.1f} {unit}"
        num /= 1024.0
    return f"{num:.1f} PB"


class NetworkStatusPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        header = QHBoxLayout()
        title = QLabel("Netwerk Status")
        title.setStyleSheet("font-size:28px; font-weight:800; letter-spacing:0.02em;")
        header.addWidget(title)
        header.addStretch(1)
        refresh = QPushButton("Vernieuwen")
        refresh.clicked.connect(self.refresh_stats)
        refresh.setStyleSheet(
            "QPushButton {"
            "  color:#111111;"
            "  border:1px solid rgba(33,33,33,0.2);"
            "  border-radius:999px;"
            "  padding:8px 24px;"
            "  background:transparent;"
            "}"
            "QPushButton:hover { border-color: rgba(33,33,33,0.45); }"
        )
        header.addWidget(refresh)
        login = QPushButton("Beheerder Login")
        login.setStyleSheet(
            "QPushButton {"
            "  background:#facc15;"
            "  color:#050505;"
            "  border-radius:999px;"
            "  padding:8px 28px;"
            "  font-weight:600;"
            "}"
            "QPushButton:hover { background:#050505; color:#facc15; }"
        )
        header.addWidget(login)
        layout.addLayout(header)

        self.net_card = self._status_card()
        layout.addWidget(self.net_card)

        stats_grid = QGridLayout()
        stats_grid.setSpacing(12)
        self.cpu_card = self._stat_card("CPU Gebruik")
        self.ram_card = self._stat_card("RAM Gebruik")
        self.disk_card = self._stat_card("SD Kaart Opslag")
        stats_grid.addWidget(self.cpu_card, 0, 0)
        stats_grid.addWidget(self.ram_card, 0, 1)
        stats_grid.addWidget(self.disk_card, 0, 2)
        layout.addLayout(stats_grid)

        self.system_card = self._system_info_card()
        layout.addWidget(self.system_card)

        self.iface_card = self._interfaces_card()
        layout.addWidget(self.iface_card)

        self.refresh_stats()
        timer = QTimer(self)
        timer.timeout.connect(self.refresh_stats)
        timer.start(4000)

    def _status_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("Card")
        layout = QGridLayout(card)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        labels = ["IP Adres", "MAC Adres", "Gateway", "DNS Servers"]
        self.status_values = [QLabel("-") for _ in labels]
        for idx, label in enumerate(labels):
            lbl = QLabel(label.upper())
            lbl.setStyleSheet("color:#6b7280; letter-spacing:0.3em; font-size:11px;")
            layout.addWidget(lbl, 0, idx)
            layout.addWidget(self.status_values[idx], 1, idx)
        return card

    def _stat_card(self, title: str) -> QFrame:
        card = QFrame()
        card.setObjectName("Card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 16, 16, 16)
        label = QLabel(title.upper())
        label.setStyleSheet("color:#6b7280; letter-spacing:0.3em; font-size:11px;")
        value = QLabel("-")
        value.setStyleSheet("font-size:26px; font-weight:700; color:#111111;")
        bar = QProgressBar()
        bar.setRange(0, 100)
        layout.addWidget(label)
        layout.addWidget(value)
        layout.addWidget(bar)
        layout.addWidget(QLabel(""))
        card.value_label = value  # type: ignore[attr-defined]
        card.bar = bar  # type: ignore[attr-defined]
        return card

    def _system_info_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("Card")
        layout = QGridLayout(card)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        entries = [
            ("Hostname", socket.gethostname()),
            ("Model", platform.machine()),
            ("Besturingssysteem", f"{platform.system()} {platform.release()}"),
            ("Uptime", self._format_uptime()),
        ]
        for idx, (label, value) in enumerate(entries):
            lbl = QLabel(label.upper())
            lbl.setStyleSheet("color:#6b7280; letter-spacing:0.3em; font-size:11px;")
            val = QLabel(value)
            layout.addWidget(lbl, idx // 2, (idx % 2) * 2)
            layout.addWidget(val, idx // 2, (idx % 2) * 2 + 1)
        return card

    def _interfaces_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("Card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 16, 16, 16)
        title = QLabel("Netwerk Interfaces")
        title.setStyleSheet("font-size:18px; font-weight:700; letter-spacing:0.08em;")
        layout.addWidget(title)
        self.interface_labels = []
        for iface in ("eth0", "wlan0"):
            row = QHBoxLayout()
            name = QLabel(iface.upper())
            name.setStyleSheet(
                "font-family:'SFMono-Regular','Menlo','Courier New',monospace; letter-spacing:0.35em; color:#111111;"
            )
            status = QLabel("Onbekend")
            row.addWidget(name)
            row.addStretch(1)
            row.addWidget(status)
            layout.addLayout(row)
            self.interface_labels.append(status)
        return card

    def refresh_stats(self):
        cpu = psutil.cpu_percent()
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage("/")

        self.cpu_card.value_label.setText(f"{cpu:.0f}%")  # type: ignore[attr-defined]
        self.cpu_card.bar.setValue(int(cpu))  # type: ignore[attr-defined]
        self.ram_card.value_label.setText(  # type: ignore[attr-defined]
            f"{_format_bytes(mem.used)} / {_format_bytes(mem.total)}"
        )
        self.ram_card.bar.setValue(int(mem.percent))  # type: ignore[attr-defined]
        self.disk_card.value_label.setText(  # type: ignore[attr-defined]
            f"{_format_bytes(disk.used)} / {_format_bytes(disk.total)}"
        )
        self.disk_card.bar.setValue(int(disk.percent))  # type: ignore[attr-defined]

        net_info = self._network_info()
        for label, value in zip(self.status_values, net_info):
            label.setText(value)

        stats = psutil.net_if_stats()
        for idx, iface in enumerate(("eth0", "wlan0")):
            status = stats.get(iface)
            if status and status.isup:
                txt = "Verbonden" if status.speed else "Actief"
            else:
                txt = "Niet actief"
            color = "#facc15" if status and status.isup else "#9ca3af"
            self.interface_labels[idx].setText(txt.upper())
            self.interface_labels[idx].setStyleSheet(
                f"color:{color}; font-weight:600; letter-spacing:0.08em;"
            )

    def _network_info(self):
        ip = "-"
        gateway = "-"
        dns = "8.8.8.8, 8.8.4.4"
        mac = "-"
        try:
            ip = socket.gethostbyname(socket.gethostname())
        except socket.gaierror:
            pass
        link_families = {
            getattr(socket, "AF_PACKET", None),
            getattr(socket, "AF_LINK", None),
        }
        for addrs in psutil.net_if_addrs().values():
            for addr in addrs:
                if addr.family in link_families and addr.family is not None:
                    mac = addr.address
        if psutil.net_if_stats():
            gateway = "192.168.1.1"
        return [ip, mac, gateway, dns]

    def _format_uptime(self) -> str:
        seconds = int(psutil.boot_time())
        uptime_seconds = time.time() - seconds
        days = int(uptime_seconds // (24 * 3600))
        hours = int((uptime_seconds % (24 * 3600)) // 3600)
        return f"{days} dagen, {hours} uur"
