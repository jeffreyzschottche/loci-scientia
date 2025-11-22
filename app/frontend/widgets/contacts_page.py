from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
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

from ..config import BACKEND_HTTP, BACKEND_TIMEOUT
from .contact_form import ContactFormDialog


class ContactsPage(QWidget):
    def __init__(self):
        super().__init__()
        self.contacts: list[dict] = []
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

        self.location_title = QLabel("Locatie")
        self.location_title.setStyleSheet("font-weight:600; margin-top:16px;")
        self.location_summary = QLabel("Nog geen locatie gekoppeld.")
        self.location_summary.setWordWrap(True)
        self.location_summary.setStyleSheet("color:#9ca3af;")
        self.location_coords = QLabel()
        self.location_coords.setStyleSheet("color:#9ca3af; font-size:11px;")

        layout.addWidget(self.location_title)
        layout.addWidget(self.location_summary)
        layout.addWidget(self.location_coords)

        layout.addStretch(1)
        return card

    def _update_detail(self, index: int) -> None:
        if index < 0 or index >= len(self.contacts):
            return
        contact = self.contacts[index]
        self.name.setText(contact.get("name", ""))
        self.company.setText(contact.get("company", ""))
        self.email.setText(f"✉ {contact.get('email', '')}")
        self.phone.setText(f"☎ {contact.get('phone', '')}")
        self.notes.setText(contact.get("notes", ""))

        summary, coords = self._format_location(contact)
        self.location_summary.setText(summary)
        self.location_coords.setText(coords)

    def _format_location(self, contact: dict) -> tuple[str, str]:
        label = contact.get("location_label") or contact.get("location_street")
        city = contact.get("location_city")
        region = contact.get("location_region")
        country = contact.get("location_country")
        lat = contact.get("location_lat")
        lon = contact.get("location_lon")
        context_bits = [bit for bit in [city, region, country] if bit]
        summary = label or city or "Nog geen locatie gekoppeld."
        if label and context_bits:
            summary = f"{label} — {', '.join(context_bits)}"
        elif context_bits and not label:
            summary = ", ".join(context_bits)
        coords = ""
        if lat is not None and lon is not None:
            coords = f"GPS: {lat:.5f}, {lon:.5f}"
        return summary, coords

    def _reload_contacts(self) -> None:
        try:
            resp = requests.get(f"{BACKEND_HTTP}/contacts", timeout=BACKEND_TIMEOUT)
            resp.raise_for_status()
            self.contacts = resp.json()
        except Exception:
            self.contacts = []

        self.list_widget.clear()
        for person in self.contacts:
            item = QListWidgetItem(person.get("name", "Onbekend"))
            self.list_widget.addItem(item)
        self.count_label.setText(f"{len(self.contacts)} contacten")
        if self.contacts:
            self.list_widget.setCurrentRow(0)
            self._update_detail(0)

    def _open_add_dialog(self) -> None:
        dialog = ContactFormDialog(self)
        if dialog.exec() != QDialog.Accepted:
            return

        payload = dialog.payload()
        try:
            resp = requests.post(
                f"{BACKEND_HTTP}/contacts", json=payload, timeout=BACKEND_TIMEOUT
            )
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
        self.list_widget.addItem(QListWidgetItem(contact.get("name", "Onbekend")))
        self.count_label.setText(f"{len(self.contacts)} contacten")
        self.list_widget.setCurrentRow(len(self.contacts) - 1)
