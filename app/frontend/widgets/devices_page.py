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
    QVBoxLayout,
    QWidget,
)

import requests

BACKEND_HTTP = "http://127.0.0.1:8000"


class DevicesPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        header = QVBoxLayout()
        title = QLabel("Connected Devices & Gebruikersbeheer")
        title.setStyleSheet("font-size:20px; font-weight:600;")
        subtitle = QLabel(
            "Beheer verbonden apparaten en gebruikersaccounts voor het systeem"
        )
        subtitle.setStyleSheet("color:#9ca3af;")
        header.addWidget(title)
        header.addWidget(subtitle)
        layout.addLayout(header)

        top_actions = QHBoxLayout()
        self.summary_label = QLabel("0 devices")
        top_actions.addWidget(self.summary_label)
        top_actions.addStretch(1)
        add_btn = QPushButton("Apparaat toevoegen")
        add_btn.setStyleSheet(
            "background:#2563eb; color:white; border-radius:8px; padding:6px 12px;"
        )
        add_btn.clicked.connect(self._open_add_dialog)
        top_actions.addWidget(add_btn)
        layout.addLayout(top_actions)

        self.grid = QGridLayout()
        self.grid.setSpacing(12)
        layout.addLayout(self.grid)

        self._reload_devices()

    def _device_card(self, device: dict) -> QFrame:
        card = QFrame()
        card.setObjectName("Card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        header = QHBoxLayout()
        name = QLabel(device.get("device_name", "Onbekend apparaat"))
        name.setStyleSheet("font-weight:600;")
        header.addWidget(name)
        layout.addLayout(header)

        layout.addWidget(QLabel(f"Gebruiker: {device['user_name']}"))
        layout.addWidget(QLabel(f"E-mail: {device['email']}"))
        layout.addWidget(QLabel(f"Telefoon: {device['phone']}"))
        layout.addWidget(QLabel(f"Device naam: {device['device_name']}"))

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
        dialog = QDialog(self)
        dialog.setWindowTitle("Nieuw apparaat & gebruiker")

        form = QFormLayout(dialog)
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
