from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

import requests

BACKEND_HTTP = "http://127.0.0.1:8000"


class ContactsPage(QWidget):
    def __init__(self):
        super().__init__()
        self.contacts = []
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        layout.addWidget(self._build_list(), 0)
        self.detail = self._build_detail_card()
        layout.addWidget(self.detail, 1)
        self._reload_contacts()

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
        add_btn.clicked.connect(self._open_add_dialog)
        header.addWidget(add_btn, 0, Qt.AlignRight)
        panel_layout.addLayout(header)

        search = QLineEdit()
        search.setPlaceholderText("Zoek contacten…")
        panel_layout.addWidget(search)

        self.list_widget = QListWidget()
        self.list_widget.currentRowChanged.connect(self._update_detail)
        panel_layout.addWidget(self.list_widget, 1)
        self.count_label = QLabel("0 contacten")
        panel_layout.addWidget(self.count_label, 0, Qt.AlignRight)
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

        self.notes = QLabel()
        self.notes.setWordWrap(True)
        self.notes.setStyleSheet("color:#9ca3af;")
        layout.addWidget(self.notes)
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
        self.notes.setText(contact.get("notes", ""))

    def _reload_contacts(self) -> None:
        try:
            resp = requests.get(f"{BACKEND_HTTP}/contacts", timeout=5)
            resp.raise_for_status()
            self.contacts = resp.json()
        except Exception:
            self.contacts = []

        self.list_widget.clear()
        for person in self.contacts:
            item = QListWidgetItem(person["name"])
            self.list_widget.addItem(item)
        self.count_label.setText(f"{len(self.contacts)} contacten")
        if self.contacts:
            self.list_widget.setCurrentRow(0)
            self._update_detail(0)

    def _open_add_dialog(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle("Nieuw contact")

        form = QFormLayout(dialog)
        name_edit = QLineEdit()
        company_edit = QLineEdit()
        email_edit = QLineEdit()
        phone_edit = QLineEdit()
        notes_edit = QLineEdit()

        form.addRow("Naam", name_edit)
        form.addRow("Bedrijf", company_edit)
        form.addRow("E-mail", email_edit)
        form.addRow("Telefoon", phone_edit)
        form.addRow("Notities", notes_edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel, parent=dialog
        )
        form.addRow(buttons)

        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)

        if dialog.exec() != QDialog.Accepted:
            return

        name = name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Ongeldig", "Naam is verplicht.")
            return

        payload = {
            "name": name,
            "company": company_edit.text().strip(),
            "email": email_edit.text().strip(),
            "phone": phone_edit.text().strip(),
            "notes": notes_edit.text().strip(),
        }

        try:
            resp = requests.post(f"{BACKEND_HTTP}/contacts", json=payload, timeout=5)
            resp.raise_for_status()
            contact = resp.json()
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Fout",
                f"Contact kon niet worden opgeslagen:\n{exc}",
            )
            return

        self.contacts.append(contact)
        self.list_widget.addItem(QListWidgetItem(contact["name"]))
        self.count_label.setText(f"{len(self.contacts)} contacten")
        self.list_widget.setCurrentRow(len(self.contacts) - 1)
