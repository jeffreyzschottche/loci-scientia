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

        self.status = QLabel("● Device online")
        self.status.setStyleSheet(
            "color:#facc15; font-weight:600; letter-spacing:0.08em;"
        )
        layout.addWidget(self.status, 0, Qt.AlignVCenter)

        self.home_btn = QPushButton("Chat")
        self.home_btn.setCursor(Qt.PointingHandCursor)
        self.home_btn.setStyleSheet(
            "QPushButton {"
            "  background-color: #facc15;"
            "  color: #050505;"
            "  font-weight: 600;"
            "  border-radius: 999px;"
            "  padding: 12px 32px;"
            "  border: 0;"
            "}"
            "QPushButton:hover { background-color: #050505; color: #facc15; }"
        )
        self.home_btn.clicked.connect(self.home_requested.emit)
        layout.addWidget(self.home_btn, 0, Qt.AlignVCenter)

    def set_title(self, title: str):
        self.title.setText(title)
