from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

import requests

from ..config import BACKEND_HTTP, BACKEND_TIMEOUT
from .contact_form import ContactFormDialog


class ContactCard(QFrame):
    edit_requested = Signal(dict)
    delete_requested = Signal(dict)
    map_requested = Signal(dict)
    add_location_requested = Signal(dict)

    def __init__(self, contact: dict):
        super().__init__()
        self.contact = contact
        self.setObjectName("Card")
        self.setStyleSheet(
            "QFrame#Card { background:#ffffff; border:1px solid #e5e7eb; border-radius:20px; }"
        )
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 14, 20, 14)
        layout.setSpacing(16)

        info = QVBoxLayout()
        info.setSpacing(4)

        name_row = QHBoxLayout()
        name_label = QLabel(contact.get("name", "Onbekend"))
        name_label.setStyleSheet("font-size:18px; font-weight:700;")
        name_row.addWidget(name_label)
        name_row.addStretch(1)
        layout.addLayout(info, 1)

        contact_icon = QLabel("👤")
        contact_icon.setFixedSize(36, 36)
        contact_icon.setAlignment(Qt.AlignCenter)
        contact_icon.setStyleSheet(
            "background:#ffffff; border:1px solid #e4e4e7; border-radius:18px; font-size:16px;"
        )

        info.addLayout(name_row)
        info.addWidget(self._line_with_icon("✉️", contact.get("email", "")))
        info.addWidget(self._line_with_icon("☎️", contact.get("phone", "")))
        info.addWidget(self._build_location_row())

        actions = QHBoxLayout()
        actions.setSpacing(6)
        edit_btn = QPushButton("Bewerk")
        edit_btn.setCursor(Qt.PointingHandCursor)
        edit_btn.setStyleSheet(
            "QPushButton { border:1px solid #d4d4d8; border-radius:20px; padding:6px 16px; }"
            "QPushButton:hover { border-color:#111111; }"
        )
        edit_btn.setFixedHeight(40)
        delete_btn = QPushButton("Verwijder")
        delete_btn.setCursor(Qt.PointingHandCursor)
        delete_btn.setStyleSheet(
            "QPushButton { background:#111111; color:#ffffff; border-radius:20px; padding:6px 16px; }"
            "QPushButton:hover { background:#facc15; color:#050505; }"
        )
        delete_btn.setFixedHeight(40)
        edit_btn.clicked.connect(lambda: self.edit_requested.emit(contact))
        delete_btn.clicked.connect(lambda: self.delete_requested.emit(contact))
        actions.addWidget(edit_btn)
        actions.addWidget(delete_btn)
        actions.addStretch(1)
        info.addLayout(actions)

    def _line_with_icon(self, icon: str, text: str) -> QWidget:
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)
        icon_label = QLabel(icon)
        icon_label.setFixedWidth(18)
        label = QLabel(text)
        label.setStyleSheet("color:#4b5563;")
        row.addWidget(icon_label, 0, Qt.AlignTop)
        row.addWidget(label, 1)
        container = QWidget()
        container.setLayout(row)
        return container

    def _build_location_row(self) -> QWidget:
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)
        icon_label = QLabel("📍")
        icon_label.setFixedWidth(18)
        row.addWidget(icon_label, 0, Qt.AlignTop)

        location_line = self.contact.get("location_label") or self.contact.get(
            "location_street"
        )
        city = self.contact.get("location_city")
        if location_line and city:
            location_line = f"{location_line}, {city}"
        label = QLabel(location_line or "Geen locatie gekoppeld")
        label.setStyleSheet("color:#4b5563;")
        row.addWidget(label, 1)

        has_location = (
            self.contact.get("location_lat") is not None
            and self.contact.get("location_lon") is not None
        )
        action_btn = QPushButton("Op kaart" if has_location else "Locatie koppelen")
        action_btn.setCursor(Qt.PointingHandCursor)
        action_btn.setStyleSheet(
            "QPushButton { border:1px solid #d4d4d8; border-radius:14px; padding:4px 14px; font-size:12px; }"
            "QPushButton:hover { border-color:#111111; }"
        )
        action_btn.setFixedHeight(28)
        if has_location:
            action_btn.clicked.connect(lambda: self.map_requested.emit(self.contact))
        else:
            action_btn.clicked.connect(
                lambda: self.add_location_requested.emit(self.contact)
            )
        row.addWidget(action_btn, 0, Qt.AlignRight)

        container = QWidget()
        container.setLayout(row)
        return container


