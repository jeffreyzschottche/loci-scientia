import asyncio
import sys
import os

from PySide6.QtCore import QUrl, QDir # NIEUW: Import voor robuuste padconversie
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QHBoxLayout, QMainWindow, QVBoxLayout, QWidget
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
from .widgets.maps_page import MapsPage
from .widgets.network_page import NetworkStatusPage
from .widgets.sidebar import Sidebar
from .widgets.settings_page import SettingsPage

BACKEND_WS = "ws://127.0.0.1:8000/ws"


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
                    background-size: cover; 
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

    async def closeEvent(self, event):  # type: ignore[override]
        await self.ws_client.close()
        event.accept()


def main():
    app = QApplication(sys.argv)
    # Zorg dat de desktopafbeelding ook als applicatie-icoon wordt ingesteld
    app_images_dir = os.path.join(os.path.dirname(__file__), "images")
    app_icon_path = os.path.join(app_images_dir, "desktopimage.jpeg")
    if os.path.exists(app_icon_path):
        app.setWindowIcon(QIcon(app_icon_path))
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)
    window = MainWindow()
    window.show()
    with loop:
        loop.run_forever()


if __name__ == "__main__":
    main()
