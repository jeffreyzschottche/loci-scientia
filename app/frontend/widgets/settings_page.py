from __future__ import annotations

import asyncio
import json
import os
import platform
import re
import shutil
import subprocess
from collections.abc import Coroutine
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo, available_timezones

import requests
from PySide6.QtCore import QDate, QObject, Qt, QTimer, Signal
from PySide6.QtGui import QFont, QPainter
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QListView,
    QPlainTextEdit,
    QProgressDialog,
    QPushButton,
    QSizePolicy,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ..config import BACKEND_BEARER_TOKEN, BACKEND_HTTP, OLLAMA_MODELS, PROMPT_MODES
from ..translations import get_current_language, register_language_change_callback, set_language, t
from .dialog_style import OverlayDialog, ask_yes_no_dialog, show_error_dialog
from .ios_switch import IosSwitch

class SettingsPage(QWidget):
    FIELD_STYLE = (
        "QComboBox, QDateEdit {"
        "  min-height: 44px;"
        "  padding: 0 16px;"
        "  border: 1px solid #e7e0d4;"
        "  border-radius: 16px;"
        "  background: #fffdf8;"
        "  color: #171717;"
        "  font-size: 14px;"
        "  font-weight: 600;"
        "}"
        "QComboBox[popupOpen='true'] {"
        "  border-bottom-left-radius: 0px;"
        "  border-bottom-right-radius: 0px;"
        "}"
        "QComboBox:hover, QDateEdit:hover {"
        "  border-color: #f0c94c;"
        "  background: #ffffff;"
        "}"
        "QComboBox:focus, QDateEdit:focus {"
        "  border: 2px solid #facc15;"
        "  background: #ffffff;"
        "}"
        "QComboBox::drop-down, QDateEdit::drop-down {"
        "  width: 34px;"
        "  border: none;"
        "}"
        "QComboBox QAbstractItemView {"
        "  background:#fffdf8;"
        "  color:#171717;"
        "  border:1px solid #e7e0d4;"
        "  selection-background-color:#facc15;"
        "  selection-color:#171717;"
        "  outline:0;"
        "}"
        "QComboBox QAbstractItemView::item {"
        "  min-height:34px;"
        "  padding:6px 12px;"
        "}"
        "QComboBox QAbstractItemView::item:hover {"
        "  background:#fff4cf;"
        "  color:#171717;"
        "}"
        "QComboBox QAbstractItemView::item:selected {"
        "  background:#facc15;"
        "  color:#171717;"
        "}"
    )

    def _schedule_task(self, coro: Coroutine[object, object, object]) -> None:
        loop = asyncio.get_event_loop()
        loop.create_task(coro)
    COMBO_POPUP_STYLE = (
        "QListView {"
        "  background:#fffdf8;"
        "  color:#171717;"
        "  border:1px solid #e7e0d4;"
        "  border-top:none;"
        "  border-bottom-left-radius:16px;"
        "  border-bottom-right-radius:16px;"
        "  outline:0;"
        "  padding:4px 0;"
        "}"
        "QListView::item {"
        "  min-height:34px;"
        "  padding:6px 12px;"
        "}"
        "QListView::item:hover {"
        "  background:#fff4cf;"
        "  color:#171717;"
        "}"
        "QListView::item:selected {"
        "  background:#facc15;"
        "  color:#171717;"
        "}"
    )

    def __init__(self):
        super().__init__()
        self._ollama_combo: QComboBox | None = None
        self._ollama_apply: QPushButton | None = None
        self._ollama_status: QLabel | None = None
        self._current_model: str | None = None
        self._saved_model: str = ""
        self._busy_dialog: QProgressDialog | None = None
        self._support_status: QLabel | None = None
        self._support_enable: QPushButton | None = None
        self._support_disable: QPushButton | None = None
        self._support_duration: QComboBox | None = None
        self._support_last_payload: dict[str, object] | None = None
        self._wifi_status: QLabel | None = None
        self._wifi_open_button: QPushButton | None = None
        self._wifi_last_info: dict[str, str] | None = None
        self._bluetooth_status: QLabel | None = None
        self._bluetooth_list: QListWidget | None = None
        self._bluetooth_connected_list: QListWidget | None = None
        self._bluetooth_scan_list: QListWidget | None = None
        self._bluetooth_content: QWidget | None = None
        self._bluetooth_toggle: QPushButton | None = None
        self._bluetooth_power_button: QPushButton | None = None
        self._bluetooth_repair_button: QPushButton | None = None
        self._bluetooth_refresh_button: QPushButton | None = None
        self._bluetooth_scan_button: QPushButton | None = None
        self._bluetooth_pair_button: QPushButton | None = None
        self._bluetooth_forget_button: QPushButton | None = None
        self._bluetooth_last_info: dict[str, object] | None = None
        self._timezone_combo: QComboBox | None = None
        self._timezone_loading = False
        self._language_combo: QComboBox | None = None
        self._date_edit: QDateEdit | None = None
        self._date_loading = False
        self._system_save_button: QPushButton | None = None
        self._system_reset_button: QPushButton | None = None
        self._kiosk_switch: IosSwitch | None = None
        self._kiosk_status: QLabel | None = None
        self._kiosk_busy = False
        self._saved_timezone: str = ""
        self._saved_language: str = ""
        self._saved_today: str = ""
        self._focus_mode_tabs: QWidget | None = None
        self._focus_mode_tabs_layout: QHBoxLayout | None = None
        self._focus_mode_buttons: dict[str, QPushButton] = {}
        self._focus_mode_selected: str = ""
        self._focus_mode_info: QLabel | None = None
        self._focus_mode_manage: QPushButton | None = None
        self._focus_mode_new: QPushButton | None = None
        self._ollama_reset: QPushButton | None = None
        self._ollama_description: QLabel | None = None
        self._builtin_modes = {"Developer", "Finance", "Law", "Child"}
        self._system_loading = False
        self._support_active = False
        self._support_duration_keys = ["settings_30_min", "settings_1_hour", "settings_2_hours"]
        self._support_duration_values = [30, 60, 120]
        self._support_refresh_timer = QTimer(self)
        self._support_refresh_timer.setInterval(30000)
        self._support_refresh_timer.timeout.connect(self._load_support_status)
        self._wifi_refresh_timer = QTimer(self)
        self._wifi_refresh_timer.setInterval(15000)
        self._wifi_refresh_timer.timeout.connect(self._refresh_wifi_status)
        self._bluetooth_refresh_timer = QTimer(self)
        self._bluetooth_refresh_timer.setInterval(15000)
        self._bluetooth_refresh_timer.timeout.connect(self._refresh_bluetooth_status)
        self._model_signals = ModelSwitchSignals()
        self._model_signals.progress.connect(self._on_model_progress)
        self._model_signals.done.connect(self._on_model_done)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        self._tabs = QTabWidget()
        self._tabs.setObjectName("SettingsTabs")
        self._tabs.addTab(self._system_tab(), t("settings_tab_system"))
        self._tabs.addTab(self._advanced_tab(), t("settings_tab_advanced"))
        self._tabs.addTab(self._ssh_tab(), t("settings_tab_ssh"))
        self._tabs.addTab(self._wifi_tab(), t("settings_tab_wifi"))
        self._tabs.addTab(self._bluetooth_tab(), t("settings_tab_bluetooth"))
        self._tabs.tabBar().setObjectName("SettingsTabsBar")
        layout.addWidget(self._tabs, 1)

        register_language_change_callback(self._update_translations)

        QTimer.singleShot(0, self._load_models)
        QTimer.singleShot(0, self._load_support_status)
        QTimer.singleShot(0, self._refresh_wifi_status)
        QTimer.singleShot(0, self._refresh_bluetooth_status)
        self._support_refresh_timer.start()
        self._wifi_refresh_timer.start()
        self._bluetooth_refresh_timer.start()

    def _system_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        card = self._settings_card()
        body = QWidget()
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(16)
        pref_grid = QGridLayout()
        pref_grid.setHorizontalSpacing(14)
        pref_grid.setVerticalSpacing(14)
        self._timezone_label = QLabel(t("settings_timezone"))
        self._timezone_combo = ChevronComboBox()
        self._style_combo_box(self._timezone_combo)
        self._timezone_combo.setMaxVisibleItems(18)
        timezones = self._available_timezones()
        self._timezone_loading = True
        self._system_loading = True
        self._timezone_combo.addItems(timezones)
        current_timezone = self._current_timezone()
        if current_timezone and current_timezone in timezones:
            self._timezone_combo.setCurrentText(current_timezone)
        elif "Europe/Amsterdam" in timezones:
            self._timezone_combo.setCurrentText("Europe/Amsterdam")
        self._timezone_loading = False
        self._timezone_combo.currentTextChanged.connect(self._on_system_preference_changed)
        pref_grid.addWidget(self._preference_field(self._timezone_label, self._timezone_combo), 0, 0)

        self._application_language_label = QLabel(t("settings_application_language"))
        self._language_combo = ChevronComboBox()
        self._style_combo_box(self._language_combo)
        for label, value in self._language_options():
            self._language_combo.addItem(label, value)
        current_language = self._current_language()
        if current_language:
            for index in range(self._language_combo.count()):
                if self._language_combo.itemData(index) == current_language:
                    self._language_combo.setCurrentIndex(index)
                    break
        self._language_combo.currentIndexChanged.connect(self._on_system_preference_changed)
        pref_grid.addWidget(self._preference_field(self._application_language_label, self._language_combo), 0, 1)

        self._today_label = QLabel(t("settings_today"))
        self._date_edit = ChevronDateEdit()
        self._date_edit.setStyleSheet(self.FIELD_STYLE)
        self._date_edit.setCalendarPopup(True)
        self._date_edit.setDisplayFormat("yyyy-MM-dd")
        self._date_loading = True
        self._date_edit.setDate(self._current_qdate())
        self._date_loading = False
        self._date_edit.dateChanged.connect(self._on_system_preference_changed)
        pref_grid.addWidget(self._preference_field(self._today_label, self._date_edit), 0, 2)
        body_layout.addLayout(pref_grid)

        actions = QHBoxLayout()
        actions.setContentsMargins(0, 0, 0, 0)
        actions.addStretch(1)
        self._system_reset_button = QPushButton(t("settings_reset"))
        self._system_reset_button.setCursor(Qt.PointingHandCursor)
        self._system_reset_button.clicked.connect(self._reset_system_preferences)
        self._system_save_button = QPushButton(t("settings_save"))
        self._system_save_button.setCursor(Qt.PointingHandCursor)
        self._system_save_button.clicked.connect(self._save_system_preferences)
        self._system_reset_button.setStyleSheet(self._action_button_style("secondary"))
        self._system_save_button.setStyleSheet(self._action_button_style("primary"))
        actions.addWidget(self._system_reset_button)
        actions.addWidget(self._system_save_button)
        body_layout.addLayout(actions)

        self._system_loading = False
        self._capture_saved_system_preferences()
        self._update_system_action_buttons()
        card.layout().addWidget(body)
        layout.addWidget(card)

        info_card = self._settings_card(t("settings_system_information"))
        info_body = QWidget()
        info_layout = QGridLayout(info_body)
        info_layout.setHorizontalSpacing(14)
        info_layout.setVerticalSpacing(14)

        system_info = [
            ("settings_device_prefix", self._env_display_value("DEVICE_NAME_PREFIX")),
            ("settings_device_number", self._env_display_value("DEVICE_NUMBER")),
            ("settings_backend_url", self._effective_backend_url()),
            ("settings_backend_port", self._env_display_value("BACKEND_PORT")),
            ("settings_backend_bind_host", self._env_display_value("BACKEND_BIND_HOST")),
            ("settings_api_routes_port", self._env_display_value("API_ROUTES_DEFAULT_PORT")),
            ("settings_admin_users", self._env_display_value("ADMIN_USERS")),
            ("settings_admin_device_id", self._env_display_value("ADMIN_DEVICE_ID")),
            ("settings_ollama_base_url", self._env_display_value("OLLAMA_BASE_URL")),
            ("settings_ollama_model_label", self._env_display_value("OLLAMA_MODEL")),
            ("settings_qdrant_devices_path", self._env_display_value("QDRANT_DEVICES_EMBEDDED_PATH")),
        ]
        self._system_info_labels: list[QLabel] = []
        for index, (label_key, value) in enumerate(system_info):
            label, pill = self._system_info_pill(t(label_key), value)
            row = index // 3
            column = index % 3
            info_layout.addWidget(pill, row, column)
            self._system_info_labels.append(label)

        info_card.layout().addWidget(info_body)
        layout.addWidget(info_card)

        if self._show_kiosk_toggle():
            layout.addWidget(self._kiosk_card())
            QTimer.singleShot(0, self._refresh_kiosk_state)

        layout.addStretch(1)
        return tab

    # ------------------------------------------------------------------ kiosk
    @staticmethod
    def _truthy(value: object) -> bool:
        return str(value or "").strip().lower() in {"1", "true", "yes", "on", "enable", "enabled"}

    def _show_kiosk_toggle(self) -> bool:
        raw = self._read_env_value("SHOW_KIOSK_TOGGLE")
        if raw is None:
            raw = os.environ.get("SHOW_KIOSK_TOGGLE", "")
        return self._truthy(raw)

    @staticmethod
    def _kiosk_script_path() -> Path:
        return Path(__file__).resolve().parents[3] / "scripts" / "aitje-kiosk-apply.sh"

    def _kiosk_card(self) -> QFrame:
        card = self._settings_card(t("settings_kiosk_title"))
        body = QWidget()
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(10)

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(16)

        text_col = QVBoxLayout()
        text_col.setContentsMargins(0, 0, 0, 0)
        text_col.setSpacing(4)
        label = QLabel(t("settings_kiosk_switch_label"))
        label.setStyleSheet("font-weight:700; color:#171717; font-size:14px;")
        text_col.addWidget(label)
        description = QLabel(t("settings_kiosk_description"))
        description.setWordWrap(True)
        description.setStyleSheet("color:#6b7280; font-size:13px; line-height:1.45;")
        text_col.addWidget(description)
        row.addLayout(text_col, 1)

        self._kiosk_switch = IosSwitch()
        self._kiosk_switch.toggled.connect(self._on_kiosk_toggled)
        row.addWidget(self._kiosk_switch, 0, Qt.AlignTop)
        body_layout.addLayout(row)

        self._kiosk_status = QLabel(t("settings_kiosk_status_loading"))
        self._kiosk_status.setWordWrap(True)
        self._kiosk_status.setStyleSheet("color:#6b7280; font-size:12px;")
        body_layout.addWidget(self._kiosk_status)

        card.layout().addWidget(body)
        return card

    def _set_kiosk_switch(self, state: bool) -> None:
        if not self._kiosk_switch:
            return
        # blockSignals so a programmatic set doesn't fire _on_kiosk_toggled.
        self._kiosk_switch.blockSignals(True)
        self._kiosk_switch.setChecked(state)
        self._kiosk_switch.blockSignals(False)

    def _read_kiosk_state(self) -> bool:
        if platform.system() != "Linux" or shutil.which("systemctl") is None:
            return False
        out = self._run_command(["systemctl", "is-enabled", "aitje-kiosk.service"], timeout=5).strip()
        return out == "enabled"

    def _refresh_kiosk_state(self) -> None:
        if not self._kiosk_switch:
            return
        self._schedule_task(self._refresh_kiosk_state_async())

    async def _refresh_kiosk_state_async(self) -> None:
        state = await asyncio.to_thread(self._read_kiosk_state)
        self._set_kiosk_switch(state)
        if self._kiosk_status:
            self._kiosk_status.setText(
                t("settings_kiosk_active") if state else t("settings_kiosk_inactive")
            )

    def _on_kiosk_toggled(self, checked: bool) -> None:
        if self._kiosk_busy:
            return
        self._schedule_task(self._apply_kiosk_async(bool(checked)))

    def _run_kiosk_helper(self, action: str) -> tuple[str, str]:
        """Run the privileged helper. Returns (status, output) where status is
        one of: 'ok', 'need_sudo' (passwordless sudo not set up yet — one-time
        bootstrap required), or 'error'. A status string avoids colliding with
        the helper's own numeric exit codes."""
        if platform.system() != "Linux":
            return ("error", t("settings_kiosk_linux_only"))
        script = self._kiosk_script_path()
        if not script.exists():
            return ("error", f"{script} ontbreekt")
        try:
            probe = subprocess.run(["sudo", "-n", "true"], capture_output=True, text=True, timeout=10)
        except Exception as exc:
            return ("error", str(exc))
        if probe.returncode != 0:
            return ("need_sudo", "")
        try:
            env = os.environ.copy()
            kiosk_env = "1" if self._truthy(env.get("AITJE_KIOSK")) else "0"
            completed = subprocess.run(
                ["sudo", "-n", "env", f"AITJE_KIOSK={kiosk_env}", str(script), action],
                capture_output=True,
                text=True,
                timeout=180,
            )
        except subprocess.TimeoutExpired:
            return ("error", "timeout")
        output = ((completed.stdout or "") + (completed.stderr or "")).strip()
        return ("ok" if completed.returncode == 0 else "error", output)

    async def _apply_kiosk_async(self, enable: bool) -> None:
        self._kiosk_busy = True
        # Disable the switch for the whole operation so a second click can't
        # desync the visual state from the in-flight apply.
        if self._kiosk_switch:
            self._kiosk_switch.setEnabled(False)
        if self._kiosk_status:
            self._kiosk_status.setText(t("settings_kiosk_applying"))
        action = "enable" if enable else "disable"
        status, output = await asyncio.to_thread(self._run_kiosk_helper, action)

        if status == "ok":
            if self._kiosk_status:
                self._kiosk_status.setText(
                    t("settings_kiosk_enabled_reboot") if enable else t("settings_kiosk_disabled_reboot")
                )
            self._kiosk_busy = False
            if self._kiosk_switch:
                self._kiosk_switch.setEnabled(True)
            # Show the reboot prompt from the Qt loop (not inside this coroutine)
            # so the modal's nested event loop runs at the top level.
            QTimer.singleShot(0, self._prompt_kiosk_reboot)
            return

        # Failure: re-sync the switch to the *actual* system state (don't assume
        # the operation left it untouched) and explain why.
        actual_state = await asyncio.to_thread(self._read_kiosk_state)
        self._set_kiosk_switch(actual_state)
        if self._kiosk_status:
            self._kiosk_status.setText(
                t("settings_kiosk_active") if actual_state else t("settings_kiosk_inactive")
            )
        self._kiosk_busy = False
        if self._kiosk_switch:
            self._kiosk_switch.setEnabled(True)
        if status == "need_sudo":
            message = t("settings_kiosk_needs_bootstrap", path=str(self._kiosk_script_path()))
        else:
            detail = output.strip()[:600]
            message = t("settings_kiosk_failed")
            if detail:
                message = f"{message}\n\n{detail}"
        QTimer.singleShot(0, lambda m=message: show_error_dialog(self, t("settings_kiosk_title"), m))

    def _prompt_kiosk_reboot(self) -> None:
        if ask_yes_no_dialog(
            self,
            t("settings_kiosk_reboot_title"),
            t("settings_kiosk_reboot_prompt"),
            default_to_no=True,
        ):
            self._reboot_device()

    def _reboot_device(self) -> str:
        return self._run_command(["sudo", "-n", "systemctl", "reboot"], timeout=15)

    def _advanced_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        focus_mode_card = self._settings_card(t("settings_focus_mode"))
        focus_mode_body = QWidget()
        focus_mode_layout = QVBoxLayout(focus_mode_body)
        focus_mode_layout.setContentsMargins(0, 0, 0, 0)
        focus_mode_layout.setSpacing(12)
        self._focus_mode_tabs = QWidget()
        self._focus_mode_tabs_layout = QHBoxLayout(self._focus_mode_tabs)
        self._focus_mode_tabs_layout.setContentsMargins(0, 0, 0, 0)
        self._focus_mode_tabs_layout.setSpacing(10)
        focus_mode_layout.addWidget(self._focus_mode_tabs)
        actions = QHBoxLayout()
        actions.setSpacing(10)
        self._focus_mode_new = QPushButton(t("settings_add_focus_mode"))
        self._focus_mode_manage = QPushButton(t("settings_edit_focus_mode"))
        self._focus_mode_new.clicked.connect(self._create_focus_mode)
        self._focus_mode_manage.clicked.connect(self._manage_focus_mode)
        for button, variant in (
            (self._focus_mode_new, "secondary"),
            (self._focus_mode_manage, "primary"),
        ):
            button.setCursor(Qt.PointingHandCursor)
            button.setStyleSheet(self._action_button_style(variant))
            actions.addWidget(button)
        actions.addStretch(1)
        focus_mode_layout.addLayout(actions)
        self._focus_mode_info = QLabel()
        self._focus_mode_info.setWordWrap(True)
        self._focus_mode_info.setStyleSheet("color:#6b7280; font-size:13px; line-height:1.45;")
        focus_mode_layout.addWidget(self._focus_mode_info)
        self._populate_focus_mode_options()
        focus_mode_card.layout().addWidget(focus_mode_body)
        layout.addWidget(focus_mode_card)

        model_card = self._settings_card(t("settings_ollama_model"))
        model_body = QWidget()
        model_layout = QGridLayout(model_body)
        model_layout.setHorizontalSpacing(12)
        model_layout.setVerticalSpacing(10)
        model_layout.setColumnStretch(1, 1)
        self._model_label = QLabel(t("settings_model"))
        model_layout.addWidget(self._model_label, 0, 0)
        self._ollama_combo = ChevronComboBox()
        self._style_combo_box(self._ollama_combo)
        self._ollama_combo.setEnabled(False)
        self._ollama_combo.currentTextChanged.connect(self._on_model_selection_changed)
        model_layout.addWidget(self._ollama_combo, 0, 1)
        self._ollama_apply = QPushButton(t("settings_use"))
        self._ollama_apply.setEnabled(False)
        self._ollama_apply.setCursor(Qt.PointingHandCursor)
        self._ollama_apply.setStyleSheet(self._compact_action_button_style("primary"))
        self._ollama_apply.clicked.connect(self._on_apply_model)
        model_layout.addWidget(self._ollama_apply, 0, 2)
        self._ollama_reset = QPushButton(t("settings_reset"))
        self._ollama_reset.setEnabled(False)
        self._ollama_reset.setCursor(Qt.PointingHandCursor)
        self._ollama_reset.setStyleSheet(self._compact_action_button_style("secondary"))
        self._ollama_reset.clicked.connect(self._reset_model_selection)
        model_layout.addWidget(self._ollama_reset, 0, 3)
        self._ollama_status = QLabel(t("settings_loading_models"))
        self._ollama_status.setStyleSheet("color:#6b7280; font-size:12px;")
        model_layout.addWidget(self._ollama_status, 1, 0, 1, 4)
        self._ollama_description = QLabel()
        self._ollama_description.setWordWrap(True)
        self._ollama_description.setStyleSheet("color:#6b7280; font-size:13px; line-height:1.45;")
        model_layout.addWidget(self._ollama_description, 2, 0, 1, 4)
        model_card.layout().addWidget(model_body)
        layout.addWidget(model_card)

        layout.addStretch(1)
        return tab

    def _ssh_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        support_card = self._settings_card(t("settings_remote_support"))
        support_body = QWidget()
        support_layout = QVBoxLayout(support_body)
        support_layout.setSpacing(10)
        self._support_hint = QLabel(t("settings_support_hint"))
        self._support_hint.setWordWrap(True)
        self._support_hint.setStyleSheet("color:#6b7280; font-size:12px;")
        support_layout.addWidget(self._support_hint)

        support_form = QGridLayout()
        support_form.setHorizontalSpacing(12)
        self._duration_label = QLabel(t("settings_duration"))
        support_form.addWidget(self._duration_label, 0, 0)
        self._support_duration = ChevronComboBox()
        self._style_combo_box(self._support_duration)
        for key in self._support_duration_keys:
            self._support_duration.addItem(t(key))
        support_form.addWidget(self._support_duration, 0, 1)
        support_layout.addLayout(support_form)

        self._support_status = QLabel(t("settings_support_status_loading"))
        self._support_status.setStyleSheet("color:#6b7280; font-size:12px;")
        support_layout.addWidget(self._support_status)

        support_actions = QHBoxLayout()
        support_actions.setSpacing(10)
        self._support_enable = QPushButton(t("settings_enable_support"))
        self._support_disable = QPushButton(t("settings_stop_support"))
        self._support_enable.setCursor(Qt.PointingHandCursor)
        self._support_disable.setCursor(Qt.PointingHandCursor)
        self._support_enable.setStyleSheet(self._compact_action_button_style("primary"))
        self._support_disable.setStyleSheet(self._compact_action_button_style("primary"))
        self._support_disable.setEnabled(False)
        support_actions.addWidget(self._support_enable)
        support_actions.addWidget(self._support_disable)
        support_actions.addStretch(1)
        support_layout.addLayout(support_actions)
        self._support_enable.clicked.connect(self._on_support_enable)
        self._support_disable.clicked.connect(self._on_support_disable)

        support_card.layout().addWidget(support_body)
        layout.addWidget(support_card)
        layout.addStretch(1)
        return tab

    def _wifi_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        card = self._settings_card(t("settings_wifi_title"))
        body = QWidget()
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(8)

        self._wifi_intro = QLabel(t("settings_wifi_intro"))
        self._wifi_intro.setWordWrap(True)
        self._wifi_intro.setStyleSheet("color:#6b7280; font-size:14px; line-height:1.4;")
        body_layout.addWidget(self._wifi_intro)

        self._wifi_status = QLabel(t("settings_wifi_status_loading"))
        self._wifi_status.setWordWrap(True)
        self._wifi_status.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self._wifi_status.setStyleSheet(
            "color:#111111; font-size:14px; font-weight:600; background:#fffdf8; border:1px solid #efe6d8; "
            "border-radius:18px; padding:16px; line-height:1.5;"
        )
        body_layout.addWidget(self._wifi_status)

        actions = QHBoxLayout()
        actions.setContentsMargins(0, 0, 0, 0)
        actions.setSpacing(10)
        self._wifi_open_button = QPushButton(t("settings_wifi_open"))
        self._wifi_open_button.setCursor(Qt.PointingHandCursor)
        self._wifi_open_button.setStyleSheet(self._action_button_style("primary"))
        self._wifi_open_button.clicked.connect(self._open_wifi_settings)
        actions.addWidget(self._wifi_open_button)
        actions.addStretch(1)
        body_layout.addLayout(actions)

        card.layout().addWidget(body)
        layout.addWidget(card)
        layout.addStretch(1)
        return tab

    def _open_wifi_settings(self) -> None:
        commands: list[list[str]] = []
        system = platform.system()
        if system == "Linux":
            commands = [
                ["iwgtk"],
                ["nm-connection-editor"],
                ["gnome-control-center", "wifi"],
                ["gnome-control-center", "network"],
            ]
        elif system == "Darwin":
            commands = [
                ["open", "x-apple.systempreferences:com.apple.Network-Settings.extension"],
                ["open", "/System/Library/PreferencePanes/Network.prefPane"],
            ]
        elif system == "Windows":
            commands = [["cmd", "/c", "start", "", "ms-settings:network-wifi"]]

        for command in commands:
            executable = command[0]
            if executable not in {"open", "cmd"} and shutil.which(executable) is None:
                continue
            try:
                subprocess.Popen(command)
                return
            except Exception:
                continue
        show_error_dialog(self, t("error"), t("settings_wifi_open_failed"))

    def _bluetooth_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        card = self._settings_card(t("settings_bluetooth_title"))
        body = QWidget()
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(10)

        toggle_row = QHBoxLayout()
        toggle_row.setContentsMargins(0, 0, 0, 0)
        self._bluetooth_intro = QLabel("")
        self._bluetooth_intro.setVisible(False)
        toggle_row.addStretch(1)
        self._bluetooth_toggle = QPushButton(t("settings_bluetooth_toggle_off"))
        self._bluetooth_toggle.setCheckable(True)
        self._bluetooth_toggle.setCursor(Qt.PointingHandCursor)
        self._bluetooth_toggle.setStyleSheet(self._action_button_style("secondary"))
        self._bluetooth_toggle.clicked.connect(self._toggle_bluetooth)
        toggle_row.addWidget(self._bluetooth_toggle, 0)
        body_layout.addLayout(toggle_row)

        self._bluetooth_content = QWidget()
        content_layout = QVBoxLayout(self._bluetooth_content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(10)

        self._bluetooth_status = QLabel("")
        self._bluetooth_status.setWordWrap(True)
        self._bluetooth_status.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self._bluetooth_status.setStyleSheet("color:#6b7280; font-size:13px;")
        content_layout.addWidget(self._bluetooth_status)

        self._bluetooth_connected_title = QLabel(t("settings_bluetooth_connected_devices"))
        self._bluetooth_connected_title.setStyleSheet("font-weight:700; color:#171717;")
        content_layout.addWidget(self._bluetooth_connected_title)

        self._bluetooth_connected_list = QListWidget()
        self._bluetooth_connected_list.setMinimumHeight(140)
        self._style_bluetooth_list(self._bluetooth_connected_list)
        content_layout.addWidget(self._bluetooth_connected_list)

        connected_actions = QHBoxLayout()
        connected_actions.setContentsMargins(0, 0, 0, 0)
        self._bluetooth_forget_button = QPushButton(t("settings_bluetooth_forget"))
        self._bluetooth_forget_button.setCursor(Qt.PointingHandCursor)
        self._bluetooth_forget_button.setStyleSheet(self._action_button_style("secondary"))
        self._bluetooth_forget_button.clicked.connect(self._forget_selected_bluetooth_device)
        connected_actions.addWidget(self._bluetooth_forget_button)
        connected_actions.addStretch(1)
        content_layout.addLayout(connected_actions)

        self._bluetooth_scan_title = QLabel(t("settings_bluetooth_scan_results"))
        self._bluetooth_scan_title.setStyleSheet("font-weight:700; color:#171717;")
        content_layout.addWidget(self._bluetooth_scan_title)

        self._bluetooth_scan_list = QListWidget()
        self._bluetooth_scan_list.setMinimumHeight(180)
        self._style_bluetooth_list(self._bluetooth_scan_list)
        content_layout.addWidget(self._bluetooth_scan_list)

        actions = QHBoxLayout()
        actions.setContentsMargins(0, 0, 0, 0)
        actions.setSpacing(10)
        self._bluetooth_scan_button = QPushButton(t("settings_bluetooth_scan"))
        self._bluetooth_pair_button = QPushButton(t("settings_bluetooth_pair_connect"))
        for button, variant in (
            (self._bluetooth_scan_button, "secondary"),
            (self._bluetooth_pair_button, "primary"),
        ):
            button.setCursor(Qt.PointingHandCursor)
            button.setStyleSheet(self._action_button_style(variant))
            actions.addWidget(button)
        actions.addStretch(1)
        self._bluetooth_scan_button.clicked.connect(self._scan_bluetooth_devices)
        self._bluetooth_pair_button.clicked.connect(self._pair_selected_bluetooth_device)
        content_layout.addLayout(actions)
        body_layout.addWidget(self._bluetooth_content)
        self._bluetooth_content.setVisible(False)

        card.layout().addWidget(body)
        layout.addWidget(card)
        layout.addStretch(1)
        return tab

    @staticmethod
    def _style_bluetooth_list(list_widget: QListWidget) -> None:
        list_widget.setStyleSheet(
            "QListWidget { background:#fffdf8; border:1px solid #efe6d8; border-radius:18px; padding:8px; }"
            "QListWidget::item { min-height:38px; padding:8px 10px; border-radius:12px; color:#171717; }"
            "QListWidget::item:selected { background:#facc15; color:#111111; }"
        )

    def _refresh_bluetooth_status(self) -> None:
        if self._bluetooth_status:
            self._bluetooth_status.setText(t("settings_bluetooth_status_loading"))
        self._schedule_task(self._refresh_bluetooth_status_async())

    async def _refresh_bluetooth_status_async(self) -> None:
        info = await asyncio.to_thread(self._read_bluetooth_info)
        self._bluetooth_last_info = info
        self._apply_bluetooth_info(info)

    def _toggle_bluetooth(self) -> None:
        checked = bool(self._bluetooth_toggle and self._bluetooth_toggle.isChecked())
        self._schedule_task(self._set_bluetooth_enabled_async(checked))

    async def _set_bluetooth_enabled_async(self, enabled: bool) -> None:
        if self._bluetooth_status and enabled:
            self._bluetooth_status.setText(t("settings_bluetooth_powering_on"))
        output = await asyncio.to_thread(self._set_bluetooth_enabled, enabled)
        info = await asyncio.to_thread(self._read_bluetooth_info)
        if output and info.get("powered") != ("yes" if enabled else "no"):
            info["user_note"] = t("settings_bluetooth_toggle_failed")
            self._log_bluetooth_error("set_enabled", output)
        self._bluetooth_last_info = info
        self._apply_bluetooth_info(info)

    def _set_bluetooth_enabled(self, enabled: bool) -> str:
        return self._run_bluetoothctl(["power", "on" if enabled else "off"], 10)

    def _power_on_bluetooth(self) -> None:
        self._schedule_task(self._power_on_bluetooth_async())

    async def _power_on_bluetooth_async(self) -> None:
        if self._bluetooth_status:
            self._bluetooth_status.setText(t("settings_bluetooth_powering_on"))
        power_output = await asyncio.to_thread(self._power_on_bluetooth_adapter)
        info = await asyncio.to_thread(self._read_bluetooth_info)
        if power_output:
            info["note"] = power_output
        self._bluetooth_last_info = info
        self._apply_bluetooth_info(info)

    def _repair_bluetooth(self) -> None:
        self._schedule_task(self._repair_bluetooth_async())

    async def _repair_bluetooth_async(self) -> None:
        if self._bluetooth_status:
            self._bluetooth_status.setText(t("settings_bluetooth_repairing"))
        repair_output = await asyncio.to_thread(self._repair_bluetooth_stack)
        info = await asyncio.to_thread(self._read_bluetooth_info)
        if repair_output:
            info["note"] = repair_output
        self._bluetooth_last_info = info
        self._apply_bluetooth_info(info)

    def _scan_bluetooth_devices(self) -> None:
        self._schedule_task(self._scan_bluetooth_devices_async())

    async def _scan_bluetooth_devices_async(self) -> None:
        if self._bluetooth_status:
            self._bluetooth_status.setText(t("settings_bluetooth_scanning"))
        scan_output = await asyncio.to_thread(self._scan_bluetooth_devices_blocking)
        info = await asyncio.to_thread(self._read_bluetooth_info)
        if scan_output and self._is_bluetooth_error(scan_output):
            self._log_bluetooth_error("scan", scan_output)
            info["user_note"] = t("settings_bluetooth_scan_failed")
        self._bluetooth_last_info = info
        self._apply_bluetooth_info(info)

    def _pair_selected_bluetooth_device(self) -> None:
        if not self._bluetooth_scan_list:
            return
        item = self._bluetooth_scan_list.currentItem()
        if item is None:
            if self._bluetooth_status:
                self._bluetooth_status.setText(t("settings_bluetooth_select_device"))
            return
        mac = item.data(Qt.UserRole)
        if not mac:
            return
        self._schedule_task(self._pair_bluetooth_device_async(str(mac)))

    async def _pair_bluetooth_device_async(self, mac: str) -> None:
        if self._bluetooth_status:
            self._bluetooth_status.setText(t("settings_bluetooth_pairing", device=mac))
        result = await asyncio.to_thread(self._pair_bluetooth_device, mac)
        if result and self._is_bluetooth_error(result):
            self._log_bluetooth_error("pair_connect", result)
        info = await asyncio.to_thread(self._read_bluetooth_info)
        if result and self._is_bluetooth_error(result):
            info["user_note"] = t("settings_bluetooth_pair_failed")
        self._bluetooth_last_info = info
        self._apply_bluetooth_info(info)

    def _forget_selected_bluetooth_device(self) -> None:
        if not self._bluetooth_connected_list:
            return
        item = self._bluetooth_connected_list.currentItem()
        if item is None:
            if self._bluetooth_status:
                self._bluetooth_status.setText(t("settings_bluetooth_select_device"))
            return
        mac = item.data(Qt.UserRole)
        if mac:
            self._schedule_task(self._forget_bluetooth_device_async(str(mac)))

    async def _forget_bluetooth_device_async(self, mac: str) -> None:
        result = await asyncio.to_thread(self._forget_bluetooth_device, mac)
        if result and self._is_bluetooth_error(result):
            self._log_bluetooth_error("forget", result)
        info = await asyncio.to_thread(self._read_bluetooth_info)
        if result and self._is_bluetooth_error(result):
            info["user_note"] = t("settings_bluetooth_forget_failed")
        self._bluetooth_last_info = info
        self._apply_bluetooth_info(info)

    def _pair_bluetooth_device(self, mac: str) -> str:
        outputs = [
            self._run_bluetoothctl(["agent", "KeyboardDisplay"], 10),
            self._run_bluetoothctl(["default-agent"], 10),
            self._run_bluetoothctl(["trust", mac], 15),
            self._run_bluetoothctl(["pair", mac], 60),
            self._run_bluetoothctl(["connect", mac], 30),
            self._activate_bluetooth_audio(mac),
            self._collect_bluetooth_profile_debug(mac),
        ]
        return "\n".join(output for output in outputs if output).strip()

    def _forget_bluetooth_device(self, mac: str) -> str:
        return self._run_bluetoothctl(["remove", mac], 20)

    def _activate_bluetooth_audio(self, mac: str) -> str:
        if shutil.which("pactl") is None:
            return ""
        sinks = self._run_command(["pactl", "list", "short", "sinks"], timeout=5)
        mac_token = mac.replace(":", "_").lower()
        selected_sink = ""
        for line in sinks.splitlines():
            parts = line.split()
            if len(parts) < 2:
                continue
            sink_name = parts[1]
            lowered = sink_name.lower()
            if "bluez" in lowered and mac_token in lowered:
                selected_sink = sink_name
                break
            if "bluetooth" in lowered and mac_token in lowered:
                selected_sink = sink_name
                break
        if not selected_sink:
            return ""
        return self._run_command(["pactl", "set-default-sink", selected_sink], timeout=5)

    def _collect_bluetooth_profile_debug(self, mac: str) -> str:
        sections = [self._run_bluetoothctl(["info", mac], 5)]
        if shutil.which("pactl"):
            sections.append("pactl sinks:\n" + self._run_command(["pactl", "list", "short", "sinks"], timeout=5))
            sections.append("pactl cards:\n" + self._run_command(["pactl", "list", "short", "cards"], timeout=5))
        return "\n".join(section for section in sections if section).strip()

    def _power_on_bluetooth_adapter(self) -> str:
        output = self._run_bluetoothctl(["power", "on"], 10)
        state = self._read_bluetooth_power_state()
        if state == "yes":
            return output
        message = t("settings_bluetooth_power_on_failed")
        return "\n".join(part for part in (output, message) if part).strip()

    def _repair_bluetooth_stack(self) -> str:
        outputs: list[str] = []
        if shutil.which("rfkill"):
            outputs.append(self._run_command(["rfkill", "unblock", "bluetooth"], timeout=10))
        if shutil.which("systemctl"):
            outputs.append(self._run_command(["systemctl", "start", "bluetooth"], timeout=15))
        if shutil.which("hciconfig"):
            outputs.append(self._run_command(["hciconfig", "hci0", "up"], timeout=10))
        outputs.append(self._power_on_bluetooth_adapter())
        return "\n".join(output for output in outputs if output).strip()

    def _scan_bluetooth_devices_blocking(self) -> str:
        if self._read_bluetooth_power_state() != "yes":
            return t("settings_bluetooth_power_required")
        return self._run_bluetoothctl(["--timeout", "12", "scan", "on"], 16)

    def _read_bluetooth_power_state(self) -> str:
        if platform.system() != "Linux" or shutil.which("bluetoothctl") is None:
            return ""
        for line in self._run_bluetoothctl(["show"], 5).splitlines():
            stripped = line.strip()
            if stripped.startswith("Powered:"):
                return stripped.split(":", 1)[1].strip()
        return ""

    def _read_bluetooth_info(self) -> dict[str, object]:
        system = platform.system()
        info: dict[str, object] = {"platform": system, "devices": []}
        if system != "Linux":
            info["note"] = t("settings_bluetooth_linux_only")
            return info
        if shutil.which("bluetoothctl") is None:
            info["note"] = t("settings_bluetoothctl_missing")
            return info

        show_output = self._run_bluetoothctl(["show"], 5)
        for line in show_output.splitlines():
            stripped = line.strip()
            if stripped.startswith("Name:"):
                info["adapter"] = stripped.split(":", 1)[1].strip()
            elif stripped.startswith("Powered:"):
                info["powered"] = stripped.split(":", 1)[1].strip()
            elif stripped.startswith("Discoverable:"):
                info["discoverable"] = stripped.split(":", 1)[1].strip()
            elif stripped.startswith("Pairable:"):
                info["pairable"] = stripped.split(":", 1)[1].strip()
        service_state = self._read_bluetooth_service_state()
        if service_state:
            info["service"] = service_state
        rfkill_state = self._read_bluetooth_rfkill_state()
        if rfkill_state:
            info["rfkill"] = rfkill_state

        devices: list[dict[str, str]] = []
        for line in self._run_bluetoothctl(["devices"], 8).splitlines():
            match = re.match(r"Device\s+([0-9A-Fa-f:]{17})\s+(.+)", line.strip())
            if not match:
                continue
            mac, name = match.groups()
            detail = self._read_bluetooth_device_detail(mac)
            detail.setdefault("mac", mac)
            detail.setdefault("name", name.strip())
            devices.append(detail)
        info["devices"] = devices
        return info

    def _read_bluetooth_service_state(self) -> str:
        if shutil.which("systemctl") is None:
            return ""
        return self._run_command(["systemctl", "is-active", "bluetooth"], timeout=5).strip()

    def _read_bluetooth_rfkill_state(self) -> str:
        if shutil.which("rfkill") is None:
            return ""
        output = self._run_command(["rfkill", "list", "bluetooth"], timeout=5)
        if not output:
            return ""
        states = []
        for line in output.splitlines():
            stripped = line.strip()
            if stripped.startswith("Soft blocked:") or stripped.startswith("Hard blocked:"):
                states.append(stripped)
        return ", ".join(states)

    def _read_bluetooth_device_detail(self, mac: str) -> dict[str, str]:
        detail: dict[str, str] = {}
        for line in self._run_bluetoothctl(["info", mac], 5).splitlines():
            stripped = line.strip()
            if stripped.startswith("Name:"):
                detail["name"] = stripped.split(":", 1)[1].strip()
            elif stripped.startswith("Alias:"):
                detail["alias"] = stripped.split(":", 1)[1].strip()
            elif stripped.startswith("Paired:"):
                detail["paired"] = stripped.split(":", 1)[1].strip()
            elif stripped.startswith("Trusted:"):
                detail["trusted"] = stripped.split(":", 1)[1].strip()
            elif stripped.startswith("Connected:"):
                detail["connected"] = stripped.split(":", 1)[1].strip()
            elif stripped.startswith("Icon:"):
                detail["icon"] = stripped.split(":", 1)[1].strip()
            elif stripped.startswith("Class:"):
                detail["device_class"] = stripped.split(":", 1)[1].strip()
            elif stripped.startswith("Modalias:"):
                detail["modalias"] = stripped.split(":", 1)[1].strip()
            elif stripped.startswith("UUID:"):
                uuids = detail.setdefault("uuids", "")
                uuid_value = stripped.split(":", 1)[1].strip()
                detail["uuids"] = f"{uuids}\n{uuid_value}".strip()
        return detail

    def _run_bluetoothctl(self, args: list[str], timeout: int = 10) -> str:
        return self._run_command(["bluetoothctl", *args], timeout=timeout)

    def _apply_bluetooth_info(self, info: dict[str, object] | None) -> None:
        powered = bool(info and info.get("powered") == "yes")
        if self._bluetooth_toggle:
            self._bluetooth_toggle.blockSignals(True)
            self._bluetooth_toggle.setChecked(powered)
            self._bluetooth_toggle.setText(
                t("settings_bluetooth_toggle_on") if powered else t("settings_bluetooth_toggle_off")
            )
            self._bluetooth_toggle.setStyleSheet(self._action_button_style("primary" if powered else "secondary"))
            self._bluetooth_toggle.blockSignals(False)
        if self._bluetooth_content:
            self._bluetooth_content.setVisible(powered)
        if not powered:
            if self._bluetooth_status:
                self._bluetooth_status.setText("")
            if self._bluetooth_connected_list:
                self._bluetooth_connected_list.clear()
            if self._bluetooth_scan_list:
                self._bluetooth_scan_list.clear()
            return

        if self._bluetooth_status:
            self._bluetooth_status.setText(self._format_bluetooth_status(info))
        if self._bluetooth_connected_list:
            self._bluetooth_connected_list.clear()
        if self._bluetooth_scan_list:
            self._bluetooth_scan_list.clear()
        for device in (info or {}).get("devices", []):
            if not isinstance(device, dict):
                continue
            mac = str(device.get("mac", ""))
            name = self._bluetooth_display_name(device)
            subtitle = self._bluetooth_display_subtitle(device)
            flags = []
            if device.get("connected") == "yes":
                flags.append(t("settings_bluetooth_connected"))
            if device.get("paired") == "yes":
                flags.append(t("settings_bluetooth_paired"))
            suffix = f" ({', '.join(flags)})" if flags else ""
            item = QListWidgetItem(f"{name}{suffix}\n{subtitle}")
            item.setData(Qt.UserRole, mac)
            if device.get("connected") == "yes" or device.get("paired") == "yes":
                if self._bluetooth_connected_list:
                    self._bluetooth_connected_list.addItem(item)
            elif self._bluetooth_scan_list:
                self._bluetooth_scan_list.addItem(item)
        if self._bluetooth_connected_list and self._bluetooth_connected_list.count() == 0:
            self._bluetooth_connected_list.addItem(t("settings_bluetooth_no_connected_devices"))
        if self._bluetooth_scan_list and self._bluetooth_scan_list.count() == 0:
            self._bluetooth_scan_list.addItem(t("settings_bluetooth_no_scan_results"))

    def _bluetooth_display_name(self, device: dict[str, str]) -> str:
        for key in ("alias", "name"):
            value = str(device.get(key, "")).strip()
            if value and not self._looks_like_bluetooth_identifier(value):
                return value
        kind = self._bluetooth_device_kind(device)
        return t("settings_bluetooth_unknown_device", kind=kind)

    def _bluetooth_display_subtitle(self, device: dict[str, str]) -> str:
        mac = str(device.get("mac", "")).strip()
        raw_name = str(device.get("alias") or device.get("name") or "").strip()
        kind = self._bluetooth_device_kind(device)
        parts = [kind]
        if raw_name and raw_name != mac and self._looks_like_bluetooth_identifier(raw_name):
            parts.append(raw_name)
        if mac:
            parts.append(mac)
        return " · ".join(parts)

    def _bluetooth_device_kind(self, device: dict[str, str]) -> str:
        haystack = "\n".join(
            str(device.get(key, ""))
            for key in ("icon", "device_class", "modalias", "uuids", "alias", "name")
        ).lower()
        if "keyboard" in haystack:
            return t("settings_bluetooth_kind_keyboard")
        if "mouse" in haystack:
            return t("settings_bluetooth_kind_mouse")
        if "audio" in haystack or "headset" in haystack or "headphone" in haystack or "speaker" in haystack:
            return t("settings_bluetooth_kind_audio")
        if "phone" in haystack:
            return t("settings_bluetooth_kind_phone")
        if "computer" in haystack or "laptop" in haystack:
            return t("settings_bluetooth_kind_computer")
        if "input" in haystack or "hid" in haystack:
            return t("settings_bluetooth_kind_input")
        return t("settings_bluetooth_kind_device")

    @staticmethod
    def _looks_like_bluetooth_identifier(value: str) -> bool:
        stripped = value.strip()
        if re.fullmatch(r"(?:[0-9A-Fa-f]{2}:){2,5}[0-9A-Fa-f]{2}", stripped):
            return True
        if re.fullmatch(r"[0-9A-Fa-f]{4,}(?:::[0-9A-Fa-f]{4,})?", stripped):
            return True
        if re.fullmatch(r"[0-9A-Fa-f:_-]{8,}", stripped):
            return True
        return False

    def _format_bluetooth_status(self, info: dict[str, object] | None) -> str:
        if not info:
            return t("settings_bluetooth_info_unavailable")
        user_note = str(info.get("user_note", "")).strip()
        return user_note or t("settings_bluetooth_ready")

    @staticmethod
    def _bluetooth_log_path() -> Path:
        return Path(__file__).resolve().parents[3] / "bluetooth.log"

    def _log_bluetooth_error(self, action: str, output: str) -> None:
        if not output.strip():
            return
        try:
            timestamp = datetime.now(timezone.utc).isoformat()
            with self._bluetooth_log_path().open("a", encoding="utf-8") as handle:
                handle.write(f"[{timestamp}] {action}\n{output.strip()}\n\n")
        except Exception:
            pass

    @staticmethod
    def _is_bluetooth_error(output: str) -> bool:
        lowered = output.lower()
        return any(
            marker in lowered
            for marker in (
                "failed",
                "error",
                "not available",
                "not permitted",
                "permission denied",
                "blocked",
                "no default controller",
            )
        )

    def _refresh_wifi_status(self) -> None:
        if self._wifi_status:
            self._wifi_status.setText(t("settings_wifi_status_loading"))
        self._schedule_task(self._refresh_wifi_status_async())

    async def _refresh_wifi_status_async(self) -> None:
        info = await asyncio.to_thread(self._read_wifi_info)
        self._wifi_last_info = info
        if self._wifi_status:
            self._wifi_status.setText(self._format_wifi_status(info))

    @staticmethod
    def _run_command(command: list[str], timeout: int = 5) -> str:
        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            stdout = (exc.stdout or "").strip()
            stderr = (exc.stderr or "").strip()
            return stdout or stderr
        stdout = (completed.stdout or "").strip()
        stderr = (completed.stderr or "").strip()
        return stdout or stderr

    def _read_wifi_info(self) -> dict[str, str]:
        system = platform.system()
        info = {"platform": system}
        try:
            if system == "Linux":
                info.update(self._read_wifi_info_linux())
            elif system == "Darwin":
                info.update(self._read_wifi_info_macos())
            elif system == "Windows":
                info.update(self._read_wifi_info_windows())
            else:
                info["note"] = t("settings_wifi_info_unavailable")
        except Exception as exc:
            info["note"] = str(exc)
        if not info.get("ssid") and not info.get("state"):
            info.setdefault("state", t("settings_wifi_not_connected"))
        return info

    def _read_wifi_info_linux(self) -> dict[str, str]:
        info: dict[str, str] = {}
        if shutil.which("nmcli"):
            wifi_lines = self._run_command(["nmcli", "-t", "-f", "ACTIVE,SSID,DEVICE,SIGNAL,SECURITY", "dev", "wifi"]).splitlines()
            for line in wifi_lines:
                parts = line.split(":")
                if parts and parts[0] == "yes":
                    info["ssid"] = parts[1] if len(parts) > 1 else ""
                    info["interface"] = parts[2] if len(parts) > 2 else ""
                    info["signal"] = (parts[3] + "%") if len(parts) > 3 and parts[3] else ""
                    info["security"] = parts[4] if len(parts) > 4 else ""
                    info["state"] = t("settings_wifi_connected")
                    break
            device = info.get("interface")
            if device:
                detail_lines = self._run_command(["nmcli", "-t", "-f", "IP4.ADDRESS,IP4.GATEWAY,GENERAL.HWADDR", "device", "show", device]).splitlines()
                for line in detail_lines:
                    if line.startswith("IP4.ADDRESS"):
                        info["ipv4"] = line.split(":", 1)[1].split("/", 1)[0].strip()
                    elif line.startswith("IP4.GATEWAY"):
                        info["gateway"] = line.split(":", 1)[1].strip()
                    elif line.startswith("GENERAL.HWADDR"):
                        info["mac"] = line.split(":", 1)[1].strip()
        elif shutil.which("iwgetid"):
            ssid = self._run_command(["iwgetid", "-r"]).strip()
            if ssid:
                info["ssid"] = ssid
                info["state"] = t("settings_wifi_connected")
        return info

    def _read_wifi_info_macos(self) -> dict[str, str]:
        info: dict[str, str] = {}
        airport = "/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport"
        if Path(airport).exists():
            airport_data = self._run_command([airport, "-I"])
            for line in airport_data.splitlines():
                stripped = line.strip()
                if stripped.startswith("SSID:"):
                    info["ssid"] = stripped.split(":", 1)[1].strip()
                elif stripped.startswith("BSSID:"):
                    info["bssid"] = stripped.split(":", 1)[1].strip()
                elif stripped.startswith("agrCtlRSSI:"):
                    info["signal"] = stripped.split(":", 1)[1].strip() + " dBm"
                elif stripped.startswith("link auth:"):
                    info["security"] = stripped.split(":", 1)[1].strip()
                elif stripped.startswith("channel:"):
                    info["channel"] = stripped.split(":", 1)[1].strip()
                elif stripped.startswith("state:"):
                    state = stripped.split(":", 1)[1].strip()
                    info["state"] = t("settings_wifi_connected") if state == "running" else state
        for candidate in ("en0", "en1"):
            ifconfig = self._run_command(["ifconfig", candidate])
            active = False
            for line in ifconfig.splitlines():
                stripped = line.strip()
                if stripped.startswith("status:"):
                    active = stripped.split(":", 1)[1].strip().lower() == "active"
                elif stripped.startswith("inet "):
                    info.setdefault("interface", candidate)
                    info["ipv4"] = stripped.split()[1].strip()
                elif stripped.startswith("inet6 ") and "prefixlen" in stripped and "scopeid" in stripped:
                    info.setdefault("ipv6", stripped.split()[1].strip())
                elif stripped.startswith("ether "):
                    info["mac"] = stripped.split()[1].strip()
            if active or info.get("ipv4"):
                info.setdefault("interface", candidate)
                info["state"] = t("settings_wifi_connected")
                break
        if info.get("interface"):
            route = self._run_command(["route", "-n", "get", "default"])
            for line in route.splitlines():
                stripped = line.strip()
                if stripped.startswith("gateway:"):
                    info["gateway"] = stripped.split(":", 1)[1].strip()
                    break
        return info

    def _read_wifi_info_windows(self) -> dict[str, str]:
        info: dict[str, str] = {}
        output = self._run_command(["netsh", "wlan", "show", "interfaces"])
        for line in output.splitlines():
            stripped = line.strip()
            if ":" not in stripped:
                continue
            key, value = [item.strip() for item in stripped.split(":", 1)]
            if key == "SSID" and value and value != "N/A":
                info["ssid"] = value
            elif key == "Description":
                info["interface"] = value
            elif key == "Signal":
                info["signal"] = value
            elif key == "Authentication":
                info["security"] = value
            elif key == "State":
                info["state"] = value
            elif key == "BSSID":
                info["bssid"] = value
        return info

    def _format_wifi_status(self, info: dict[str, str] | None) -> str:
        if not info:
            return t("settings_wifi_info_unavailable")
        lines = [f"{t('settings_wifi_platform')}: {info.get('platform', platform.system())}"]
        fields = [
            ("ssid", "settings_wifi_ssid"),
            ("state", "settings_wifi_state"),
            ("interface", "settings_wifi_interface"),
            ("signal", "settings_wifi_signal"),
            ("security", "settings_wifi_security"),
            ("channel", "settings_wifi_channel"),
            ("ipv4", "settings_wifi_ipv4"),
            ("ipv6", "settings_wifi_ipv6"),
            ("gateway", "settings_wifi_gateway"),
            ("mac", "settings_wifi_mac"),
            ("bssid", "settings_wifi_bssid"),
        ]
        for key, label_key in fields:
            value = info.get(key, "").strip()
            if value:
                lines.append(f"{t(label_key)}: {value}")
        note = info.get("note", "").strip()
        if note:
            lines.append(f"{t('settings_wifi_note')}: {note}")
        if len(lines) == 1:
            lines.append(f"{t('settings_wifi_state')}: {t('settings_wifi_not_connected')}")
        return "\n".join(lines)

    def open_tab(self, key: str) -> None:
        tab_map = {
            "system": 0,
            "advanced": 1,
            "support": 2,
            "ssh": 2,
            "wifi": 3,
            "bluetooth": 4,
        }
        index = tab_map.get(key)
        if index is not None and hasattr(self, "_tabs"):
            self._tabs.setCurrentIndex(index)

    @staticmethod
    def _settings_card(title: str | None = None) -> QFrame:
        card = QFrame()
        card.setObjectName("Card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 16, 16, 16)
        if title:
            label = QLabel(title)
            label.setStyleSheet("font-weight:700; letter-spacing:0.02em;")
            layout.addWidget(label)
        return card

    @staticmethod
    def _preference_field(label: QLabel, field: QWidget) -> QWidget:
        card = QFrame()
        card.setStyleSheet(
            "QFrame {"
            "  background:#fffdf8;"
            "  border:1px solid #efe6d8;"
            "  border-radius:18px;"
            "}"
        )
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(14, 12, 14, 14)
        card_layout.setSpacing(8)
        label.setStyleSheet(
            "color:#3f3a33; background:transparent; border:none; font-size:12px; font-weight:700; letter-spacing:0.04em;"
        )
        card_layout.addWidget(label)
        card_layout.addWidget(field)
        return card

    @staticmethod
    def _system_info_pill(title: str, value: str) -> tuple[QLabel, QFrame]:
        card = QFrame()
        card.setStyleSheet(
            "QFrame {"
            "  background:#fffdf8;"
            "  border:1px solid #ede4d5;"
            "  border-radius:18px;"
            "}"
        )
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(6)

        label = QLabel(title)
        label.setStyleSheet(
            "color:#7a6d58; background:transparent; border:none; font-size:11px; font-weight:700; letter-spacing:0.06em;"
        )
        layout.addWidget(label)

        content = QLabel(value)
        content.setWordWrap(True)
        content.setStyleSheet("color:#171717; background:transparent; border:none; font-size:14px; font-weight:600;")
        layout.addWidget(content)
        layout.addStretch(1)
        return label, card

    def _available_timezones(self) -> list[str]:
        try:
            zones = sorted(available_timezones())
        except Exception:
            zones = ["UTC"]
        if "UTC" in zones:
            zones.remove("UTC")
            zones.insert(0, "UTC")
        return zones

    @staticmethod
    def _language_options() -> list[tuple[str, str]]:
        return [
            ("Nederlands", "nl-NL"),
            ("English", "en-US"),
        ]

    def _current_timezone(self) -> str | None:
        env_value = os.environ.get("TIMEZONE")
        if env_value:
            return env_value.strip()
        value = self._read_env_value("TIMEZONE")
        if value:
            return value
        return None

    def _current_language(self) -> str | None:
        env_value = os.environ.get("LANGUAGE")
        if env_value:
            return env_value.strip()
        value = self._read_env_value("LANGUAGE")
        if value:
            return value
        return None

    def _current_focus_mode(self) -> str | None:
        env_value = os.environ.get("AITJE_DEFAULT_PROMPT_MODE")
        if env_value:
            return env_value.strip()
        value = self._read_env_value("AITJE_DEFAULT_PROMPT_MODE")
        if value:
            return value
        return None

    def _configured_today(self) -> str | None:
        env_value = os.environ.get("AITJE_TODAY_DATE")
        if env_value:
            return env_value.strip()
        value = self._read_env_value("AITJE_TODAY_DATE")
        if value:
            return value
        return None

    def _today_date(self) -> datetime:
        timezone_name = self._current_timezone() or "UTC"
        try:
            tzinfo = ZoneInfo(timezone_name)
        except Exception:
            tzinfo = timezone.utc
        configured = self._configured_today()
        if configured:
            try:
                return datetime.fromisoformat(configured).replace(tzinfo=tzinfo)
            except ValueError:
                pass
        return datetime.now(tzinfo)

    def _current_qdate(self) -> QDate:
        dt = self._today_date()
        return QDate(dt.year, dt.month, dt.day)

    def _env_display_value(self, key: str, default: str | None = None) -> str:
        value = self._read_env_value(key)
        if value is None:
            value = os.environ.get(key, "")
        value = (value or "").strip()
        return value or (default or t("settings_not_set"))

    def _effective_backend_url(self) -> str:
        configured = self._read_env_value("BACKEND_HTTP")
        if configured and configured.strip():
            return configured.strip()
        return BACKEND_HTTP

    @staticmethod
    def _mode_filename(mode: str) -> str:
        slug = "".join(ch.lower() if ch.isalnum() else "_" for ch in mode.strip()).strip("_")
        return f"{slug}.txt" if slug else ""

    @staticmethod
    def _env_file_path() -> Path:
        return Path(__file__).resolve().parents[3] / ".env"

    @staticmethod
    def _action_button_style(variant: str = "primary") -> str:
        if variant == "secondary":
            return (
                "QPushButton {"
                "  min-height: 42px;"
                "  padding: 0 18px;"
                "  border: 1px solid #e5dccd;"
                "  border-radius: 16px;"
                "  background: #fffaf0;"
                "  color: #473f34;"
                "  font-weight: 700;"
                "  text-align: center;"
                "}"
                "QPushButton:hover { background: #fff4cf; border-color: #f0c94c; }"
                "QPushButton:disabled { color:#b8b0a4; background:#f8f4ec; border-color:#eee7dc; }"
            )
        return (
            "QPushButton {"
            "  min-height: 42px;"
            "  padding: 0 18px;"
            "  border: 1px solid #facc15;"
            "  border-radius: 16px;"
            "  background: #facc15;"
            "  color: #151515;"
            "  font-weight: 800;"
            "  text-align: center;"
            "}"
            "QPushButton:hover { background: #111111; color:#facc15; border-color:#111111; }"
            "QPushButton:disabled { color:#9c8b4a; background:#f6e7a5; border-color:#f6e7a5; }"
        )

    @staticmethod
    def _compact_action_button_style(variant: str = "primary") -> str:
        base = SettingsPage._action_button_style(variant)
        return base.replace("min-height: 42px;", "min-height: 34px;").replace("border-radius: 16px;", "border-radius: 14px;")

    def _style_combo_box(self, combo: QComboBox) -> None:
        combo.setStyleSheet(self.FIELD_STYLE)
        popup = QListView(combo)
        popup.setStyleSheet(self.COMBO_POPUP_STYLE)
        combo.setView(popup)

    def _read_env_value(self, key: str) -> str | None:
        path = self._env_file_path()
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except FileNotFoundError:
            return None
        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in line:
                continue
            name, value = line.split("=", 1)
            if name.strip() != key:
                continue
            value = value.strip()
            if (value.startswith('"') and value.endswith('"')) or (
                value.startswith("'") and value.endswith("'")
            ):
                value = value[1:-1]
            return value.strip()
        return None

    @staticmethod
    def _format_env_value(value: str) -> str:
        if re.fullmatch(r"[A-Za-z0-9_./,:-]*", value):
            return value
        escaped = (
            value.replace("\\", "\\\\")
            .replace('"', '\\"')
            .replace("$", "\\$")
            .replace("`", "\\`")
        )
        return f'"{escaped}"'

    def _set_env_value(self, key: str, value: str) -> None:
        path = self._env_file_path()
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except FileNotFoundError:
            lines = []
        formatted_value = self._format_env_value(value)
        updated = False
        new_lines: list[str] = []
        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in line:
                new_lines.append(line)
                continue
            name, _ = line.split("=", 1)
            if name.strip() == key:
                new_lines.append(f"{key}={formatted_value}")
                updated = True
            else:
                new_lines.append(line)
        if not updated:
            if new_lines and new_lines[-1].strip():
                new_lines.append("")
            new_lines.append(f"{key}={formatted_value}")
        path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")

    def _on_system_preference_changed(self, *_args) -> None:
        if self._system_loading or self._timezone_loading or self._date_loading:
            return
        self._update_system_action_buttons()

    def _capture_saved_system_preferences(self) -> None:
        self._saved_timezone = self._current_timezone() or ""
        self._saved_language = self._current_language() or "nl-NL"
        self._saved_today = self._configured_today() or self._current_qdate().toString("yyyy-MM-dd")

    def _save_system_preferences(self) -> None:
        timezone_value = (self._timezone_combo.currentText().strip() if self._timezone_combo else "")
        language_value = str(self._language_combo.currentData() or "").strip() if self._language_combo else ""
        today_value = self._date_edit.date().toString("yyyy-MM-dd") if self._date_edit else ""
        if not timezone_value or not language_value or not today_value:
            return
        try:
            self._set_env_value("TIMEZONE", timezone_value)
            os.environ["TIMEZONE"] = timezone_value
            self._set_env_value("LANGUAGE", language_value)
            os.environ["LANGUAGE"] = language_value
            self._set_env_value("AITJE_RESPONSE_LANGUAGE", language_value)
            os.environ["AITJE_RESPONSE_LANGUAGE"] = language_value
            self._set_env_value("AITJE_TODAY_DATE", today_value)
            os.environ["AITJE_TODAY_DATE"] = today_value
            set_language(language_value)
            self._capture_saved_system_preferences()
            self._update_system_action_buttons()
        except Exception as exc:
            show_error_dialog(self, t("error"), f"{t('settings_could_not_save_system_preferences')} {exc}")

    def _reset_system_preferences(self) -> None:
        self._system_loading = True
        if self._timezone_combo:
            self._timezone_combo.setCurrentText(self._saved_timezone or "Europe/Amsterdam")
        if self._language_combo:
            for index in range(self._language_combo.count()):
                if self._language_combo.itemData(index) == self._saved_language:
                    self._language_combo.setCurrentIndex(index)
                    break
        if self._date_edit:
            self._date_loading = True
            parsed = QDate.fromString(self._saved_today, "yyyy-MM-dd")
            if parsed.isValid():
                self._date_edit.setDate(parsed)
            self._date_loading = False
        self._system_loading = False
        self._update_system_action_buttons()

    def _update_system_action_buttons(self) -> None:
        if not self._system_save_button or not self._system_reset_button:
            return
        dirty = self._system_preferences_dirty()
        self._system_save_button.setEnabled(dirty)
        self._system_reset_button.setEnabled(dirty)

    def _system_preferences_dirty(self) -> bool:
        timezone_value = (self._timezone_combo.currentText().strip() if self._timezone_combo else "")
        language_value = str(self._language_combo.currentData() or "").strip() if self._language_combo else ""
        today_value = self._date_edit.date().toString("yyyy-MM-dd") if self._date_edit else ""
        return (
            timezone_value != self._saved_timezone
            or language_value != self._saved_language
            or today_value != self._saved_today
        )

    def _populate_focus_mode_options(self) -> None:
        if not self._focus_mode_tabs_layout:
            return
        current_value = self._current_focus_mode()
        modes = self._configured_prompt_modes()
        while self._focus_mode_tabs_layout.count():
            item = self._focus_mode_tabs_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self._focus_mode_buttons = {}

        all_modes = [("", t("chat_mode_default"))] + [(mode, mode) for mode in modes]
        for value, label in all_modes:
            button = QPushButton(label)
            button.setCursor(Qt.PointingHandCursor)
            button.setCheckable(True)
            button.setMinimumHeight(40)
            button.setStyleSheet(self._focus_mode_tab_style(False))
            button.clicked.connect(lambda _checked=False, mode=value: self._on_focus_mode_changed(mode))
            self._focus_mode_tabs_layout.addWidget(button)
            self._focus_mode_buttons[value] = button
        self._focus_mode_tabs_layout.addStretch(1)
        self._focus_mode_selected = current_value or ""
        self._sync_focus_mode_tabs()
        self._update_focus_mode_info()

    def _sync_focus_mode_tabs(self) -> None:
        for value, button in self._focus_mode_buttons.items():
            active = value == self._focus_mode_selected
            button.setChecked(active)
            button.setStyleSheet(self._focus_mode_tab_style(active))

    @staticmethod
    def _focus_mode_tab_style(active: bool) -> str:
        if active:
            return (
                "QPushButton {"
                "  background:#facc15;"
                "  color:#171717;"
                "  border:1px solid #facc15;"
                "  border-radius:18px;"
                "  padding:0 18px;"
                "  font-weight:800;"
                "}"
            )
        return (
            "QPushButton {"
            "  background:#fffdf8;"
            "  color:#6a5c46;"
            "  border:1px solid #facc15;"
            "  border-radius:18px;"
            "  padding:0 18px;"
            "  font-weight:700;"
            "}"
            "QPushButton:hover { background:#fff7db; color:#171717; }"
        )

    def _on_focus_mode_changed(self, value: str) -> None:
        value = (value or "").strip()
        try:
            self._set_env_value("AITJE_DEFAULT_PROMPT_MODE", value)
            if value:
                os.environ["AITJE_DEFAULT_PROMPT_MODE"] = value
            else:
                os.environ.pop("AITJE_DEFAULT_PROMPT_MODE", None)
        except Exception as exc:
            show_error_dialog(self, t("error"), f"{t('settings_could_not_save_focus_mode')} {exc}")
            return
        self._focus_mode_selected = value
        self._sync_focus_mode_tabs()
        self._update_focus_mode_info()

    def _configured_prompt_modes(self) -> list[str]:
        seen: set[str] = set()
        modes: list[str] = []
        env_modes = self._read_env_value("PROMPT_MODES")
        raw_modes = [item.strip() for item in (env_modes or "").split(",") if item.strip()]
        source_modes = raw_modes or list(PROMPT_MODES) or ["Developer", "Finance", "Law", "Child"]
        for mode in source_modes:
            if mode not in seen:
                modes.append(mode)
                seen.add(mode)
        return modes

    def _prompt_template_path(self, mode: str) -> Path:
        filename = self._mode_filename(mode)
        return Path(__file__).resolve().parents[2] / "backend" / "prompt_templates" / filename

    def _default_prompt_template_path(self) -> Path:
        return Path(__file__).resolve().parents[2] / "backend" / "prompt.txt"

    def _read_prompt_template(self, mode: str) -> str:
        path = self._prompt_template_path(mode)
        try:
            return path.read_text(encoding="utf-8").strip()
        except FileNotFoundError:
            return ""

    def _read_default_prompt_template(self) -> str:
        try:
            return self._default_prompt_template_path().read_text(encoding="utf-8").strip()
        except FileNotFoundError:
            return t("settings_focus_mode_default_prompt_preview")

    def _describe_model(self, model: str) -> str:
        normalized = (model or "").strip().lower()
        if not normalized:
            return t("settings_model_description_empty")

        size_match = re.search(r"(\d+(?:\.\d+)?)b", normalized)
        size_value = float(size_match.group(1)) if size_match else None
        if size_value is None:
            size_text_nl = "onbekende grootte"
            size_text_en = "unknown size"
        elif size_value < 1.5:
            size_text_nl = "een zeer klein model"
            size_text_en = "a very small model"
        elif size_value < 3.5:
            size_text_nl = "een compact model"
            size_text_en = "a compact model"
        elif size_value < 8:
            size_text_nl = "een middelgroot model"
            size_text_en = "a mid-sized model"
        else:
            size_text_nl = "een groter model"
            size_text_en = "a larger model"

        reasons = []
        if "qwen3" in normalized or "qwen 3" in normalized or "deepseek-r1" in normalized or "gpt-oss" in normalized:
            reasons.append(("heeft ingebouwde redeneersterkte", "has strong reasoning behavior"))
        if "gemma" in normalized:
            reasons.append(("is vaak sterk in snelle algemene antwoorden", "is often strong at fast general responses"))
        if "llama" in normalized:
            reasons.append(("is meestal een brede allrounder", "is usually a broad all-rounder"))
        if "coder" in normalized or "code" in normalized:
            reasons.append(("is meer gericht op code en technische taken", "is more focused on code and technical tasks"))

        lang = get_current_language()
        family = model.split(":")[0]
        if lang == "en":
            parts = [f"`{family}` is {size_text_en}."]
            if reasons:
                parts.append("It " + ", and ".join(item[1] for item in reasons) + ".")
            if size_value is not None:
                parts.append(
                    "Smaller models are usually faster and lighter; larger models are often stronger but heavier."
                )
            return " ".join(parts)

        parts = [f"`{family}` is {size_text_nl}."]
        if reasons:
            parts.append("Het " + ", en ".join(item[0] for item in reasons) + ".")
        if size_value is not None:
            parts.append(
                "Kleinere modellen zijn meestal sneller en lichter; grotere modellen zijn vaak sterker maar zwaarder."
            )
        return " ".join(parts)

    def _write_prompt_modes(self, modes: list[str]) -> None:
        cleaned = [mode.strip() for mode in modes if mode.strip()]
        self._set_env_value("PROMPT_MODES", ",".join(cleaned))
        PROMPT_MODES[:] = cleaned

    def _is_builtin_mode(self, mode: str) -> bool:
        return mode in self._builtin_modes

    def _selected_focus_mode(self) -> str:
        return self._focus_mode_selected.strip()

    def _focus_mode_summary(self, mode: str) -> str:
        if not mode:
            return t("settings_focus_mode_default_info")
        builtin_info = {
            "Developer": t("settings_focus_mode_developer_info"),
            "Finance": t("settings_focus_mode_finance_info"),
            "Law": t("settings_focus_mode_law_info"),
            "Child": t("settings_focus_mode_child_info"),
        }
        if mode in builtin_info:
            return builtin_info[mode]
        preview = self._read_prompt_template(mode)
        if not preview:
            return t("settings_focus_mode_custom_info_empty")
        return t("settings_focus_mode_custom_info", prompt=preview[:220].replace("\n", " "))

    def _update_focus_mode_info(self) -> None:
        mode = self._selected_focus_mode()
        if self._focus_mode_info:
            locked = (
                t("settings_focus_mode_builtin_locked")
                if mode and self._is_builtin_mode(mode)
                else t("settings_focus_mode_custom_editable")
                if mode
                else t("settings_focus_mode_default_locked")
            )
            self._focus_mode_info.setText(f"{self._focus_mode_summary(mode)}\n{locked}")
        if self._focus_mode_manage:
            self._focus_mode_manage.setEnabled(True)
            self._focus_mode_manage.setText(
                t("settings_view_focus_mode") if not mode or self._is_builtin_mode(mode) else t("settings_edit_focus_mode")
            )

    def _create_focus_mode(self) -> None:
        dialog = PromptTemplateDialog(self)
        if dialog.exec() != QDialog.Accepted:
            return
        name, prompt = dialog.values()
        self._save_custom_focus_mode(name, prompt, previous_name=None)

    def _manage_focus_mode(self) -> None:
        mode = self._selected_focus_mode()
        dialog = PromptTemplateDialog(
            self,
            mode_name=mode or t("chat_mode_default"),
            prompt_text=self._read_default_prompt_template() if not mode else self._read_prompt_template(mode),
            builtin=not mode or self._is_builtin_mode(mode),
        )
        result = dialog.exec()
        if result != QDialog.Accepted or dialog.action != "save":
            if result == QDialog.Accepted and dialog.action == "delete":
                self._delete_custom_focus_mode(mode)
            return
        name, prompt = dialog.values()
        if self._is_builtin_mode(mode):
            return
        self._save_custom_focus_mode(name, prompt, previous_name=mode)

    def _save_custom_focus_mode(self, name: str, prompt: str, previous_name: str | None) -> None:
        cleaned_name = name.strip()
        if not cleaned_name or not prompt.strip():
            show_error_dialog(self, t("error"), t("settings_focus_mode_validation_error"))
            return
        if self._is_builtin_mode(cleaned_name) and cleaned_name != (previous_name or ""):
            show_error_dialog(self, t("error"), t("settings_focus_mode_builtin_name_error"))
            return
        target_path = self._prompt_template_path(cleaned_name)
        try:
            if previous_name and previous_name != cleaned_name:
                old_path = self._prompt_template_path(previous_name)
                if old_path.exists():
                    old_path.unlink()
            target_path.write_text(prompt.strip() + "\n", encoding="utf-8")
            modes = [mode for mode in self._configured_prompt_modes() if mode != (previous_name or "")]
            if cleaned_name not in modes:
                modes.append(cleaned_name)
            self._write_prompt_modes(modes)
            self._set_env_value("AITJE_DEFAULT_PROMPT_MODE", cleaned_name)
            os.environ["AITJE_DEFAULT_PROMPT_MODE"] = cleaned_name
            self._populate_focus_mode_options()
        except OSError as exc:
            show_error_dialog(self, t("error"), f"{t('settings_could_not_save_focus_mode')} {exc}")

    def _delete_custom_focus_mode(self, mode: str) -> None:
        if self._is_builtin_mode(mode):
            return
        if not ask_yes_no_dialog(self, t("settings_delete_focus_mode"), t("settings_delete_focus_mode_confirm", mode=mode)):
            return
        try:
            path = self._prompt_template_path(mode)
            if path.exists():
                path.unlink()
            modes = [item for item in self._configured_prompt_modes() if item != mode]
            self._write_prompt_modes(modes)
            current_default = self._current_focus_mode()
            if current_default == mode:
                self._set_env_value("AITJE_DEFAULT_PROMPT_MODE", "")
                os.environ.pop("AITJE_DEFAULT_PROMPT_MODE", None)
            self._populate_focus_mode_options()
        except OSError as exc:
            show_error_dialog(self, t("error"), f"{t('settings_delete_focus_mode')} {exc}")


    def _auth_headers(self) -> dict:
        if BACKEND_BEARER_TOKEN:
            return {"Authorization": f"Bearer {BACKEND_BEARER_TOKEN}"}
        return {}

    def _load_models(self) -> None:
        if not self._ollama_combo or not self._ollama_status:
            return
        self._schedule_task(self._load_models_async())

    async def _load_models_async(self) -> None:
        try:
            response = await asyncio.to_thread(
                requests.get,
                f"{BACKEND_HTTP}/api/v1/ollama/models",
                timeout=10,
                headers=self._auth_headers(),
            )
            response.raise_for_status()
            payload = response.json()
        except Exception as exc:
            fallback = OLLAMA_MODELS
            if fallback:
                self._current_model = fallback[0]
                self._saved_model = fallback[0]
                self._ollama_combo.clear()
                self._ollama_combo.addItems(fallback)
                self._ollama_combo.setEnabled(True)
                self._ollama_status.setText(t("settings_backend_not_reachable"))
                self._update_model_ui_state()
                return
            self._ollama_status.setText(f"{t('settings_could_not_fetch_models')} {exc}")
            return

        available = payload.get("available", [])
        current = payload.get("current")
        self._current_model = current
        self._saved_model = current or ""
        self._ollama_combo.clear()
        self._ollama_combo.addItems(available)
        if current in available:
            self._ollama_combo.setCurrentText(current)
        self._ollama_combo.setEnabled(bool(available))
        if current:
            self._ollama_status.setText(f"{t('settings_current_model')} {current}")
        else:
            self._ollama_status.setText(t("settings_no_active_model"))
        self._update_model_ui_state()

    def _on_model_selection_changed(self, _value: str) -> None:
        self._update_model_ui_state()

    def _update_model_ui_state(self) -> None:
        if self._ollama_apply:
            dirty = bool(self._ollama_combo and self._ollama_combo.currentText().strip() and self._ollama_combo.currentText().strip() != self._saved_model)
            self._ollama_apply.setEnabled(dirty)
        if self._ollama_reset:
            dirty = bool(self._ollama_combo and self._ollama_combo.currentText().strip() != self._saved_model)
            self._ollama_reset.setEnabled(dirty)
        if self._ollama_description and self._ollama_combo:
            self._ollama_description.setText(self._describe_model(self._ollama_combo.currentText().strip()))

    def _reset_model_selection(self) -> None:
        if not self._ollama_combo:
            return
        if self._saved_model:
            self._ollama_combo.setCurrentText(self._saved_model)
        self._update_model_ui_state()

    def _on_apply_model(self) -> None:
        if not self._ollama_combo or not self._ollama_status:
            return
        model = self._ollama_combo.currentText().strip()
        if not model:
            return
        if model == self._current_model:
            self._ollama_status.setText(t("settings_model_already_active", model=model))
            return

        self._show_busy(t("settings_ollama_fetching", model=model))
        asyncio.create_task(self._apply_model_async(model))

    async def _apply_model_async(self, model: str) -> None:
        try:
            await asyncio.to_thread(self._stream_model_switch, model)
        except Exception as exc:
            self._hide_busy()
            self._ollama_status.setText(f"{t('settings_switch_failed')} {exc}")
            return

    def _stream_model_switch(self, model: str) -> None:
        url = f"{BACKEND_HTTP}/api/v1/ollama/model/stream"
        with requests.post(
            url,
            json={"model": model},
            stream=True,
            timeout=600,
            headers=self._auth_headers(),
        ) as resp:
            resp.raise_for_status()
            for line in resp.iter_lines():
                if not line:
                    continue
                decoded = line.decode("utf-8")
                if not decoded.startswith("data: "):
                    continue
                payload = decoded[6:]
                try:
                    event_data = json.loads(payload)
                except json.JSONDecodeError:
                    continue

                status = event_data.get("status")
                progress = event_data.get("progress")
                if isinstance(progress, int):
                    self._model_signals.progress.emit(progress, status or "")
                elif status:
                    self._model_signals.progress.emit(-1, status)

                if event_data.get("done"):
                    current = event_data.get("current") or ""
                    error = event_data.get("error") or ""
                    self._model_signals.done.emit(current, error)
                    return

    def _show_busy(self, message: str) -> None:
        if self._busy_dialog is None:
            self._busy_dialog = QProgressDialog(self)
            self._busy_dialog.setWindowModality(Qt.ApplicationModal)
            self._busy_dialog.setCancelButton(None)
            self._busy_dialog.setRange(0, 100)
            self._busy_dialog.setMinimumDuration(0)
            self._busy_dialog.setWindowTitle(t("settings_ollama_busy"))
            self._busy_dialog.setAutoClose(False)
            self._busy_dialog.setAutoReset(False)
            self._busy_dialog.setValue(0)
        self._busy_dialog.setLabelText(message)
        self._busy_dialog.show()

    def _hide_busy(self) -> None:
        if self._busy_dialog is not None:
            self._busy_dialog.hide()

    def _on_model_progress(self, progress: int, status: str) -> None:
        if self._busy_dialog is None:
            return
        if progress >= 0:
            self._busy_dialog.setValue(progress)
        if status:
            self._busy_dialog.setLabelText(status)

    def _on_model_done(self, current: str, error: str) -> None:
        self._hide_busy()
        if error:
            self._ollama_status.setText(f"{t('settings_switch_failed')} {error}")
            return
        if current:
            self._current_model = current
            self._saved_model = current
            self._ollama_status.setText(f"{t('settings_current_model')} {current}")
            self._ollama_combo.setCurrentText(current)
            self._update_model_ui_state()

    def _load_support_status(self) -> None:
        if not self._support_status:
            return
        self._schedule_task(self._load_support_status_async())

    async def _load_support_status_async(self) -> None:
        try:
            payload = await asyncio.to_thread(self._fetch_support_status)
        except requests.HTTPError as exc:
            self._set_support_busy(False)
            message = self._support_error_message(exc)
            self._support_status.setText(message)
            return
        except Exception as exc:
            self._set_support_busy(False)
            self._support_status.setText(f"{t('settings_could_not_load_support')} {exc}")
            return
        self._apply_support_state(payload)

    def _fetch_support_status(self) -> dict:
        resp = requests.get(
            f"{BACKEND_HTTP}/api/support/tunnel",
            timeout=6,
            headers=self._auth_headers(),
        )
        resp.raise_for_status()
        return resp.json()

    def _on_support_enable(self) -> None:
        if not (self._support_enable and self._support_duration):
            return
        if not ask_yes_no_dialog(
            self,
            t("settings_enable_remote_support"),
            t("settings_enable_remote_support_confirm"),
        ):
            return
        duration = self._selected_support_duration()
        self._set_support_busy(True, t("settings_activating_support"))
        self._schedule_task(self._enable_support_async(duration))

    async def _enable_support_async(self, duration: int) -> None:
        try:
            payload = await asyncio.to_thread(
                self._post_support_enable,
                duration,
            )
        except requests.HTTPError as exc:
            self._set_support_busy(False)
            show_error_dialog(self, t("error"), self._support_error_message(exc))
            return
        except Exception as exc:
            self._set_support_busy(False)
            show_error_dialog(self, t("error"), str(exc))
            return
        self._set_support_busy(False)
        self._apply_support_state(payload)

    def _post_support_enable(self, duration: int) -> dict:
        payload = {"action": "open", "duration_minutes": duration}
        resp = requests.post(
            f"{BACKEND_HTTP}/api/support/tunnel",
            json=payload,
            timeout=10,
            headers=self._auth_headers(),
        )
        resp.raise_for_status()
        return resp.json()

    def _on_support_disable(self) -> None:
        if not self._support_disable:
            return
        if not ask_yes_no_dialog(
            self,
            t("settings_disable_remote_support"),
            t("settings_disable_remote_support_confirm"),
        ):
            return
        self._set_support_busy(True, t("settings_closing_support"))
        self._schedule_task(self._disable_support_async())

    async def _disable_support_async(self) -> None:
        try:
            payload = await asyncio.to_thread(self._post_support_disable)
        except requests.HTTPError as exc:
            self._set_support_busy(False)
            show_error_dialog(self, t("error"), self._support_error_message(exc))
            return
        except Exception as exc:
            self._set_support_busy(False)
            show_error_dialog(self, t("error"), str(exc))
            return
        self._set_support_busy(False)
        self._apply_support_state(payload)

    def _post_support_disable(self) -> dict:
        resp = requests.post(
            f"{BACKEND_HTTP}/api/support/tunnel",
            json={"action": "close"},
            timeout=10,
            headers=self._auth_headers(),
        )
        resp.raise_for_status()
        return resp.json()

    def _support_error_message(self, exc: requests.HTTPError) -> str:
        status = getattr(exc.response, "status_code", None)
        detail = None
        try:
            detail = exc.response.json().get("detail")
        except Exception:
            detail = None
        if status == 401:
            return t("settings_bearer_token_required")
        if detail:
            return detail
        return str(exc)

    def _apply_support_state(self, payload: dict) -> None:
        self._support_last_payload = dict(payload)
        active = bool(payload.get("active"))
        port = payload.get("port")
        expires_at = self._format_support_timestamp(payload.get("expires_at"))
        remaining = self._format_support_remaining(payload.get("expires_at"))
        error = payload.get("error")
        self._support_active = active
        if self._support_status:
            if active:
                self._support_status.setText(
                    t(
                        "settings_support_active_message",
                        port=port if port is not None else "-",
                        expires_at=expires_at or "-",
                        remaining=remaining or t("settings_support_expiring_now"),
                    )
                )
            else:
                message = t("settings_support_inactive_message")
                if error:
                    message = f"{message} {error}"
                self._support_status.setText(message)
        if self._support_enable:
            self._support_enable.setEnabled(not active)
        if self._support_disable:
            self._support_disable.setEnabled(active)
        if self._support_duration:
            self._support_duration.setEnabled(not active)

    def _set_support_busy(self, busy: bool, message: str | None = None) -> None:
        if self._support_enable:
            self._support_enable.setEnabled(not busy and not self._support_active)
        if self._support_disable:
            self._support_disable.setEnabled(not busy and self._support_active)
        if self._support_duration:
            self._support_duration.setEnabled(not busy and not self._support_active)
        if message and self._support_status:
            self._support_status.setText(message)

    def _selected_support_duration(self) -> int:
        if not self._support_duration:
            return 60
        idx = self._support_duration.currentIndex()
        if 0 <= idx < len(self._support_duration_values):
            return self._support_duration_values[idx]
        return 60

    def _update_translations(self) -> None:
        """Update all translatable UI elements when language changes."""
        if hasattr(self, "_tabs"):
            self._tabs.setTabText(0, t("settings_tab_system"))
            self._tabs.setTabText(1, t("settings_tab_advanced"))
            self._tabs.setTabText(2, t("settings_tab_ssh"))
            self._tabs.setTabText(3, t("settings_tab_wifi"))
            self._tabs.setTabText(4, t("settings_tab_bluetooth"))
        if hasattr(self, "_timezone_label"):
            self._timezone_label.setText(t("settings_timezone"))
        if hasattr(self, "_application_language_label"):
            self._application_language_label.setText(t("settings_application_language"))
        if hasattr(self, "_today_label"):
            self._today_label.setText(t("settings_today"))
        if hasattr(self, "_focus_mode_new") and self._focus_mode_new:
            self._focus_mode_new.setText(t("settings_add_focus_mode"))
        if hasattr(self, "_model_label"):
            self._model_label.setText(t("settings_model"))
        if hasattr(self, "_duration_label"):
            self._duration_label.setText(t("settings_duration"))
        if hasattr(self, "_support_hint"):
            self._support_hint.setText(t("settings_support_hint"))
        if hasattr(self, "_support_duration") and self._support_duration:
            for idx, key in enumerate(self._support_duration_keys):
                if idx < self._support_duration.count():
                    self._support_duration.setItemText(idx, t(key))
        if hasattr(self, "_support_enable"):
            self._support_enable.setText(t("settings_enable_support"))
        if hasattr(self, "_support_disable"):
            self._support_disable.setText(t("settings_stop_support"))
        if hasattr(self, "_support_status") and self._support_status and self._support_last_payload is not None:
            self._apply_support_state(self._support_last_payload)
        if hasattr(self, "_ollama_apply"):
            self._ollama_apply.setText(t("settings_use"))
        if hasattr(self, "_ollama_reset") and self._ollama_reset:
            self._ollama_reset.setText(t("settings_reset"))
        if hasattr(self, "_system_save_button") and self._system_save_button:
            self._system_save_button.setText(t("settings_save"))
        if hasattr(self, "_system_reset_button") and self._system_reset_button:
            self._system_reset_button.setText(t("settings_reset"))
        if hasattr(self, "_wifi_intro"):
            self._wifi_intro.setText(t("settings_wifi_intro"))
        if hasattr(self, "_wifi_open_button") and self._wifi_open_button:
            self._wifi_open_button.setText(t("settings_wifi_open"))
        if hasattr(self, "_wifi_status"):
            if self._wifi_last_info:
                self._wifi_status.setText(self._format_wifi_status(self._wifi_last_info))
            else:
                self._wifi_status.setText(t("settings_wifi_status_loading"))
        if hasattr(self, "_bluetooth_intro"):
            self._bluetooth_intro.setText(t("settings_bluetooth_intro"))
        if hasattr(self, "_bluetooth_toggle") and self._bluetooth_toggle:
            self._bluetooth_toggle.setText(
                t("settings_bluetooth_toggle_on")
                if self._bluetooth_toggle.isChecked()
                else t("settings_bluetooth_toggle_off")
            )
        if hasattr(self, "_bluetooth_connected_title"):
            self._bluetooth_connected_title.setText(t("settings_bluetooth_connected_devices"))
        if hasattr(self, "_bluetooth_scan_title"):
            self._bluetooth_scan_title.setText(t("settings_bluetooth_scan_results"))
        if hasattr(self, "_bluetooth_power_button") and self._bluetooth_power_button:
            self._bluetooth_power_button.setText(t("settings_bluetooth_power_on"))
        if hasattr(self, "_bluetooth_repair_button") and self._bluetooth_repair_button:
            self._bluetooth_repair_button.setText(t("settings_bluetooth_repair"))
        if hasattr(self, "_bluetooth_refresh_button") and self._bluetooth_refresh_button:
            self._bluetooth_refresh_button.setText(t("settings_bluetooth_refresh"))
        if hasattr(self, "_bluetooth_scan_button") and self._bluetooth_scan_button:
            self._bluetooth_scan_button.setText(t("settings_bluetooth_scan"))
        if hasattr(self, "_bluetooth_pair_button") and self._bluetooth_pair_button:
            self._bluetooth_pair_button.setText(t("settings_bluetooth_pair_connect"))
        if hasattr(self, "_bluetooth_forget_button") and self._bluetooth_forget_button:
            self._bluetooth_forget_button.setText(t("settings_bluetooth_forget"))
        if hasattr(self, "_bluetooth_status"):
            if self._bluetooth_last_info:
                self._apply_bluetooth_info(self._bluetooth_last_info)
            else:
                self._bluetooth_status.setText(t("settings_bluetooth_status_loading"))
        if hasattr(self, "_system_info_labels"):
            keys = [
                "settings_device_prefix",
                "settings_device_number",
                "settings_backend_url",
                "settings_backend_port",
                "settings_backend_bind_host",
                "settings_api_routes_port",
                "settings_admin_users",
                "settings_admin_device_id",
                "settings_ollama_base_url",
                "settings_ollama_model_label",
                "settings_qdrant_devices_path",
            ]
            for label, key in zip(self._system_info_labels, keys):
                label.setText(t(key))
        if hasattr(self, "_language_combo") and self._language_combo:
            self._sync_application_language_combo()
        if hasattr(self, "_focus_mode_tabs_layout"):
            self._populate_focus_mode_options()
        elif hasattr(self, "_focus_mode_info"):
            self._update_focus_mode_info()
        if hasattr(self, "_ollama_description"):
            self._update_model_ui_state()
        if hasattr(self, "_support_duration") and self._support_duration:
            current_idx = self._support_duration.currentIndex()
            self._support_duration.clear()
            for key in self._support_duration_keys:
                self._support_duration.addItem(t(key))
            self._support_duration.setCurrentIndex(current_idx)

    def _sync_application_language_combo(self) -> None:
        if not self._language_combo:
            return
        current_language = "en-US" if get_current_language() == "en" else "nl-NL"
        self._language_combo.blockSignals(True)
        for index in range(self._language_combo.count()):
            if self._language_combo.itemData(index) == current_language:
                self._language_combo.setCurrentIndex(index)
                break
        self._language_combo.blockSignals(False)

    @staticmethod
    def _format_support_timestamp(value: str | None) -> str:
        if not value:
            return ""
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError:
            return value
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone().strftime("%d-%m %H:%M")

    @staticmethod
    def _format_support_remaining(value: str | None) -> str:
        if not value:
            return ""
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError:
            return ""
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        remaining_seconds = int((parsed - datetime.now(timezone.utc)).total_seconds())
        if remaining_seconds <= 0:
            return ""
        total_minutes = max(1, remaining_seconds // 60)
        hours, minutes = divmod(total_minutes, 60)
        if hours and minutes:
            return t("settings_support_remaining_hours_minutes", hours=hours, minutes=minutes)
        if hours:
            return t("settings_support_remaining_hours", hours=hours)
        return t("settings_support_remaining_minutes", minutes=total_minutes)


class ModelSwitchSignals(QObject):
    progress = Signal(int, str)
    done = Signal(str, str)


class PromptTemplateDialog(OverlayDialog):
    def __init__(
        self,
        parent=None,
        *,
        mode_name: str = "",
        prompt_text: str = "",
        builtin: bool = False,
    ):
        super().__init__(parent, width=720, height=620)
        self.action = "cancel"
        self._builtin = builtin
        self.setWindowTitle(t("settings_focus_mode_dialog_title"))

        title = QLabel(
            t("settings_focus_mode_dialog_builtin_title", mode=mode_name)
            if builtin and mode_name
            else t("settings_focus_mode_dialog_title")
        )
        title.setStyleSheet("font-size:24px; font-weight:800; color:#111111;")
        self.card_layout.addWidget(title)

        intro = QLabel(
            t("settings_focus_mode_dialog_builtin_intro")
            if builtin
            else t("settings_focus_mode_dialog_intro")
        )
        intro.setWordWrap(True)
        intro.setStyleSheet("color:#6b7280; font-size:13px; line-height:1.45;")
        self.card_layout.addWidget(intro)

        self._name_label = QLabel(t("settings_focus_mode_name"))
        self._name_label.setStyleSheet("font-size:12px; font-weight:700; color:#3f3a33;")
        self.card_layout.addWidget(self._name_label)

        self._name_input = QLineEdit(mode_name)
        self._name_input.setPlaceholderText(t("settings_focus_mode_name_placeholder"))
        self._name_input.setEnabled(not builtin)
        self._name_input.setStyleSheet(
            "QLineEdit { background:#fffdf8; border:1px solid #e7e0d4; border-radius:16px; padding:12px 14px; font-size:14px; font-weight:600; }"
            "QLineEdit:focus { border:2px solid #facc15; }"
        )
        self.card_layout.addWidget(self._name_input)

        self._prompt_label = QLabel(t("settings_focus_mode_prompt"))
        self._prompt_label.setStyleSheet("font-size:12px; font-weight:700; color:#3f3a33;")
        self.card_layout.addWidget(self._prompt_label)

        self._prompt_input = QPlainTextEdit(prompt_text)
        self._prompt_input.setReadOnly(builtin)
        self._prompt_input.setStyleSheet(
            "QPlainTextEdit { background:#fffdf8; border:1px solid #e7e0d4; border-radius:18px; padding:14px; font-size:14px; color:#171717; }"
            "QPlainTextEdit:focus { border:2px solid #facc15; }"
        )
        self.card_layout.addWidget(self._prompt_input, 1)

        actions = QHBoxLayout()
        actions.setSpacing(10)
        actions.addStretch(1)

        if not builtin:
            cancel = QPushButton(t("cancel"))
            cancel.setCursor(Qt.PointingHandCursor)
            cancel.setStyleSheet(SettingsPage._action_button_style("secondary"))
            cancel.clicked.connect(self.reject)
            actions.addWidget(cancel)

        if not builtin and mode_name:
            delete = QPushButton(t("settings_delete"))
            delete.setCursor(Qt.PointingHandCursor)
            delete.setStyleSheet(SettingsPage._action_button_style("secondary"))
            delete.clicked.connect(self._accept_delete)
            actions.addWidget(delete)

        if not builtin:
            save = QPushButton(t("settings_save"))
            save.setCursor(Qt.PointingHandCursor)
            save.setStyleSheet(SettingsPage._action_button_style("primary"))
            save.clicked.connect(self._accept_save)
            actions.addWidget(save)
        actions.addStretch(1)
        self.card_layout.addLayout(actions)

    def _accept_save(self) -> None:
        self.action = "save"
        self.accept()

    def _accept_delete(self) -> None:
        self.action = "delete"
        self.accept()

    def values(self) -> tuple[str, str]:
        return self._name_input.text().strip(), self._prompt_input.toPlainText().strip()


class ChevronComboBox(QComboBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._popup_open = False

    def showPopup(self) -> None:
        self._popup_open = True
        self.setProperty("popupOpen", True)
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()
        super().showPopup()

    def hidePopup(self) -> None:
        super().hidePopup()
        self._popup_open = False
        self.setProperty("popupOpen", False)
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        self._paint_chevron()

    def _paint_chevron(self) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.TextAntialiasing)
        painter.setPen(Qt.black)
        font = self._scaled_chevron_font(painter.font())
        font.setBold(True)
        painter.setFont(font)
        glyph = "▲" if self._popup_open else "▼"
        painter.drawText(self.rect().adjusted(0, 0, -14, 0), Qt.AlignRight | Qt.AlignVCenter, glyph)

    @staticmethod
    def _scaled_chevron_font(base_font: QFont) -> QFont:
        font = QFont(base_font)
        point_size = font.pointSizeF()
        if point_size and point_size > 0:
            font.setPointSizeF(point_size * 0.96)
            return font
        pixel_size = font.pixelSize()
        if pixel_size and pixel_size > 0:
            font.setPixelSize(max(1, round(pixel_size * 0.96)))
            return font
        font.setPointSize(14)
        return font


class ChevronDateEdit(QDateEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._calendar_open = False

    def showPopup(self) -> None:
        self._calendar_open = True
        self.update()
        super().showPopup()

    def hidePopup(self) -> None:
        super().hidePopup()
        self._calendar_open = False
        self.update()

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        self._paint_chevron()

    def _paint_chevron(self) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.TextAntialiasing)
        painter.setPen(Qt.black)
        font = ChevronComboBox._scaled_chevron_font(painter.font())
        font.setBold(True)
        painter.setFont(font)
        glyph = "▲" if self._calendar_open else "▼"
        painter.drawText(self.rect().adjusted(0, 0, -14, 0), Qt.AlignRight | Qt.AlignVCenter, glyph)


class QLineEditPlaceholder(QLabel):
    """Simple placeholder widget used for display-only fields."""

    def __init__(self, text: str):
        super().__init__(text)
        self.setStyleSheet(
            "border:1px solid #d6d3ce; border-radius:20px; padding:12px 16px;"
            "color:#1f1f1f; background:#fcfbf9;"
        )