class ContactsPage(QWidget):
    view_on_map_requested = Signal(dict)
    add_location_requested = Signal(dict, bool)
    contacts_updated = Signal(str)

    def __init__(self):
        super().__init__()
        self.contacts: list[dict] = []
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        header = QHBoxLayout()
        title_section = QVBoxLayout()
        title = QLabel("Contacten")
        title.setStyleSheet("font-size:32px; font-weight:800; letter-spacing:0.02em;")
        subtitle = QLabel("Beheer je contacten en bekijk ze op de kaart")
        subtitle.setStyleSheet("color:#6b7280; font-size:14px; letter-spacing:0.04em;")
        title_section.addWidget(title)
        title_section.addWidget(subtitle)
        header.addLayout(title_section)
        header.addStretch(1)
        add_btn = QPushButton("+ Contact toevoegen")
        add_btn.setCursor(Qt.PointingHandCursor)
        add_btn.setStyleSheet(
            "QPushButton { background:#facc15; color:#050505; padding:10px 26px; border-radius:20px; font-weight:600; }"
            "QPushButton:hover { background:#050505; color:#facc15; }"
        )
        add_btn.setFixedHeight(40)
        add_btn.clicked.connect(self._open_add_dialog)
        header.addWidget(add_btn)
        layout.addLayout(header)

        search = QLineEdit()
        search.setPlaceholderText("Zoek contacten…")
        search.textChanged.connect(self._filter_contacts)
        layout.addWidget(search)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setStyleSheet(
            "QScrollArea { background: transparent; border: none; }"
            "QScrollArea > QWidget > QWidget { background: transparent; }"
        )
        self.list_container = QWidget()
        self.list_container.setStyleSheet("background: transparent;")
        self.list_layout = QVBoxLayout(self.list_container)
        self.list_layout.setContentsMargins(0, 0, 0, 0)
        self.list_layout.setSpacing(12)
        self.scroll_area.setWidget(self.list_container)
        layout.addWidget(self.scroll_area, 1)

        self.count_label = QLabel("Totaal: 0 contacten")
        self.count_label.setStyleSheet("color:#6b7280; font-size:12px;")
        layout.addWidget(self.count_label, 0, Qt.AlignLeft)

        self.filtered_contacts: list[dict] = []
        self.reload_contacts()

    def _filter_contacts(self, query: str):
        query = query.strip().lower()
        if not query:
            self.filtered_contacts = list(self.contacts)
        else:
            self.filtered_contacts = [
                c
                for c in self.contacts
                if query in (c.get("name") or "").lower()
                or query in (c.get("email") or "").lower()
                or query in (c.get("phone") or "").lower()
            ]
        self._render_contacts()

    def _render_contacts(self):
        while self.list_layout.count():
            item = self.list_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        if not self.filtered_contacts:
            placeholder = QLabel("Geen contacten gevonden.")
            placeholder.setStyleSheet("color:#9ca3af; font-style:italic;")
            placeholder.setAlignment(Qt.AlignCenter)
            placeholder.setMinimumHeight(160)
            self.list_layout.addWidget(placeholder)
        else:
            for contact in self.filtered_contacts:
                card = ContactCard(contact)
                card.edit_requested.connect(self._handle_edit_requested)
                card.delete_requested.connect(self._handle_delete_requested)
                card.map_requested.connect(self._handle_view_map)
                card.add_location_requested.connect(self._handle_location_assignment)
                self.list_layout.addWidget(card)

    def reload_contacts(self, *, select_id: str | None = None) -> None:
        try:
            resp = requests.get(f"{BACKEND_HTTP}/contacts", timeout=BACKEND_TIMEOUT)
            resp.raise_for_status()
            self.contacts = resp.json()
        except Exception:
            self.contacts = []
        self.filtered_contacts = list(self.contacts)
        self.count_label.setText(f"Totaal: {len(self.contacts)} contacten")
        self._render_contacts()

    def _handle_view_map(self, contact: dict):
        lat = contact.get("location_lat")
        lon = contact.get("location_lon")
        if lat is None or lon is None:
            QMessageBox.information(
                self,
                "Geen locatie",
                "Dit contact heeft nog geen GPS-locatie.",
            )
            return
        self.view_on_map_requested.emit(contact)

    def _handle_location_assignment(self, contact: dict):
        self.add_location_requested.emit(contact, False)

    def _open_add_dialog(self) -> None:
        dialog = ContactFormDialog(self)
        if dialog.exec() != QDialog.Accepted:
            return

        payload = dialog.payload()
        mode = dialog.save_mode()
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

        contact_id = contact.get("id")
        self.reload_contacts(select_id=str(contact_id) if contact_id is not None else None)
        updated = self._find_contact_by_id(contact_id)
        if contact_id is not None:
            self.contacts_updated.emit(str(contact_id))
        if updated:
            self._maybe_request_location(updated, mode)

    def _handle_edit_requested(self, contact: dict):
        dialog = ContactFormDialog(
            self,
            title="Contact bewerken",
            initial=contact,
        )
        if dialog.exec() != QDialog.Accepted:
            return
        contact_id = contact.get("id")
        if contact_id is None:
            return
        payload = dialog.payload()
        mode = dialog.save_mode()
        try:
            requests.patch(
                f"{BACKEND_HTTP}/contacts/{contact_id}",
                json=payload,
                timeout=BACKEND_TIMEOUT,
            )
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Fout",
                f"Contact kon niet worden bijgewerkt:\n{exc}",
            )
            return
        self.reload_contacts(select_id=str(contact_id))
        updated = self._find_contact_by_id(contact_id)
        if updated:
            self._maybe_request_location(updated, mode)
        self.contacts_updated.emit(str(contact_id))

    def _handle_delete_requested(self, contact: dict):
        contact_id = contact.get("id")
        if contact_id is None:
            return
        confirm = QMessageBox.question(
            self,
            "Bevestig",
            f"Weet je zeker dat je {contact.get('name')} wilt verwijderen?",
        )
        if confirm != QMessageBox.Yes:
            return
        try:
            requests.delete(
                f"{BACKEND_HTTP}/contacts/{contact_id}", timeout=BACKEND_TIMEOUT
            )
        except Exception as exc:
            QMessageBox.critical(self, "Fout", f"Kon contact niet verwijderen:\n{exc}")
            return
        self.reload_contacts()
        self.contacts_updated.emit(str(contact_id))

    def _find_contact_by_id(self, contact_id):
        if contact_id is None:
            return None
        for contact in self.contacts:
            if str(contact.get("id")) == str(contact_id):
                return contact
        return None

    def _maybe_request_location(self, contact: dict, mode: str):
        needs_location = contact.get("location_lat") is None or contact.get(
            "location_lon"
        ) is None
        if not needs_location:
            return
        link_via_map = mode == "save_and_map"
        if not link_via_map:
            choice = QMessageBox.question(
                self,
                "Locatie toevoegen",
                "Wil je via de kaart een locatie koppelen?",
            )
            link_via_map = choice == QMessageBox.Yes
        if link_via_map:
            self.add_location_requested.emit(contact, False)
