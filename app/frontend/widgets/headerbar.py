from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget


class HeaderBar(QWidget):
    def __init__(self, title: str):
        super().__init__()
        self.setObjectName("Header")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(8)
        self.setFixedHeight(64)

        self.title = QLabel(title)
        self.title.setStyleSheet("font-size:16px;")
        self.status = QLabel("● Online")
        self.status.setStyleSheet("color:#10b981;")

        layout.addWidget(self.title)
        layout.addStretch(1)
        layout.addWidget(self.status)

    def set_title(self, title: str):
        self.title.setText(title)
