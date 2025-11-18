from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class FAQPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        layout.addWidget(QLabel("FAQ"))
        empty = QLabel("Deze sectie is nog leeg. Voeg later veelgestelde vragen toe.")
        empty.setStyleSheet("color:#9ca3af;")
        layout.addWidget(empty)
        layout.addStretch(1)
