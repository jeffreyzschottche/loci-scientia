import os

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget, QHBoxLayout


class Sidebar(QWidget):
    navigate = Signal(str)

    def __init__(self):
        super().__init__()
        self.setObjectName("Sidebar")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        header = QWidget()
        header.setFixedHeight(96)
        head_layout = QVBoxLayout(header)
        head_layout.setContentsMargins(16, 32, 16, 0)
        head_layout.setSpacing(4)
        logo = QLabel()
        logo.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        images_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "images"))
        image_path = os.path.join(images_dir, "aitje.png")
        if os.path.exists(image_path):
            pixmap = QPixmap(image_path).scaled(
                140, 48, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            logo.setPixmap(pixmap)
        else:
            logo.setText("AITJE")
            logo.setStyleSheet(
                "font-size:24px; font-weight:800; letter-spacing:0.4em; color:#111111;"
            )
        head_layout.addWidget(logo)
        subtitle = QLabel("Lokale AI console")
        subtitle.setStyleSheet(
            "color:#9ca3af; font-size:11px; letter-spacing:0.45em;"
        )
        head_layout.addWidget(subtitle)
        layout.addWidget(header)

        self.buttons: dict[str, QPushButton] = {}
        nav_items = [
            ("chat", "💬", "Chat"),
            ("kb", "📚", "Kennisbank"),
            ("maps", "🗺", "Maps"),
            ("contacts", "👥", "Contacten"),
            ("net", "🌐", "Netwerk"),
            ("devices", "📱", "Connected Devices"),
            ("settings", "⚡", "Instellingen"),
        ]
        for key, icon, label in nav_items:
            btn = QPushButton()
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn_layout = QHBoxLayout(btn)
            btn_layout.setContentsMargins(16, 4, 16, 4)
            btn_layout.setSpacing(12)
            icon_label = QLabel(icon)
            icon_label.setFixedWidth(26)
            icon_label.setStyleSheet("font-size:16px; color:#212121;")
            text_label = QLabel(label)
            text_label.setStyleSheet("font-weight:600; letter-spacing:0.02em;")
            btn_layout.addWidget(icon_label)
            btn_layout.addWidget(text_label)
            btn_layout.addStretch(1)
            btn.clicked.connect(lambda _checked, k=key: self._on_nav(k))
            self.buttons[key] = btn
            layout.addWidget(btn)

        layout.addStretch(1)
        footer = QLabel("AITJE v1.0")
        footer.setStyleSheet(
            "color:#9ca3af; font-size:11px; padding:12px; letter-spacing:0.2em;"
        )
        layout.addWidget(footer)

    def _on_nav(self, key: str):
        self.set_current(key)
        self.navigate.emit(key)

    def set_current(self, key: str):
        for name, btn in self.buttons.items():
            btn.setProperty("active", "true" if name == key else "false")
            btn.setChecked(name == key)
            btn.style().unpolish(btn)
            btn.style().polish(btn)
