import os

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget, QHBoxLayout

from ..translations import t, register_language_change_callback


class Sidebar(QWidget):
    navigate = Signal(str)

    # Define nav items with translation keys
    NAV_ITEMS = [
        ("chat", "💬", "nav_chat"),
        ("kb", "📚", "nav_knowledge_bank"),
        ("maps", "🗺", "nav_maps"),
        ("contacts", "👥", "nav_contacts"),
        ("net", "🌐", "nav_network"),
        ("devices", "📱", "nav_devices"),
        ("settings", "⚡", "nav_settings"),
    ]

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
        self._subtitle = QLabel(t("sidebar_subtitle"))
        self._subtitle.setStyleSheet(
            "color:#9ca3af; font-size:11px; letter-spacing:0.45em;"
        )
        head_layout.addWidget(self._subtitle)
        layout.addWidget(header)

        self.buttons: dict[str, QPushButton] = {}
        self._button_labels: dict[str, QLabel] = {}
        for key, icon, label_key in self.NAV_ITEMS:
            btn = QPushButton()
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn_layout = QHBoxLayout(btn)
            btn_layout.setContentsMargins(16, 4, 16, 4)
            btn_layout.setSpacing(12)
            icon_label = QLabel(icon)
            icon_label.setFixedWidth(26)
            icon_label.setStyleSheet("font-size:16px; color:#212121;")
            text_label = QLabel(t(label_key))
            text_label.setStyleSheet("font-weight:600; letter-spacing:0.02em;")
            btn_layout.addWidget(icon_label)
            btn_layout.addWidget(text_label)
            btn_layout.addStretch(1)
            btn.clicked.connect(lambda _checked, k=key: self._on_nav(k))
            self.buttons[key] = btn
            self._button_labels[key] = text_label
            layout.addWidget(btn)

        layout.addStretch(1)
        footer = QLabel("AITJE v1.0")
        footer.setStyleSheet(
            "color:#9ca3af; font-size:11px; padding:12px; letter-spacing:0.2em;"
        )
        layout.addWidget(footer)

        register_language_change_callback(self._update_translations)

    def _update_translations(self) -> None:
        """Update all translatable labels when language changes."""
        self._subtitle.setText(t("sidebar_subtitle"))
        for key, icon, label_key in self.NAV_ITEMS:
            if key in self._button_labels:
                self._button_labels[key].setText(t(label_key))

    def _on_nav(self, key: str):
        self.set_current(key)
        self.navigate.emit(key)

    def set_current(self, key: str):
        for name, btn in self.buttons.items():
            btn.setProperty("active", "true" if name == key else "false")
            btn.setChecked(name == key)
            btn.style().unpolish(btn)
            btn.style().polish(btn)
