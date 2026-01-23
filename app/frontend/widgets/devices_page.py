from functools import partial
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

import requests

from ..config import BACKEND_BEARER_TOKEN, BACKEND_HTTP
from .dialog_style import (
    OverlayDialog,
    ask_yes_no_dialog,
    show_error_dialog,
    show_warning_dialog,
)


class DeviceCard(QFrame):
    def __init__(self, device: dict, on_edit, on_delete):
        super().__init__()
        self.device = device
        self.setObjectName("DeviceCard")
        self.setStyleSheet(
            "QFrame#DeviceCard { background:#ffffff; border:1px solid #e5e7eb; border-radius:20px; }"
        )
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 14, 20, 14)
        layout.setSpacing(16)

        info = QVBoxLayout()
        info.setSpacing(4)

        name_label = QLabel(device.get("device_name", "Onbekend apparaat"))
        name_label.setStyleSheet("font-size:18px; font-weight:700;")
        info.addWidget(name_label)

        info.addWidget(self._line_with_icon("👤", device.get("user_name", "")))
        info.addWidget(self._line_with_icon("✉️", device.get("email", "")))
        info.addWidget(self._line_with_icon("☎️", device.get("phone", "")))

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
        edit_btn.clicked.connect(partial(on_edit, device))
        delete_btn.clicked.connect(partial(on_delete, device))
        actions.addWidget(edit_btn)
        actions.addWidget(delete_btn)
        actions.addStretch(1)
        info.addLayout(actions)

        layout.addLayout(info, 1)

    def _line_with_icon(self, icon: str, text: str) -> QWidget:
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)
        icon_label = QLabel(icon)
        icon_label.setFixedWidth(18)
        label = QLabel(text or "-")
        label.setStyleSheet("color:#4b5563;")
        row.addWidget(icon_label, 0, Qt.AlignTop)
        row.addWidget(label, 1)
        container = QWidget()
        container.setLayout(row)
        return container


class DevicesPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        header = QHBoxLayout()
        header.addStretch(1)
        add_btn = QPushButton("+ Apparaat toevoegen")
        add_btn.setCursor(Qt.PointingHandCursor)
        add_btn.setStyleSheet(
            "QPushButton {"
            "  background:#facc15;"
            "  color:#050505;"
            "  padding:10px 26px;"
            "  border-radius:20px;"
            "  font-weight:600;"
            "}"
            "QPushButton:hover { background:#050505; color:#facc15; }"
        )
        add_btn.setFixedHeight(40)
        add_btn.clicked.connect(self._open_add_dialog)
        header.addWidget(add_btn)
        layout.addLayout(header)

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

        self.count_label = QLabel("Totaal: 0 apparaten")
        self.count_label.setStyleSheet("color:#6b7280; font-size:12px;")
        layout.addWidget(self.count_label, 0, Qt.AlignLeft)

        self.devices: list[dict] = []
        self._reload_devices()

    def _render_devices(self):
        while self.list_layout.count():
            item = self.list_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        if not self.devices:
            placeholder = QLabel("Geen apparaten gevonden.")
            placeholder.setStyleSheet("color:#9ca3af; font-style:italic;")
            placeholder.setAlignment(Qt.AlignCenter)
            placeholder.setMinimumHeight(160)
            self.list_layout.addWidget(placeholder)
        else:
            for device in self.devices:
                card = DeviceCard(device, self._open_edit_dialog, self._confirm_delete)
                self.list_layout.addWidget(card)
            self.list_layout.addStretch(1)

    def _reload_devices(self) -> None:
        try:
            resp = requests.get(
                f"{BACKEND_HTTP}/devices",
                timeout=5,
                headers=self._auth_headers(),
            )
            resp.raise_for_status()
            self.devices = resp.json()
        except Exception:
            self.devices = []

        self.count_label.setText(f"Totaal: {len(self.devices)} apparaten")
        self._render_devices()

    def _open_add_dialog(self) -> None:
        self._open_device_dialog()

    def _open_edit_dialog(self, device: dict) -> None:
        self._open_device_dialog(device)

    def _open_device_dialog(self, device: Optional[dict] = None) -> None:
        is_edit = device is not None
        dialog = OverlayDialog(self)
        dialog.setWindowTitle(
            "Apparaat bewerken" if is_edit else "Nieuw apparaat & gebruiker"
        )

        dialog.card_layout.setContentsMargins(0, 0, 0, 0)
        dialog.card_layout.setSpacing(0)
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QScrollArea.NoFrame)
        dialog.card_layout.addWidget(scroll_area)
        form_host = QWidget()
        scroll_area.setWidget(form_host)
        form = QFormLayout(form_host)
        form.setRowWrapPolicy(QFormLayout.WrapAllRows)
        form.setContentsMargins(28, 24, 28, 24)
        form.setSpacing(6)
        form.setVerticalSpacing(14)
        user_name_edit = QLineEdit()
        email_edit = QLineEdit()
        password_edit = QLineEdit()
        password_edit.setEchoMode(QLineEdit.Password)
        confirm_edit = QLineEdit()
        confirm_edit.setEchoMode(QLineEdit.Password)
        phone_edit = QLineEdit()
        device_name_edit = QLineEdit()

        password_row = QHBoxLayout()
        password_row.setContentsMargins(0, 0, 0, 0)
        password_row.addWidget(password_edit)
        toggle_btn = QPushButton("Toon")
        toggle_btn.setCheckable(True)
        toggle_btn.setStyleSheet(
            "QPushButton { background:#f3f4f6; color:#0f172a; min-width:70px; min-height:36px; border-radius:18px; font-size:12px; }"
            "QPushButton:hover { background:#e5e7eb; }"
        )

        def _toggle_password(checked: bool) -> None:
            if checked:
                password_edit.setEchoMode(QLineEdit.Normal)
                confirm_edit.setEchoMode(QLineEdit.Normal)
                toggle_btn.setText("Verberg")
            else:
                password_edit.setEchoMode(QLineEdit.Password)
                confirm_edit.setEchoMode(QLineEdit.Password)
                toggle_btn.setText("Toon")

        toggle_btn.toggled.connect(_toggle_password)
        password_row.addWidget(toggle_btn)
        password_container = QWidget()
        password_container.setLayout(password_row)

        if device:
            user_name_edit.setText(device.get("user_name", ""))
            email_edit.setText(device.get("email", ""))
            password_edit.setText(device.get("password", ""))
            confirm_edit.setText(device.get("password", ""))
            phone_edit.setText(device.get("phone", ""))
            device_name_edit.setText(device.get("device_name", ""))

        form.addRow("Naam gebruiker", user_name_edit)
        form.addRow("E-mail", email_edit)
        form.addRow("Wachtwoord", password_container)
        form.addRow("Herhaal wachtwoord", confirm_edit)
        form.addRow("Telefoon (06)", phone_edit)
        form.addRow("Device naam", device_name_edit)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(16)
        btn_row.addStretch(1)
        cancel_btn = QPushButton("Annuleren")
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.setFixedSize(120, 36)
        cancel_btn.clicked.connect(dialog.reject)
        save_btn = QPushButton("Opslaan")
        save_btn.setCursor(Qt.PointingHandCursor)
        save_btn.setFixedSize(120, 36)
        save_btn.clicked.connect(dialog.accept)
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(save_btn)
        btn_row.addStretch(1)
        form.addRow(btn_row)

        if dialog.exec() != QDialog.Accepted:
            return

        user_name = user_name_edit.text().strip()
        device_name = device_name_edit.text().strip()
        password = password_edit.text()
        password2 = confirm_edit.text()
        if not user_name or not device_name:
            show_warning_dialog(
                self,
                "Ongeldig",
                "Naam gebruiker en device naam zijn verplicht.",
            )
            return

        if password != password2:
            show_warning_dialog(
                self,
                "Ongeldig",
                "De wachtwoorden komen niet overeen.",
            )
            return

        payload = {
            "user_name": user_name,
            "email": email_edit.text().strip(),
            "password": password,
            "phone": phone_edit.text().strip(),
            "device_name": device_name,
        }

        try:
            if is_edit:
                resp = requests.patch(
                    f"{BACKEND_HTTP}/devices/{device['id']}",
                    json=payload,
                    timeout=5,
                    headers=self._auth_headers(),
                )
            else:
                resp = requests.post(
                    f"{BACKEND_HTTP}/devices",
                    json=payload,
                    timeout=5,
                    headers=self._auth_headers(),
                )
            resp.raise_for_status()
        except Exception as exc:
            show_error_dialog(
                self,
                "Fout",
                f"Device kon niet worden opgeslagen:\n{exc}",
            )
            return

        self._reload_devices()

    def _confirm_delete(self, device: dict) -> None:
        answer = ask_yes_no_dialog(
            self,
            "Verwijderen",
            f"Weet je zeker dat je '{device.get('device_name')}' wilt verwijderen?",
        )
        if not answer:
            return

        try:
            resp = requests.delete(
                f"{BACKEND_HTTP}/devices/{device['id']}",
                timeout=5,
                headers=self._auth_headers(),
            )
            resp.raise_for_status()
        except Exception as exc:
            show_error_dialog(
                self,
                "Fout",
                f"Device kon niet worden verwijderd:\n{exc}",
            )
            return

        self._reload_devices()

    @staticmethod
    def _auth_headers() -> dict:
        if BACKEND_BEARER_TOKEN:
            return {"Authorization": f"Bearer {BACKEND_BEARER_TOKEN}"}
        return {}
