import asyncio
import sys

from PySide6.QtWidgets import QApplication, QHBoxLayout, QMainWindow, QVBoxLayout, QWidget
from qasync import QEventLoop

from .net.ws_client import WSClient
from .theme import DARK_QSS
from .widgets.api_page import ApiPage
from .widgets.chat_page import ChatPage
from .widgets.headerbar import HeaderBar
from .widgets.sidebar import Sidebar
from .widgets.ssd_monitor import SSDMonitor

BACKEND_WS = "ws://127.0.0.1:8000/ws"


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Loci Scientia")
        self.resize(1200, 800)

        self.ws_client = WSClient(BACKEND_WS)

        root = QWidget()
        self.setCentralWidget(root)
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self.sidebar = Sidebar()
        self.sidebar.setFixedWidth(256)
        root_layout.addWidget(self.sidebar)

        self.center = QWidget()
        center_layout = QVBoxLayout(self.center)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(0)

        self.header = HeaderBar("Chat Assistant")
        center_layout.addWidget(self.header)

        self.pages = {
            "chat": ChatPage(self.ws_client),
            "api": ApiPage(),
            "net": SSDMonitor("/" if sys.platform != "win32" else "C:\\"),
        }

        self.content = QWidget()
        content_layout = QVBoxLayout(self.content)
        content_layout.setContentsMargins(16, 16, 16, 16)
        for page in self.pages.values():
            content_layout.addWidget(page)
        center_layout.addWidget(self.content, 1)
        root_layout.addWidget(self.center, 1)

        self.sidebar.navigate.connect(self.show_page)
        self.show_page("chat")
        self.setStyleSheet(DARK_QSS)

    def show_page(self, key: str):
        for name, page in self.pages.items():
            page.setVisible(name == key)
        titles = {
            "chat": "Chat Assistant",
            "api": "API Management",
            "net": "Netwerk Status",
        }
        self.header.set_title(titles.get(key, "Loci"))

    async def closeEvent(self, event):  # type: ignore[override]
        await self.ws_client.close()
        event.accept()


def main():
    app = QApplication(sys.argv)
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)
    window = MainWindow()
    window.show()
    with loop:
        loop.run_forever()


if __name__ == "__main__":
    main()
