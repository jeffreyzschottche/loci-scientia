from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget


class Sidebar(QWidget):
    navigate = Signal(str)

    def __init__(self):
        super().__init__()
        self.setObjectName("Sidebar")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QWidget()
        header.setFixedHeight(64)
        head_layout = QVBoxLayout(header)
        head_layout.setContentsMargins(16, 12, 16, 12)
        logo = QLabel("Loci Scientia")
        logo.setStyleSheet("font-weight:600;")
        head_layout.addWidget(logo)
        layout.addWidget(header)

        self.buttons: dict[str, QPushButton] = {}
        for key, label in [
            ("chat", "Chat"),
            ("api", "API Management"),
            ("kb", "Kennisbank"),
            ("maps", "Maps"),
            ("contacts", "Contacten"),
            ("net", "Netwerk Status"),
        ]:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.clicked.connect(lambda _checked, k=key: self._on_nav(k))
            self.buttons[key] = btn
            layout.addWidget(btn)

        layout.addStretch(1)
        footer = QLabel("Loci Scientia OS v1.0\nCognitionis Scientia")
        footer.setStyleSheet("color:#6b7280; font-size:11px; padding:12px;")
        layout.addWidget(footer)

    def _on_nav(self, key: str):
        for name, btn in self.buttons.items():
            btn.setProperty("active", "true" if name == key else "false")
            btn.setChecked(name == key)
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        self.navigate.emit(key)
