import asyncio
import sys
import os
from typing import Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QLinearGradient, QBrush, QPen
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QProgressBar,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)
from qasync import QEventLoop

from .config import BACKEND_WS
from .net.ws_client import WSClient
from .theme import AITJE_QSS
from .translations import t, register_language_change_callback
from .widgets.chat_page import ChatPage
from .widgets.contacts_page import ContactsPage
from .widgets.devices_page import DevicesPage
from .widgets.headerbar import HeaderBar
from .widgets.knowledge_page import KnowledgePage
from .widgets.maps_page import MapsPage
from .widgets.network_page import NetworkStatusPage
from .widgets.sidebar import Sidebar
from .widgets.settings_page import SettingsPage


class BootScreen(QWidget):
    """Animated splash screen that mimics the AITJE loading state from the Figma design."""

    # Translation keys for status steps
    STATUS_STEP_KEYS = [
        (0, "boot_starting"),
        (20, "boot_loading_neural"),
        (45, "boot_preparing_api"),
        (70, "boot_syncing_devices"),
        (90, "boot_almost_ready"),
        (100, "boot_welcome"),
    ]

    def __init__(
        self,
        logo_path: Optional[str] = None,
        duration_ms: int = 5000,
        on_finished=None,
    ):
        super().__init__()

        self.on_finished = on_finished
        self.duration_ms = duration_ms
        self.progress_value = 0

        self.setObjectName("BootScreenRoot")
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        self.showFullScreen()

        self.setStyleSheet(
            """
            QWidget#BootScreenRoot {
                background: #ffffff;
                color: #111111;
            }
            QLabel#BootTitle {
                font-size: 48pt;
                font-weight: 800;
                letter-spacing: 0.04em;
                color: #111111;
            }
            QLabel#BootSubtitle {
                font-size: 14pt;
                color: #4b5563;
            }
            QLabel#BootPercent {
                font-size: 16pt;
                font-weight: 700;
                color: #111111;
            }
            QProgressBar {
                background: #f5f5f5;
                border: 1px solid #e4e4e7;
                border-radius: 999px;
                height: 28px;
                color: #111111;
            }
            QProgressBar::chunk {
                border-radius: 999px;
                background: #facc15;
            }
            """
        )

        outer = QVBoxLayout(self)
        outer.setContentsMargins(80, 80, 80, 80)
        outer.setSpacing(32)
        outer.addStretch(1)

        center = QVBoxLayout()
        center.setSpacing(24)
        center.setAlignment(Qt.AlignCenter)

        hero_pixmap = None
        if logo_path and os.path.exists(logo_path):
            hero_pixmap = QPixmap(logo_path)
        hero_label = QLabel()
        hero_label.setAlignment(Qt.AlignCenter)
        if hero_pixmap and not hero_pixmap.isNull():
            hero_label.setPixmap(
                hero_pixmap.scaled(260, 320, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )
        else:
            hero_label.setPixmap(self._build_egg_pixmap(260, 320))
        center.addWidget(hero_label, 0, Qt.AlignCenter)

        title = QLabel(t("boot_title"))
        title.setObjectName("BootTitle")
        title.setAlignment(Qt.AlignCenter)
        center.addWidget(title)

        subtitle = QLabel(t("boot_subtitle"))
        subtitle.setObjectName("BootSubtitle")
        subtitle.setAlignment(Qt.AlignCenter)
        center.addWidget(subtitle)

        outer.addLayout(center)

        progress_layout = QVBoxLayout()
        progress_layout.setSpacing(8)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setTextVisible(False)
        progress_layout.addWidget(self.progress_bar)

        info_row = QHBoxLayout()
        info_row.setContentsMargins(0, 0, 0, 0)

        self.status_label = QLabel(t(self.STATUS_STEP_KEYS[0][1]))
        self.status_label.setObjectName("BootSubtitle")
        info_row.addWidget(self.status_label, 1, Qt.AlignLeft)

        self.percent_label = QLabel("0%")
        self.percent_label.setObjectName("BootPercent")
        info_row.addWidget(self.percent_label, 0, Qt.AlignRight)

        progress_layout.addLayout(info_row)
        outer.addLayout(progress_layout)
        outer.addStretch(1)

        self.timer = QTimer(self)
        total_ticks = max(1, duration_ms // 60)
        self.increment = max(1, 100 // total_ticks)
        self.timer.timeout.connect(self._advance)
        self.timer.start(60)

    def _build_egg_pixmap(self, width: int, height: int) -> QPixmap:
        pixmap = QPixmap(width, height)
        pixmap.fill(Qt.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)

        gradient = QLinearGradient(0, 0, 0, height)
        gradient.setColorAt(0, QColor("#ffffff"))
        gradient.setColorAt(1, QColor("#f7f7f7"))
        painter.setBrush(QBrush(gradient))
        painter.setPen(QPen(QColor("#0a0a0a"), 4))
        painter.drawEllipse(10, 10, width - 20, height - 20)

        # Simple crack lines to mimic the Figma egg
        painter.setPen(QPen(QColor("#0a0a0a"), 2))
        painter.drawLine(width * 0.45, height * 0.35, width * 0.5, height * 0.55)
        painter.drawLine(width * 0.55, height * 0.38, width * 0.5, height * 0.6)
        painter.end()
        return pixmap

    def _advance(self):
        self.progress_value = min(100, self.progress_value + self.increment)
        self.progress_bar.setValue(self.progress_value)
        self.percent_label.setText(f"{self.progress_value}%")

        for threshold, key in reversed(self.STATUS_STEP_KEYS):
            if self.progress_value >= threshold:
                self.status_label.setText(t(key))
                break

        if self.progress_value >= 100:
            self.timer.stop()
            QTimer.singleShot(400, self.finish)

    def finish(self):
        if self.on_finished:
            self.on_finished()
        self.close()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AITJE Dashboard")
        self.resize(1200, 800)

        self.ws_client = WSClient(BACKEND_WS)

        root = QWidget()
        root.setObjectName("RootWidget")
        self.setCentralWidget(root)

        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self.sidebar = Sidebar()
        self.sidebar.setFixedWidth(280)
        root_layout.addWidget(self.sidebar)

        self.center = QWidget()
        self.center.setObjectName("CenterContainer")
        center_layout = QVBoxLayout(self.center)
        center_layout.setContentsMargins(0, 16, 0, 0)
        center_layout.setSpacing(0)

        self.header = HeaderBar("AITJE Dashboard")
        self.header.home_requested.connect(self._go_home)
        center_layout.addWidget(self.header)

        self.pages = {
            "chat": ChatPage(self.ws_client),
            "kb": KnowledgePage(),
            "maps": MapsPage(),
            "contacts": ContactsPage(),
            "net": NetworkStatusPage(),
            "devices": DevicesPage(),
            "settings": SettingsPage(),
        }

        contacts_page = self.pages.get("contacts")
        maps_page = self.pages.get("maps")
        if isinstance(contacts_page, ContactsPage):
            contacts_page.view_on_map_requested.connect(
                self._handle_view_on_map_request
            )
            contacts_page.add_location_requested.connect(
                self._handle_add_location_request
            )
        if isinstance(maps_page, MapsPage) and isinstance(contacts_page, ContactsPage):
            contacts_page.contacts_updated.connect(
                lambda contact_id="": maps_page.handle_external_contact_change(
                    contact_id or None
                )
            )
            maps_page.contact_changed.connect(
                lambda contact_id="": contacts_page.reload_contacts(
                    select_id=contact_id or None
                )
            )
        self.content_scroll = QScrollArea()
        self.content_scroll.setWidgetResizable(True)
        self.content_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.content = QWidget()
        self.content.setObjectName("ContentArea")

        content_layout = QVBoxLayout(self.content)
        content_layout.setContentsMargins(24, 24, 24, 24)
        content_layout.setSpacing(16)
        for page in self.pages.values():
            content_layout.addWidget(page)
            page.setObjectName("Card")
            page.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.content_scroll.setWidget(self.content)

        center_layout.addWidget(self.content_scroll, 1)
        root_layout.addWidget(self.center, 1)

        self.sidebar.navigate.connect(self.show_page)
        self.sidebar.set_current("chat")
        self.show_page("chat")

        self.setStyleSheet(AITJE_QSS)

        # Register for language changes
        register_language_change_callback(self._on_language_change)
        self.header.language_changed.connect(self._on_language_change)

    def _on_language_change(self, _lang: str = "") -> None:
        """Update all UI elements when language changes."""
        self._update_page_header()

    def _handle_view_on_map_request(self, contact: dict) -> None:
        maps_page = self.pages.get("maps")
        if isinstance(maps_page, MapsPage):
            maps_page.focus_on_contact(contact)
        self.sidebar.set_current("maps")
        self.show_page("maps")

    def _handle_add_location_request(self, contact: dict, force_pin: bool = False) -> None:
        maps_page = self.pages.get("maps")
        if isinstance(maps_page, MapsPage):
            maps_page.request_location_for_contact(contact, force_pin=force_pin)
        self.sidebar.set_current("maps")
        self.show_page("maps")

    def show_page(self, key: str):
        for name, page in self.pages.items():
            page.setVisible(name == key)
        self._current_page_key = key
        self._update_page_header()

    def _update_page_header(self):
        """Update header title and subtitle for current page."""
        key = getattr(self, "_current_page_key", "chat")
        title_keys = {
            "chat": "page_title_chat",
            "kb": "page_title_kb",
            "maps": "page_title_maps",
            "contacts": "page_title_contacts",
            "net": "page_title_net",
            "devices": "page_title_devices",
            "settings": "page_title_settings",
        }
        subtitle_keys = {
            "chat": "page_subtitle_chat",
            "kb": "page_subtitle_kb",
            "maps": "page_subtitle_maps",
            "contacts": "page_subtitle_contacts",
            "net": "page_subtitle_net",
            "devices": "page_subtitle_devices",
            "settings": "page_subtitle_settings",
        }
        self.header.set_title(t(title_keys.get(key, "page_title_chat")))
        self.header.set_subtitle(t(subtitle_keys.get(key, "subtitle_local_ai_console")))

    def _go_home(self):
        self.sidebar.set_current("chat")
        self.show_page("chat")

    def closeEvent(self, event):
        asyncio.create_task(self.ws_client.close())
        event.accept()


def main():
    app = QApplication(sys.argv)

    app_dir = os.path.dirname(__file__)
    app_images_dir = os.path.join(app_dir, "images")
    app_icon_path = os.path.join(app_images_dir, "aitje-logo.png")
    if os.path.exists(app_icon_path):
        app.setWindowIcon(QIcon(app_icon_path))

    boot_logo_path = app_icon_path

    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)

    window = MainWindow()

    def on_boot_finished():
        window.showFullScreen()

    boot_screen = BootScreen(
        logo_path=boot_logo_path,
        duration_ms=5000,
        on_finished=on_boot_finished,
    )
    boot_screen.show()

    with loop:
        loop.run_forever()


if __name__ == "__main__":
    main()
