import asyncio
import sys
import os
from typing import Optional

from PySide6.QtCore import QUrl, QDir, Qt, QTimer
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)
from qasync import QEventLoop

from .net.ws_client import WSClient
from .theme import DARK_QSS
from .widgets.api_page import ApiPage
from .widgets.chat_page import ChatPage
from .widgets.contacts_page import ContactsPage
from .widgets.devices_page import DevicesPage
from .widgets.faq_page import FAQPage
from .widgets.headerbar import HeaderBar
from .widgets.knowledge_page import KnowledgePage
from app.maps.maps_page import MapsPage
from .widgets.network_page import NetworkStatusPage
from .widgets.sidebar import Sidebar
from .widgets.settings_page import SettingsPage

BACKEND_WS = "ws://127.0.0.1:8000/ws"


class BootScreen(QWidget):
    def __init__(
        self,
        logo_path: Optional[str] = None,
        duration_ms: int = 5000,
        on_finished=None,
    ):
        super().__init__()

        self.on_finished = on_finished
        self.duration_ms = duration_ms

        self.setObjectName("BootScreenRoot")
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        self.showFullScreen()

        pixmap = QPixmap()
        image_url = ""
        if logo_path and os.path.exists(logo_path):
            loaded = QPixmap(logo_path)
            if not loaded.isNull():
                pixmap = loaded
                image_url = QUrl.fromLocalFile(logo_path).toString()

        style_lines = [
            "QWidget#BootScreenRoot {",
            "    background-color: #000000;",
        ]
        if image_url:
            style_lines += [
                f"    background-image: url({image_url});",
                "    background-repeat: no-repeat;",
                "    background-position: center;",
            ]
        style_lines += [
            "}",
            "QPlainTextEdit#Terminal {",
            "    background-color: rgba(0, 0, 0, 210);",
            "    color: #00ff7f;",
            "    border: 1px solid #00ff7f;",
            "    font-family: \"Fira Code\", \"Consolas\", \"Courier New\", monospace;",
            "    font-size: 12pt;",
            "    padding: 8px;",
            "}",
        ]
        self.setStyleSheet("\n".join(style_lines))
        self.background_pixmap = pixmap

        layout = QVBoxLayout(self)
        layout.setContentsMargins(80, 80, 80, 80)
        layout.setSpacing(0)

        logo_label = QLabel("Loci Scientia")
        logo_label.setObjectName("BootLogoLabel")
        logo_label.setAlignment(Qt.AlignCenter)
        logo_label.setStyleSheet(
            "font-size: 32pt;"
            "font-weight: 600;"
            "letter-spacing: 6px;"
        )
        layout.addWidget(logo_label, 0, Qt.AlignHCenter)
        layout.addSpacing(32)

        self.terminal = QPlainTextEdit()
        self.terminal.setObjectName("Terminal")
        self.terminal.setReadOnly(True)
        self.terminal.setLineWrapMode(QPlainTextEdit.NoWrap)

        layout.addWidget(self.terminal)

        self.messages = [
            "[BOOT] Initializing Loci kernel...",
            "[OK]  Loading core modules...",
            "[OK]  Mounting /knowledge...",
            "[OK]  Starting neural interfaces...",
            "[SYS] Scanning local devices...",
            "[OK]  Connecting to Loci Network...",
            "[OK]  Getting knowledge ready...",
            "[OK]  Finding out the secrets of the universe...",
            "[SYS] Installing dependencies for chat engine...",
            "[OK]  Starting Loci Scientia services...",
            "[DONE] System ready. Type 'loci --start' to begin.",
            "",
            "loci@localhost:~$ loci --start",
        ]

        self.current_index = 0
        self.interval_ms = max(150, int(self.duration_ms / (len(self.messages) + 1)))

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._next_message)
        self.timer.start(self.interval_ms)

    def paintEvent(self, event):
        painter = QPainter(self)
        if self.background_pixmap and not self.background_pixmap.isNull() and self.size().isValid():
            scaled = self.background_pixmap.scaled(
                self.size(),
                Qt.KeepAspectRatioByExpanding,
                Qt.SmoothTransformation,
            )
            painter.drawPixmap(0, 0, scaled)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 110))
        painter.end()
        super().paintEvent(event)

    def _next_message(self):
        if self.current_index < len(self.messages):
            line = self.messages[self.current_index]
            self.terminal.appendPlainText(line)
            self.current_index += 1
        else:
            self.timer.stop()
            QTimer.singleShot(400, self.finish)

    def finish(self):
        if self.on_finished:
            self.on_finished()
        self.close()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Loci Scientia")
        self.resize(1200, 800)

        self.ws_client = WSClient(BACKEND_WS)

        # --- CODE VOOR ACHTERGRONDAFBEELDING (Aangepast) ---
        # 1. Bepaal het absolute pad naar de afbeelding in dezelfde frontend map
        relative_path = os.path.join(os.path.dirname(__file__), "images", "desktopimage.jpeg")
        image_path = os.path.abspath(relative_path)
        
        print(f"DEBUG: Checking for image at path: {image_path}")
        
        icon = QIcon()
        if not os.path.exists(image_path):
             # Als de afbeelding niet gevonden wordt, print een waarschuwing
             print("WAARSCHUWING: Achtergrondafbeelding niet gevonden op het berekende pad.")
             image_url = ""
        else:
             # 2. Converteer naar een pad-URL met QUrl.fromLocalFile voor maximale compatibiliteit in Qt
             image_url = QUrl.fromLocalFile(image_path).toString()
             print(f"DEBUG: Using image URL: {image_url}")
             icon.addFile(image_path)


        # 3. Maak de root widget en stel de achtergrond in via CSS
        root = QWidget()
        root.setObjectName("RootWidget")
        self.setCentralWidget(root)
        
        # Stijl: Pas de achtergrondafbeelding toe op de root widget
        if image_url:
            root_style = f"""
                QWidget#RootWidget {{
                    background-image: url({image_url});
                    background-repeat: no-repeat;
                    background-position: center;
                }}
            """
            root.setStyleSheet(root_style)
        else:
            # Fallback CSS als de afbeelding niet is gevonden
            root.setStyleSheet("QWidget#RootWidget { background-color: #1e1e1e; }")

        if not icon.isNull():
            self.setWindowIcon(icon)

        # --- EINDE CODE VOOR ACHTERGRONDAFBEELDING ---

        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self.sidebar = Sidebar()
        self.sidebar.setFixedWidth(256)
        
        # Oplossing 2: Maak de sidebar transparant zodat de root achtergrond zichtbaar is
        self.sidebar.setStyleSheet("background: transparent;")

        root_layout.addWidget(self.sidebar)

        self.center = QWidget()
        
        # Oplossing 2: Maak de center widget transparant
        self.center.setStyleSheet("background: transparent;")
        
        center_layout = QVBoxLayout(self.center)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(0)

        self.header = HeaderBar("Chat Assistant")
        # Optioneel: Maak de header ook transparant als de image daar moet schijnen.
        # self.header.setStyleSheet("background: transparent;")
        
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

        contacts_page = self.pages["contacts"]
        if isinstance(contacts_page, ContactsPage):
            contacts_page.view_on_map_requested.connect(
                self._handle_view_on_map_request
            )
            contacts_page.add_location_requested.connect(
                self._handle_add_location_request
            )

        self.content = QWidget()
        
        # Oplossing 2: Zorg ervoor dat de content container ook transparant is
        self.content.setStyleSheet("background: transparent;")

        content_layout = QVBoxLayout(self.content)
        content_layout.setContentsMargins(16, 16, 16, 16)
        for page in self.pages.values():
            content_layout.addWidget(page)
            # Oplossing 2: Mogelijk moeten de individuele pagina's ook transparant zijn
            page.setStyleSheet("background: transparent;")
            
        center_layout.addWidget(self.content, 1)
        root_layout.addWidget(self.center, 1)

        self.sidebar.navigate.connect(self.show_page)
        self.sidebar.set_current("chat")
        self.show_page("chat")

        # Pas de DARK_QSS toe op de gehele MainWindow (behalve waar overschreven)
        self.setStyleSheet(DARK_QSS) 

    def _handle_view_on_map_request(self, contact: dict) -> None:
        maps_page = self.pages.get("maps")
        if isinstance(maps_page, MapsPage):
            maps_page.focus_on_contact(contact)
        self.sidebar.set_current("maps")
        self.show_page("maps")

    def _handle_add_location_request(self, contact: dict) -> None:
        maps_page = self.pages.get("maps")
        if isinstance(maps_page, MapsPage):
            maps_page.request_location_for_contact(contact)
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
        self.header.set_title(titles.get(key, "Loci"))

    def closeEvent(self, event):
        asyncio.create_task(self.ws_client.close())
        event.accept()


def main():
    app = QApplication(sys.argv)

    app_dir = os.path.dirname(__file__)
    app_images_dir = os.path.join(app_dir, "images")
    app_icon_path = os.path.join(app_images_dir, "desktopimage.jpeg")
    if os.path.exists(app_icon_path):
        app.setWindowIcon(QIcon(app_icon_path))

    boot_logo_path = os.path.join(app_images_dir, "lociscientialogo.png")

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
