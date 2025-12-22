from functools import partial
from typing import Optional

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QStyle,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

import requests

from ..config import BACKEND_HTTP
from .dialog_style import MODAL_QSS


class DevicesPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 0, 16, 8)
        layout.setSpacing(6)

        header = QHBoxLayout()
        header.setSpacing(12)
        header.setContentsMargins(0, 0, 0, 0)
        title_block = QVBoxLayout()
        title_block.setSpacing(2)
        title_block.setContentsMargins(0, 0, 0, 0)
        self.summary_label = QLabel("0 devices")
        self.summary_label.setStyleSheet(
            "color:#6b7280; letter-spacing:0.2em; font-size:11px;"
        )
        title_block.addWidget(self.summary_label)
        header.addLayout(title_block)
        header.addStretch(1)
        add_btn = QPushButton("Apparaat toevoegen")
        add_btn.setStyleSheet(
            "QPushButton {"
            "  background:#facc15;"
            "  color:#050505;"
            "  border-radius:20px;"
            "  padding:10px 28px;"
            "  font-weight:600;"
            "}"
            "QPushButton:hover { background:#050505; color:#facc15; }"
        )
        add_btn.setFixedHeight(40)
        add_btn.clicked.connect(self._open_add_dialog)
        header.addWidget(add_btn)
        layout.addLayout(header)

        grid_wrapper = QWidget()
        grid_wrapper_layout = QVBoxLayout(grid_wrapper)
        grid_wrapper_layout.setContentsMargins(0, 0, 0, 0)

        self.grid = QGridLayout()
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setSpacing(16)
        grid_wrapper_layout.addLayout(self.grid)
        layout.addWidget(grid_wrapper)

        self.devices: list[dict] = []
        self._reload_devices()

    def _device_card(self, device: dict) -> QFrame:
        card = QFrame()
        card.setObjectName("DeviceCard")
        card.setStyleSheet(
            """
            QFrame#DeviceCard {
                background-color: #ffffff;
                border-radius: 28px;
                border: 1px solid #e5e7eb;
                box-shadow: 0 12px 30px rgba(15, 23, 42, 0.06);
            }
            QLabel {
                color: #111111;
            }
            """
        )
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        header = QHBoxLayout()
        name = QLabel(device.get("device_name", "Onbekend apparaat"))
        name.setStyleSheet("font-weight:700; letter-spacing:0.02em; color:#111111;")
        header.addWidget(name)
        header.addStretch(1)

        edit_btn = QToolButton()
        edit_btn.setToolTip("Bewerken")
        edit_btn.setText("✏️")
        edit_btn.setIconSize(edit_btn.size())
        edit_btn.clicked.connect(partial(self._open_edit_dialog, device))
        edit_btn.setStyleSheet(
            "QToolButton { border:none; font-size:16px; }"
            "QToolButton:hover { opacity:0.8; }"
        )
        header.addWidget(edit_btn)

        delete_btn = QToolButton()
        delete_btn.setToolTip("Verwijderen")
        delete_btn.setText("🗑️")
        delete_btn.setIconSize(delete_btn.size())
        delete_btn.clicked.connect(partial(self._confirm_delete, device))
        delete_btn.setStyleSheet(
            "QToolButton { border:none; font-size:16px; }"
            "QToolButton:hover { opacity:0.8; }"
        )
        header.addWidget(delete_btn)

        layout.addLayout(header)

        meta = QVBoxLayout()
        for label, value in (
            ("Gebruiker", device.get("user_name", "")),
            ("E-mail", device.get("email", "")),
            ("Telefoon", device.get("phone", "")),
        ):
            row = QLabel(f"{label}: {value or '-'}")
            row.setStyleSheet(
                "color:#111111; background:#f9fafb; border-radius:20px; padding:10px 16px;"
            )
            meta.addWidget(row)
        layout.addLayout(meta)

        return card

    def _reload_devices(self) -> None:
        try:
            resp = requests.get(f"{BACKEND_HTTP}/devices", timeout=5)
            resp.raise_for_status()
            self.devices = resp.json()
        except Exception:
            self.devices = []

        # Clear grid
        while self.grid.count():
            item = self.grid.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)

        for idx, device in enumerate(self.devices):
            self.grid.addWidget(self._device_card(device), idx // 2, idx % 2)

        self.summary_label.setText(f"{len(self.devices)} devices")

    def _open_add_dialog(self) -> None:
        self._open_device_dialog()

    def _open_edit_dialog(self, device: dict) -> None:
        self._open_device_dialog(device)

    def _open_device_dialog(self, device: Optional[dict] = None) -> None:
        is_edit = device is not None
        dialog = QDialog(self)
        dialog.setWindowTitle(
            "Apparaat bewerken" if is_edit else "Nieuw apparaat & gebruiker"
        )
        dialog.setStyleSheet(MODAL_QSS)

        dialog_layout = QVBoxLayout(dialog)
        dialog_layout.setContentsMargins(0, 0, 0, 0)
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QScrollArea.NoFrame)
        dialog_layout.addWidget(scroll_area)
        form_host = QWidget()
        scroll_area.setWidget(form_host)
        form = QFormLayout(form_host)
        form.setContentsMargins(24, 24, 24, 24)
        user_name_edit = QLineEdit()
        email_edit = QLineEdit()
        password_edit = QLineEdit()
        password_edit.setEchoMode(QLineEdit.Password)
        confirm_edit = QLineEdit()
        confirm_edit.setEchoMode(QLineEdit.Password)
        phone_edit = QLineEdit()
        device_name_edit = QLineEdit()

        password_row = QHBoxLayout()
        password_row.addWidget(password_edit)
        toggle_btn = QPushButton("Toon")
        toggle_btn.setCheckable(True)

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

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel, parent=dialog
        )
        form.addRow(buttons)

        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)

        if dialog.exec() != QDialog.Accepted:
            return

        user_name = user_name_edit.text().strip()
        device_name = device_name_edit.text().strip()
        password = password_edit.text()
        password2 = confirm_edit.text()
        if not user_name or not device_name:
            QMessageBox.warning(
                self,
                "Ongeldig",
                "Naam gebruiker en device naam zijn verplicht.",
            )
            return

        if password != password2:
            QMessageBox.warning(
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
                    f"{BACKEND_HTTP}/devices/{device['id']}", json=payload, timeout=5
                )
            else:
                resp = requests.post(f"{BACKEND_HTTP}/devices", json=payload, timeout=5)
            resp.raise_for_status()
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Fout",
                f"Device kon niet worden opgeslagen:\n{exc}",
            )
            return

        self._reload_devices()

    def _confirm_delete(self, device: dict) -> None:
        answer = QMessageBox.question(
            self,
            "Verwijderen",
            f"Weet je zeker dat je '{device.get('device_name')}' wilt verwijderen?",
        )
        if answer != QMessageBox.Yes:
            return

        try:
            resp = requests.delete(
                f"{BACKEND_HTTP}/devices/{device['id']}", timeout=5
            )
            resp.raise_for_status()
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Fout",
                f"Device kon niet worden verwijderd:\n{exc}",
            )
            return

        self._reload_devices()
