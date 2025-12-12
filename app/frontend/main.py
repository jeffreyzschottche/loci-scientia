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
    QVBoxLayout,
    QWidget,
)
from qasync import QEventLoop

from .config import BACKEND_WS
from .net.ws_client import WSClient
from .theme import AITJE_QSS
from .widgets.api_page import ApiPage
from .widgets.chat_page import ChatPage
from .widgets.contacts_page import ContactsPage
from .widgets.devices_page import DevicesPage
from .widgets.faq_page import FAQPage
from .widgets.headerbar import HeaderBar
from .widgets.knowledge_page import KnowledgePage
from .widgets.maps_page import MapsPage
from .widgets.network_page import NetworkStatusPage
from .widgets.sidebar import Sidebar
from .widgets.settings_page import SettingsPage


class BootScreen(QWidget):
    """Animated splash screen that mimics the AITJE loading state from the Figma design."""

    STATUS_STEPS = [
        (0, "Lokale AI wordt opgestart..."),
        (20, "Neurale netwerken laden..."),
        (45, "API endpoints voorbereiden..."),
        (70, "Devices synchroniseren..."),
        (90, "Bijna klaar..."),
        (100, "Welkom! ✓"),
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
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 #fff7d6,
                    stop:1 #f4f1ff
                );
                color: #0a0a0a;
            }
            QLabel#BootTitle {
                font-size: 42pt;
                font-weight: 700;
                color: #0a0a0a;
            }
            QLabel#BootSubtitle {
                font-size: 14pt;
                color: #262626;
            }
            QLabel#BootPercent {
                font-size: 16pt;
                font-weight: 600;
                color: #0a0a0a;
            }
            QProgressBar {
                background: #f4f4f5;
                border: 0;
                border-radius: 16px;
                height: 24px;
                color: #0a0a0a;
            }
            QProgressBar::chunk {
                border-radius: 16px;
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #facc15,
                    stop:1 #f97316
                );
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

        if logo_path and os.path.exists(logo_path):
            brand = QLabel()
            brand.setAlignment(Qt.AlignCenter)
            brand.setPixmap(QPixmap(logo_path).scaled(72, 72, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            center.addWidget(brand, 0, Qt.AlignCenter)

        self.egg_label = QLabel()
        self.egg_label.setAlignment(Qt.AlignCenter)
        self.egg_label.setPixmap(self._build_egg_pixmap(260, 320))
        center.addWidget(self.egg_label, 0, Qt.AlignCenter)

        title = QLabel("AITJE ontwaakt...")
        title.setObjectName("BootTitle")
        title.setAlignment(Qt.AlignCenter)
        center.addWidget(title)

        subtitle = QLabel("De antwoorden van het universum worden lokaal opgestart.")
        subtitle.setObjectName("BootSubtitle")
        subtitle.setAlignment(Qt.AlignCenter)
        center.addWidget(subtitle)

        outer.addLayout(center)

        progress_layout = QVBoxLayout()
        progress_layout.setSpacing(8)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        progress_layout.addWidget(self.progress_bar)

        info_row = QHBoxLayout()
        info_row.setContentsMargins(0, 0, 0, 0)

        self.status_label = QLabel(self.STATUS_STEPS[0][1])
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
        gradient.setColorAt(1, QColor("#fef3c7"))
        painter.setBrush(QBrush(gradient))
        painter.setPen(QPen(QColor("#f5e8b5"), 4))
        painter.drawEllipse(10, 10, width - 20, height - 20)

        # Simple crack lines to mimic the Figma egg
        painter.setPen(QPen(QColor("#0f172a"), 2))
        painter.drawLine(width * 0.45, height * 0.35, width * 0.5, height * 0.55)
        painter.drawLine(width * 0.55, height * 0.38, width * 0.5, height * 0.6)
        painter.end()
        return pixmap

    def _advance(self):
        self.progress_value = min(100, self.progress_value + self.increment)
        self.progress_bar.setValue(self.progress_value)
        self.percent_label.setText(f"{self.progress_value}%")

        for threshold, message in reversed(self.STATUS_STEPS):
            if self.progress_value >= threshold:
                self.status_label.setText(message)
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
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(0)

        self.header = HeaderBar("AITJE Dashboard")
        self.header.home_requested.connect(self._go_home)
        center_layout.addWidget(self.header)

        self.pages = {
            "chat": ChatPage(self.ws_client),
            "api": ApiPage(),
            "kb": KnowledgePage(),
            "maps": MapsPage(),
            "contacts": ContactsPage(),
            "net": NetworkStatusPage(),
            "devices": DevicesPage(),
            "settings": SettingsPage(),
            "faq": FAQPage(),
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
        self.content = QWidget()
        self.content.setObjectName("ContentArea")

        content_layout = QVBoxLayout(self.content)
        content_layout.setContentsMargins(24, 24, 24, 24)
        content_layout.setSpacing(16)
        for page in self.pages.values():
            content_layout.addWidget(page)
            page.setObjectName("Card")

        center_layout.addWidget(self.content, 1)
        root_layout.addWidget(self.center, 1)

        self.sidebar.navigate.connect(self.show_page)
        self.sidebar.set_current("chat")
        self.show_page("chat")
        
        self.setStyleSheet(AITJE_QSS)

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
        titles = {
            "chat": "Chat Assistant",
            "api": "API Management",
            "kb": "Kennisbank",
            "maps": "Maps",
            "contacts": "Contacten",
            "net": "Netwerk Status",
            "devices": "Connected Devices",
            "settings": "Instellingen",
            "faq": "FAQ",
        }
        self.header.set_title(titles.get(key, "AITJE"))

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
        window.show()

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
