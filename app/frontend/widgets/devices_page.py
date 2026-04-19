from functools import partial
from typing import Optional

from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import (
    QDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
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
from ..translations import t, register_language_change_callback
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
        self.setMinimumWidth(240)
        self.setMaximumWidth(280)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(12)

        info = QVBoxLayout()
        info.setSpacing(4)

        name_label = QLabel(device.get("device_name") or t("devices_unknown_device"))
        name_label.setWordWrap(True)
        name_label.setStyleSheet("font-size:18px; font-weight:700;")
        info.addWidget(name_label)

        info.addWidget(self._build_status_badge())

        info.addWidget(self._line_with_icon("👤", device.get("user_name", "")))
        info.addWidget(self._line_with_icon("✉️", device.get("email", "")))

        actions = QHBoxLayout()
        actions.setSpacing(6)
        edit_btn = QPushButton(t("edit"))
        edit_btn.setCursor(Qt.PointingHandCursor)
        edit_btn.setStyleSheet(
            "QPushButton { border:1px solid #d4d4d8; border-radius:18px; padding:6px 14px; text-align:center; }"
            "QPushButton:hover { border-color:#111111; }"
        )
        edit_btn.setFixedHeight(36)
        delete_btn = QPushButton(t("delete"))
        delete_btn.setCursor(Qt.PointingHandCursor)
        delete_btn.setStyleSheet(
            "QPushButton { background:#facc15; color:#050505; border:none; border-radius:18px; padding:6px 14px; text-align:center; font-weight:600; }"
            "QPushButton:hover { background:#050505; color:#facc15; }"
        )
        delete_btn.setFixedHeight(36)
        edit_btn.clicked.connect(partial(on_edit, device))
        delete_btn.clicked.connect(partial(on_delete, device))
        actions.addWidget(edit_btn)
        actions.addWidget(delete_btn)
        layout.addLayout(info)
        layout.addLayout(actions)

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

    def _build_status_badge(self) -> QWidget:
        badge = QFrame()
        badge.setStyleSheet(self._status_style())
        badge_layout = QHBoxLayout(badge)
        badge_layout.setContentsMargins(14, 6, 14, 6)
        badge_layout.setSpacing(0)

        label = QLabel(self._status_text())
        label.setStyleSheet("background: transparent; border: none;")
        badge_layout.addWidget(label, 0, Qt.AlignLeft | Qt.AlignVCenter)
        return badge

    def _status_text(self) -> str:
        return t("devices_connected") if self.device.get("is_connected") else t("devices_not_connected")

    def _status_style(self) -> str:
        if self.device.get("is_connected"):
            return (
                "QFrame {"
                "  background:#f0fdf4;"
                "  border:1px solid #bbf7d0;"
                "  border-radius:14px;"
                "}"
                "QLabel { color:#16a34a; font-size:12px; font-weight:700; }"
            )
        return (
            "QFrame {"
            "  background:#f3f4f6;"
            "  border:1px solid #e5e7eb;"
            "  border-radius:14px;"
            "}"
            "QLabel { color:#6b7280; font-size:12px; font-weight:700; }"
        )


class DevicesPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        header = QHBoxLayout()
        header.addStretch(1)
        self._add_btn = QPushButton(t("devices_add_device"))
        self._add_btn.setCursor(Qt.PointingHandCursor)
        self._add_btn.setStyleSheet(
            "QPushButton {"
            "  background:#facc15;"
            "  color:#050505;"
            "  padding:10px 26px;"
            "  border-radius:20px;"
            "  font-weight:600;"
            "}"
            "QPushButton:hover { background:#050505; color:#facc15; }"
        )
        self._add_btn.setFixedHeight(40)
        self._add_btn.clicked.connect(self._open_add_dialog)
        header.addWidget(self._add_btn)
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
        self.list_layout = QGridLayout(self.list_container)
        self.list_layout.setContentsMargins(0, 0, 0, 0)
        self.list_layout.setHorizontalSpacing(16)
        self.list_layout.setVerticalSpacing(16)
        self.list_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.scroll_area.setWidget(self.list_container)
        layout.addWidget(self.scroll_area, 1)

        self.count_label = QLabel(t("devices_total_devices", count=0))
        self.count_label.setStyleSheet("color:#6b7280; font-size:12px;")
        layout.addWidget(self.count_label, 0, Qt.AlignLeft)

        self.devices: list[dict] = []
        self._refresh_timer = QTimer(self)
        self._refresh_timer.setInterval(5000)
        self._refresh_timer.timeout.connect(self._reload_devices)
        self._refresh_timer.start()
        self._reload_devices()

        register_language_change_callback(self._update_translations)

    def _update_translations(self) -> None:
        """Update UI elements when language changes."""
        self._add_btn.setText(t("devices_add_device"))
        self.count_label.setText(t("devices_total_devices", count=len(self.devices)))
        self._render_devices()

    def _render_devices(self):
        while self.list_layout.count():
            item = self.list_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        if not self.devices:
            empty_wrap = QWidget()
            empty_layout = QHBoxLayout(empty_wrap)
            empty_layout.setContentsMargins(0, 24, 0, 0)
            empty_layout.setSpacing(0)
            empty_layout.addWidget(
                self._build_add_card(
                    title_key="devices_empty_title",
                    subtitle_key="devices_empty_subtitle",
                ),
                0,
                Qt.AlignLeft | Qt.AlignTop,
            )
            empty_layout.addStretch(1)
            self.list_layout.addWidget(empty_wrap, 0, 0)
        else:
            columns = self._grid_columns()
            for idx, device in enumerate(self.devices):
                card = DeviceCard(device, self._open_edit_dialog, self._confirm_delete)
                row = idx // columns
                col = idx % columns
                self.list_layout.addWidget(card, row, col)

            add_card_index = len(self.devices)
            self.list_layout.addWidget(
                self._build_add_card(
                    title_key="devices_add_contact_title",
                    subtitle_key="devices_add_contact_subtitle",
                ),
                add_card_index // columns,
                add_card_index % columns,
            )
            for col in range(columns):
                self.list_layout.setColumnStretch(col, 1)

    def _build_add_card(self, *, title_key: str, subtitle_key: str) -> QPushButton:
        add_card = QPushButton()
        add_card.setCursor(Qt.PointingHandCursor)
        add_card.setFixedSize(230, 230)
        add_card.setStyleSheet(
            "QPushButton {"
            "  background:#ffffff;"
            "  border:1px solid #e5e7eb;"
            "  border-radius:28px;"
            "}"
            "QPushButton:hover { border-color:#facc15; background:#fffdf5; }"
        )
        add_card.clicked.connect(self._open_add_dialog)

        card_layout = QVBoxLayout(add_card)
        card_layout.setContentsMargins(24, 24, 24, 24)
        card_layout.setSpacing(12)
        card_layout.addStretch(1)

        plus_label = QLabel("+")
        plus_label.setAlignment(Qt.AlignCenter)
        plus_label.setStyleSheet("font-size:64px; font-weight:300; color:#111111;")
        card_layout.addWidget(plus_label)

        title = QLabel(t(title_key))
        title.setAlignment(Qt.AlignCenter)
        title.setWordWrap(True)
        title.setStyleSheet("font-size:18px; font-weight:700; color:#111111;")
        card_layout.addWidget(title)

        subtitle = QLabel(t(subtitle_key))
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("font-size:13px; color:#6b7280;")
        card_layout.addWidget(subtitle)
        card_layout.addStretch(1)

        return add_card

    def _grid_columns(self) -> int:
        viewport_width = self.scroll_area.viewport().width() if self.scroll_area else self.width()
        return max(1, min(5, viewport_width // 250))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.devices:
            self._render_devices()

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

        self.count_label.setText(t("devices_total_devices", count=len(self.devices)))
        self._render_devices()

    def _open_add_dialog(self) -> None:
        self._open_device_dialog()

    def _open_edit_dialog(self, device: dict) -> None:
        self._open_device_dialog(device)

    def _open_device_dialog(self, device: Optional[dict] = None) -> None:
        is_edit = device is not None
        dialog = OverlayDialog(self)
        dialog.setWindowTitle(
            t("devices_edit_device") if is_edit else t("devices_new_device_user")
        )

        dialog.card_layout.setContentsMargins(0, 0, 0, 0)
        dialog.card_layout.setSpacing(0)
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QScrollArea.NoFrame)
        scroll_area.setStyleSheet(
            "QScrollArea { background: transparent; border: none; }"
            "QScrollArea > QWidget > QWidget { background: transparent; }"
        )
        dialog.card_layout.addWidget(scroll_area)
        form_host = QWidget()
        form_host.setStyleSheet("background:#ffffff;")
        scroll_area.setWidget(form_host)
        form = QFormLayout(form_host)
        form.setRowWrapPolicy(QFormLayout.WrapAllRows)
        form.setContentsMargins(32, 26, 32, 28)
        form.setSpacing(8)
        form.setVerticalSpacing(16)
        form.setLabelAlignment(Qt.AlignLeft)
        user_name_edit = QLineEdit()
        email_edit = QLineEdit()
        password_edit = QLineEdit()
        password_edit.setEchoMode(QLineEdit.Password)
        confirm_edit = QLineEdit()
        confirm_edit.setEchoMode(QLineEdit.Password)
        device_name_edit = QLineEdit()

        for widget in [
            user_name_edit,
            email_edit,
            password_edit,
            confirm_edit,
            device_name_edit,
        ]:
            widget.setStyleSheet(
                "QLineEdit {"
                "  background:#ffffff;"
                "  border:1px solid #d4d4d8;"
                "  border-radius:18px;"
                "  padding:10px 14px;"
                "  min-height:38px;"
                "}"
                "QLineEdit:focus { border-color:#facc15; }"
            )

        password_row = QHBoxLayout()
        password_row.setContentsMargins(0, 0, 0, 0)
        password_row.addWidget(password_edit)
        toggle_btn = QPushButton(t("devices_show"))
        toggle_btn.setCheckable(True)
        toggle_btn.setStyleSheet(
            "QPushButton { background:#f3f4f6; color:#0f172a; min-width:78px; min-height:36px; border-radius:18px; font-size:12px; text-align:center; }"
            "QPushButton:hover { background:#e5e7eb; }"
        )

        def _toggle_password(checked: bool) -> None:
            if checked:
                password_edit.setEchoMode(QLineEdit.Normal)
                confirm_edit.setEchoMode(QLineEdit.Normal)
                toggle_btn.setText(t("devices_hide"))
            else:
                password_edit.setEchoMode(QLineEdit.Password)
                confirm_edit.setEchoMode(QLineEdit.Password)
                toggle_btn.setText(t("devices_show"))

        toggle_btn.toggled.connect(_toggle_password)
        password_row.addWidget(toggle_btn)
        password_container = QWidget()
        password_container.setLayout(password_row)

        if device:
            user_name_edit.setText(device.get("user_name", ""))
            email_edit.setText(device.get("email", ""))
            password_edit.setText(device.get("password", ""))
            confirm_edit.setText(device.get("password", ""))
            device_name_edit.setText(device.get("device_name", ""))

        form.addRow(t("devices_username"), user_name_edit)
        form.addRow(t("devices_email"), email_edit)
        form.addRow(t("devices_password"), password_container)
        form.addRow(t("devices_repeat_password"), confirm_edit)
        form.addRow(t("devices_device_name"), device_name_edit)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(16)
        btn_row.addStretch(1)
        cancel_btn = QPushButton(t("cancel"))
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.setFixedSize(120, 36)
        cancel_btn.setStyleSheet(
            "QPushButton {"
            "  background:#facc15;"
            "  color:#050505;"
            "  border:none;"
            "  border-radius:18px;"
            "  text-align:center;"
            "  font-weight:600;"
            "}"
            "QPushButton:hover { background:#050505; color:#facc15; }"
        )
        cancel_btn.clicked.connect(dialog.reject)
        save_btn = QPushButton(t("save"))
        save_btn.setCursor(Qt.PointingHandCursor)
        save_btn.setFixedSize(120, 36)
        save_btn.setStyleSheet(
            "QPushButton {"
            "  background:#facc15;"
            "  color:#050505;"
            "  border:none;"
            "  border-radius:18px;"
            "  text-align:center;"
            "  font-weight:600;"
            "}"
            "QPushButton:hover { background:#050505; color:#facc15; }"
        )
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
                t("invalid"),
                t("devices_username_device_required"),
            )
            return

        if password != password2:
            show_warning_dialog(
                self,
                t("error"),
                t("devices_passwords_dont_match"),
            )
            return

        payload = {
            "user_name": user_name,
            "email": email_edit.text().strip(),
            "password": password,
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
                t("error"),
                f"{t('devices_could_not_save')}\n{exc}",
            )
            return

        self._reload_devices()

    def _confirm_delete(self, device: dict) -> None:
        answer = ask_yes_no_dialog(
            self,
            t("delete"),
            t("devices_confirm_delete", device_name=device.get("device_name", "")),
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
                t("error"),
                f"{t('devices_could_not_delete')}\n{exc}",
            )
            return

        self._reload_devices()

    @staticmethod
    def _auth_headers() -> dict:
        if BACKEND_BEARER_TOKEN:
            return {"Authorization": f"Bearer {BACKEND_BEARER_TOKEN}"}
        return {}
