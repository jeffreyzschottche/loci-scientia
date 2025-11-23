from PySide6.QtCore import Qt, Signal
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
        header.setFixedHeight(80)
        head_layout = QVBoxLayout(header)
        head_layout.setContentsMargins(16, 16, 16, 0)
        logo = QLabel("Loci Scientia")
        logo.setStyleSheet("font-size:18px; font-weight:600;")
        head_layout.addWidget(logo)
        subtitle = QLabel("Offline LLM Console")
        subtitle.setStyleSheet("color:#9ca3af; font-size:12px;")
        head_layout.addWidget(subtitle)
        layout.addWidget(header)

        self.buttons: dict[str, QPushButton] = {}
        nav_items = [
            ("chat", "💬", "Chat"),
            ("api", "⚙", "API Management"),
            ("kb", "📚", "Kennisbank"),
            ("maps", "🗺", "Maps"),
            ("contacts", "👥", "Contacten"),
            ("net", "🌐", "Netwerk Status"),
            ("devices", "📱", "Connected Devices"),
            ("settings", "⚡", "Instellingen"),
            ("faq", "❓", "FAQ"),
        ]
        for key, icon, label in nav_items:
            btn = QPushButton()
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn_layout = QHBoxLayout(btn)
            btn_layout.setContentsMargins(16, 8, 16, 8)
            btn_layout.setSpacing(12)
            icon_label = QLabel(icon)
            icon_label.setFixedWidth(20)
            text_label = QLabel(label)
            btn_layout.addWidget(icon_label)
            btn_layout.addWidget(text_label)
            btn_layout.addStretch(1)
            btn.clicked.connect(lambda _checked, k=key: self._on_nav(k))
            self.buttons[key] = btn
            layout.addWidget(btn)

        layout.addStretch(1)
        footer = QLabel("Loci Scientia OS v1.0\nCognitionis Scientia")
        footer.setStyleSheet("color:#6b7280; font-size:11px; padding:12px;")
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
