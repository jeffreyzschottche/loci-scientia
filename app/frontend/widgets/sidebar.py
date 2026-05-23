from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QPushButton, QSizePolicy, QWidget, QHBoxLayout

from ..translations import t, register_language_change_callback


class Sidebar(QWidget):
    navigate = Signal(str)

    # Define nav items with translation keys
    NAV_ITEMS = [
        ("chat", "💬", "nav_chat"),
        ("kb", "📚", "nav_knowledge_bank"),
        ("net", "🌐", "nav_network"),
        ("devices", "👥", "nav_devices"),
        ("settings", "⚙️", "nav_settings"),
    ]

    def __init__(self):
        super().__init__()
        self.setObjectName("Sidebar")
        self.setFixedHeight(52)
        self.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(6)

        self.buttons: dict[str, QPushButton] = {}
        self._button_label_keys: dict[str, str] = {}
        for key, icon, label_key in self.NAV_ITEMS:
            btn = QPushButton()
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setMinimumHeight(40)
            btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            btn.setStyleSheet("text-align:center;")
            font = btn.font()
            font.setWeight(QFont.DemiBold)
            btn.setFont(font)
            btn.setText(f"{icon} {t(label_key)}")
            btn.clicked.connect(lambda _checked, k=key: self._on_nav(k))
            self.buttons[key] = btn
            self._button_label_keys[key] = label_key
            layout.addWidget(btn)

        self._sync_button_widths()
        register_language_change_callback(self._update_translations)

    def _update_translations(self) -> None:
        """Update all translatable labels when language changes."""
        for key, icon, label_key in self.NAV_ITEMS:
            if key in self.buttons:
                self.buttons[key].setText(f"{icon} {t(label_key)}")
        self._sync_button_widths()

    def _sync_button_widths(self) -> None:
        total_width = self.layout().contentsMargins().left() + self.layout().contentsMargins().right()
        spacing = self.layout().spacing()
        for key, btn in self.buttons.items():
            text_width = btn.fontMetrics().horizontalAdvance(btn.text())
            button_width = max(124, text_width + 40)
            if key == "devices":
                button_width += 16
            btn.setFixedWidth(button_width)
            total_width += button_width
        if self.buttons:
            total_width += spacing * (len(self.buttons) - 1)
        self.setMinimumWidth(total_width)
        self.updateGeometry()

    def _on_nav(self, key: str):
        self.set_current(key)
        self.navigate.emit(key)

    def set_current(self, key: str):
        for name, btn in self.buttons.items():
            btn.setProperty("active", "true" if name == key else "false")
            btn.setChecked(name == key)
            btn.style().unpolish(btn)
            btn.style().polish(btn)
