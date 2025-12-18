from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class FAQPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        title = QLabel("FAQ")
        title.setStyleSheet("font-size:28px; font-weight:800; letter-spacing:0.05em;")
        layout.addWidget(title)
        empty = QLabel("Deze sectie is nog leeg. Voeg later veelgestelde vragen toe.")
        empty.setStyleSheet("color:#6b7280; letter-spacing:0.02em;")
        layout.addWidget(empty)
        layout.addStretch(1)
