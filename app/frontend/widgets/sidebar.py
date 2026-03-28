from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFontMetrics
from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget, QHBoxLayout

from ..translations import t, register_language_change_callback


class Sidebar(QWidget):
    navigate = Signal(str)

    # Define nav items with translation keys
    NAV_ITEMS = [
        ("chat", "💬", "nav_chat"),
        ("kb", "📚", "nav_knowledge_bank"),
        ("net", "🌐", "nav_network"),
        ("devices", "📱", "nav_devices"),
        ("settings", "⚡", "nav_settings"),
    ]

    def __init__(self):
        super().__init__()
        self.setObjectName("Sidebar")
        self.setFixedHeight(52)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 6, 16, 6)
        layout.setSpacing(18)

        self.buttons: dict[str, QPushButton] = {}
        self._button_labels: dict[str, QLabel] = {}
        self._button_label_keys: dict[str, str] = {}
        for key, icon, label_key in self.NAV_ITEMS:
            btn = QPushButton()
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setMinimumHeight(40)
            btn_layout = QHBoxLayout(btn)
            btn_layout.setContentsMargins(20, 8, 20, 8)
            btn_layout.setSpacing(10)
            btn_layout.addStretch(1)
            icon_label = QLabel(icon)
            icon_label.setFixedWidth(18)
            icon_label.setStyleSheet("font-size:14px; color:#212121;")
            text_label = QLabel(t(label_key))
            text_label.setAlignment(Qt.AlignVCenter)
            text_label.setStyleSheet("font-weight:600; letter-spacing:0.01em;")
            btn_layout.addWidget(icon_label)
            btn_layout.addWidget(text_label)
            btn_layout.addStretch(1)
            btn.clicked.connect(lambda _checked, k=key: self._on_nav(k))
            self.buttons[key] = btn
            self._button_labels[key] = text_label
            self._button_label_keys[key] = label_key
            layout.addWidget(btn)

        self._sync_button_widths()
        register_language_change_callback(self._update_translations)

    def _update_translations(self) -> None:
        """Update all translatable labels when language changes."""
        for key, icon, label_key in self.NAV_ITEMS:
            if key in self._button_labels:
                self._button_labels[key].setText(t(label_key))
        self._sync_button_widths()

    def _sync_button_widths(self) -> None:
        for key, label in self._button_labels.items():
            metrics = QFontMetrics(label.font())
            label_width = metrics.horizontalAdvance(label.text())
            button_width = max(168, label_width + 18 + 10 + 40)
            self.buttons[key].setMinimumWidth(button_width)

    def _on_nav(self, key: str):
        self.set_current(key)
        self.navigate.emit(key)

    def set_current(self, key: str):
        for name, btn in self.buttons.items():
            btn.setProperty("active", "true" if name == key else "false")
            btn.setChecked(name == key)
            btn.style().unpolish(btn)
            btn.style().polish(btn)
