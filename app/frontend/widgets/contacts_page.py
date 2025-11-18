from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class ContactsPage(QWidget):
    def __init__(self):
        super().__init__()
        self.contacts = [
            {
                "name": "Jan de Vries",
                "company": "Tech Solutions BV",
                "email": "jan@techsolutions.nl",
                "phone": "+31 6 1234 5678",
            },
            {
                "name": "Maria Janssen",
                "company": "Data Insights",
                "email": "maria@data-insights.io",
                "phone": "+31 6 8765 4321",
            },
            {
                "name": "Pieter Bakker",
                "company": "Innovation Labs",
                "email": "pieter@innovationlabs.nl",
                "phone": "+31 6 9999 2222",
            },
        ]
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        layout.addWidget(self._build_list(), 0)
        self.detail = self._build_detail_card()
        layout.addWidget(self.detail, 1)
        self.list_widget.setCurrentRow(0)
        self._update_detail(0)

    def _build_list(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("Card")
        panel.setFixedWidth(320)
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(16, 16, 16, 16)
        panel_layout.setSpacing(12)

        header = QHBoxLayout()
        header.addWidget(QLabel("Contacten"))
        add_btn = QPushButton("+")
        add_btn.setFixedSize(32, 32)
        add_btn.setStyleSheet("background:#2563eb; color:white; border-radius:8px;")
        header.addWidget(add_btn, 0, Qt.AlignRight)
        panel_layout.addLayout(header)

        search = QLineEdit()
        search.setPlaceholderText("Zoek contacten…")
        panel_layout.addWidget(search)

        self.list_widget = QListWidget()
        for person in self.contacts:
            item = QListWidgetItem(person["name"])
            self.list_widget.addItem(item)
        self.list_widget.currentRowChanged.connect(self._update_detail)
        panel_layout.addWidget(self.list_widget, 1)
        panel_layout.addWidget(
            QLabel(f"{len(self.contacts)} contacten"), 0, Qt.AlignRight
        )
        return panel

    def _build_detail_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("Card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        self.name = QLabel()
        self.name.setStyleSheet("font-size:20px; font-weight:600;")
        self.company = QLabel()
        self.company.setStyleSheet("color:#9ca3af;")
        layout.addWidget(self.name)
        layout.addWidget(self.company)

        self.email = QLabel()
        self.phone = QLabel()
        layout.addWidget(self.email)
        layout.addWidget(self.phone)

        buttons = QHBoxLayout()
        mail_btn = QPushButton("E-mail sturen")
        mail_btn.setStyleSheet(
            "border:1px solid #374151; border-radius:8px; padding:6px 12px;"
        )
        call_btn = QPushButton("Bellen")
        call_btn.setStyleSheet(
            "background:#2563eb; color:white; border-radius:8px; padding:6px 12px;"
        )
        buttons.addWidget(mail_btn)
        buttons.addWidget(call_btn)
        layout.addLayout(buttons)

        notes = QLabel(
            "Laatste interactie: Demo ingepland voor volgende week donderdag."
        )
        notes.setWordWrap(True)
        notes.setStyleSheet("color:#9ca3af;")
        layout.addWidget(notes)
        layout.addStretch(1)
        return card

    def _update_detail(self, index: int):
        if index < 0 or index >= len(self.contacts):
            return
        contact = self.contacts[index]
        self.name.setText(contact["name"])
        self.company.setText(contact["company"])
        self.email.setText(f"✉ {contact['email']}")
        self.phone.setText(f"☎ {contact['phone']}")
