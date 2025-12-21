from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget


class HeaderBar(QWidget):
    home_requested = Signal()

    def __init__(self, title: str):
        super().__init__()
        self.setObjectName("Header")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(24, 12, 24, 12)
        layout.setSpacing(16)
        self.setFixedHeight(80)

        brand = QWidget()
        brand_layout = QVBoxLayout(brand)
        brand_layout.setContentsMargins(0, 0, 0, 0)
        brand_layout.setSpacing(2)

        self.title = QLabel(title)
        self.title.setStyleSheet(
            "font-size:26px; font-weight:800; letter-spacing:0.02em; color:#111111;"
        )
        self.subtitle = QLabel("Lokale AI-console")
        self.subtitle.setStyleSheet(
            "color:#9ca3af; font-size:11px; letter-spacing:0.45em;"
        )
        brand_layout.addWidget(self.title)
        brand_layout.addWidget(self.subtitle)

        layout.addWidget(brand, 0, Qt.AlignVCenter)
        layout.addStretch(1)

        self.status = QLabel()
        self.status.setObjectName("HeaderStatus")
        self.set_online(True)
        layout.addWidget(self.status, 0, Qt.AlignVCenter)

        self.home_btn = QPushButton("Chat")
        self.home_btn.setObjectName("HeaderHomeButton")
        self.home_btn.setCursor(Qt.PointingHandCursor)
        self.home_btn.setStyleSheet(
            "QPushButton {"
            "  background-color: #facc15;"
            "  color: #050505;"
            "  font-weight: 600;"
            "  border-radius: 20px;"
            "  padding: 12px 32px;"
            "  border: 0;"
            "}"
            "QPushButton:hover { background-color: #050505; color: #facc15; }"
        )
        self.home_btn.setMinimumHeight(40)
        self.home_btn.clicked.connect(self.home_requested.emit)
        layout.addWidget(self.home_btn, 0, Qt.AlignVCenter)

    def set_title(self, title: str):
        self.title.setText(title)

    def set_online(self, online: bool):
        text = "● ONLINE" if online else "● OFFLINE"
        color = "#16a34a" if online else "#ef4444"
        self.status.setText(text)
        self.status.setStyleSheet(
            f"color:{color}; font-weight:600; letter-spacing:0.08em;"
        )
