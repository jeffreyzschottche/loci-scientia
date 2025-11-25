from __future__ import annotations

from PySide6.QtCore import Qt, Signal
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
    view_on_map_requested = Signal(dict)
    add_location_requested = Signal(dict, bool)
    contacts_updated = Signal(str)

    def __init__(self):
        super().__init__()
        self.contacts: list[dict] = []
        self.current_contact: dict | None = None
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        layout.addWidget(self._build_list(), 0)
        self.detail = self._build_detail_card()
        layout.addWidget(self.detail, 1)
        self.reload_contacts()

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

        self.add_location_btn = QPushButton("Voeg locatie toe via kaart")
        self.add_location_btn.setEnabled(False)
        self.add_location_btn.clicked.connect(self._request_location_assignment)
        layout.addWidget(self.add_location_btn, 0, Qt.AlignLeft)
        self.add_location_btn.hide()

        self.change_location_btn = QPushButton("Wijzig locatie via kaart")
        self.change_location_btn.clicked.connect(self._request_location_update)
        layout.addWidget(self.change_location_btn, 0, Qt.AlignLeft)
        self.change_location_btn.hide()

        self.remove_location_btn = QPushButton("Verwijder locatie")
        self.remove_location_btn.clicked.connect(self._remove_location)
        layout.addWidget(self.remove_location_btn, 0, Qt.AlignLeft)
        self.remove_location_btn.hide()

        self.view_on_map_btn = QPushButton("Bekijk op kaart")
        self.view_on_map_btn.setEnabled(False)
        self.view_on_map_btn.clicked.connect(self._open_map_for_contact)
        layout.addWidget(self.view_on_map_btn, 0, Qt.AlignLeft)
        self.view_on_map_btn.hide()

        actions = QHBoxLayout()
        actions.setSpacing(8)
        self.edit_contact_btn = QPushButton("Bewerk contact")
        self.edit_contact_btn.clicked.connect(self._open_edit_dialog)
        actions.addWidget(self.edit_contact_btn)
        self.delete_contact_btn = QPushButton("Verwijder contact")
        self.delete_contact_btn.clicked.connect(self._delete_current_contact)
        actions.addWidget(self.delete_contact_btn)
        actions.addStretch(1)
        layout.addLayout(actions)
        self.edit_contact_btn.setEnabled(False)
        self.delete_contact_btn.setEnabled(False)

        layout.addStretch(1)
        return card

    def _update_detail(self, index: int) -> None:
        if index < 0 or index >= len(self.contacts):
            self.current_contact = None
            self.view_on_map_btn.setEnabled(False)
            self.view_on_map_btn.hide()
            self.add_location_btn.setEnabled(False)
            self.add_location_btn.hide()
            self.change_location_btn.hide()
            self.remove_location_btn.hide()
            self.edit_contact_btn.setEnabled(False)
            self.delete_contact_btn.setEnabled(False)
            return
        contact = self.contacts[index]
        self.current_contact = contact
        self.name.setText(contact.get("name", ""))
        self.company.setText(contact.get("company", ""))
        self.email.setText(f"✉ {contact.get('email', '')}")
        self.phone.setText(f"☎ {contact.get('phone', '')}")
        self.notes.setText(contact.get("notes", ""))

        summary, coords = self._format_location(contact)
        self.location_summary.setText(summary)
        self.location_coords.setText(coords)
        has_coords = contact.get("location_lat") is not None and contact.get(
            "location_lon"
        ) is not None
        self.view_on_map_btn.setEnabled(has_coords)
        self.view_on_map_btn.setVisible(has_coords)
        self.add_location_btn.setVisible(not has_coords)
        self.add_location_btn.setEnabled(not has_coords)
        self.change_location_btn.setVisible(has_coords)
        self.change_location_btn.setEnabled(has_coords)
        self.remove_location_btn.setVisible(has_coords)
        self.remove_location_btn.setEnabled(has_coords)
        self.edit_contact_btn.setEnabled(True)
        self.delete_contact_btn.setEnabled(True)

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

    def _open_map_for_contact(self) -> None:
        if not self.current_contact:
            return
        lat = self.current_contact.get("location_lat")
        lon = self.current_contact.get("location_lon")
        if lat is None or lon is None:
            QMessageBox.information(
                self,
                "Geen locatie",
                "Dit contact heeft nog geen GPS-locatie.",
            )
            return
        self.view_on_map_requested.emit(self.current_contact)

    def _request_location_assignment(self) -> None:
        if not self.current_contact:
            return
        self.add_location_requested.emit(self.current_contact, False)

    def _request_location_update(self) -> None:
        if not self.current_contact:
            return
        self.add_location_requested.emit(self.current_contact, True)

    def _current_contact_id(self) -> str | None:
        if not self.current_contact:
            return None
        cid = self.current_contact.get("id")
        return str(cid) if cid is not None else None

    def reload_contacts(self, *, select_id: str | None = None) -> None:
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
        target_index = 0
        if select_id:
            for idx, person in enumerate(self.contacts):
                pid = person.get("id")
                if pid is not None and str(pid) == str(select_id):
                    target_index = idx
                    break
        if self.contacts:
            self.list_widget.setCurrentRow(target_index)
            self._update_detail(target_index)
        else:
            self.current_contact = None
            self.view_on_map_btn.setEnabled(False)
            self.view_on_map_btn.hide()
            self.add_location_btn.setEnabled(False)
            self.add_location_btn.hide()
            self.change_location_btn.hide()
            self.remove_location_btn.hide()
            self.edit_contact_btn.setEnabled(False)
            self.delete_contact_btn.setEnabled(False)

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
        if contact_id is not None:
            self.contacts_updated.emit(str(contact_id))
        needs_location = contact.get("location_lat") is None or contact.get(
            "location_lon"
        ) is None
        link_via_map = mode == "save_and_map" and needs_location
        if needs_location and not link_via_map:
            choice = QMessageBox.question(
                self,
                "Locatie toevoegen",
                "Contact is opgeslagen. Wil je nu een locatie koppelen via de kaart?",
            )
            link_via_map = choice == QMessageBox.Yes
        if link_via_map:
            force_pin = bool(contact.get("location_lat") is not None and contact.get("location_lon") is not None)
            self.add_location_requested.emit(contact, force_pin)

    def _open_edit_dialog(self) -> None:
        if not self.current_contact:
            return
        contact_id = self._current_contact_id()
        dialog = ContactFormDialog(
            self,
            title="Contact bewerken",
            initial=self.current_contact,
        )
        if dialog.exec() != QDialog.Accepted or not contact_id:
            return

        payload = dialog.payload()
        mode = dialog.save_mode()
        try:
            resp = requests.patch(
                f"{BACKEND_HTTP}/contacts/{contact_id}",
                json=payload,
                timeout=BACKEND_TIMEOUT,
            )
            resp.raise_for_status()
            updated = resp.json()
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Fout",
                f"Contact kon niet worden bijgewerkt:\n{exc}",
            )
            return

        self.contacts_updated.emit(contact_id)
        self.reload_contacts(select_id=contact_id)
        if mode == "save_and_map":
            self.add_location_requested.emit(updated, True)

    def _delete_current_contact(self) -> None:
        contact_id = self._current_contact_id()
        if not contact_id or not self.current_contact:
            return
        confirm = QMessageBox.question(
            self,
            "Verwijderen",
            f"Weet je zeker dat je {self.current_contact.get('name', 'dit contact')} wilt verwijderen?",
        )
        if confirm != QMessageBox.Yes:
            return
        try:
            resp = requests.delete(
                f"{BACKEND_HTTP}/contacts/{contact_id}",
                timeout=BACKEND_TIMEOUT,
            )
            resp.raise_for_status()
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Fout",
                f"Contact kon niet worden verwijderd:\n{exc}",
            )
            return
        self.contacts_updated.emit(contact_id)
        self.reload_contacts()

    def _remove_location(self) -> None:
        contact_id = self._current_contact_id()
        if not contact_id:
            return
        confirm = QMessageBox.question(
            self,
            "Locatie verwijderen",
            "Weet je zeker dat je de locatiegegevens voor dit contact wilt verwijderen?",
        )
        if confirm != QMessageBox.Yes:
            return
        payload = {
            "location_label": None,
            "location_street": None,
            "location_city": None,
            "location_region": None,
            "location_country": None,
            "location_context": None,
            "location_lat": None,
            "location_lon": None,
        }
        try:
            resp = requests.patch(
                f"{BACKEND_HTTP}/contacts/{contact_id}",
                json=payload,
                timeout=BACKEND_TIMEOUT,
            )
            resp.raise_for_status()
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Fout",
                f"Locatie kon niet worden verwijderd:\n{exc}",
            )
            return
        self.contacts_updated.emit(contact_id)
        self.reload_contacts(select_id=contact_id)
