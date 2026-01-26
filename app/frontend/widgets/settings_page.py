from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import available_timezones

import requests
from PySide6.QtCore import QObject, Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QProgressDialog,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ..config import BACKEND_BEARER_TOKEN, BACKEND_HTTP, OLLAMA_MODELS
from .dialog_style import ask_yes_no_dialog, show_error_dialog

class SettingsPage(QWidget):
    def __init__(self):
        super().__init__()
        self._ollama_combo: QComboBox | None = None
        self._ollama_apply: QPushButton | None = None
        self._ollama_status: QLabel | None = None
        self._current_model: str | None = None
        self._busy_dialog: QProgressDialog | None = None
        self._support_status: QLabel | None = None
        self._support_enable: QPushButton | None = None
        self._support_disable: QPushButton | None = None
        self._support_duration: QComboBox | None = None
        self._timezone_combo: QComboBox | None = None
        self._timezone_loading = False
        self._language_combo: QComboBox | None = None
        self._display_timeout_combo: QComboBox | None = None
        self._system_loading = False
        self._support_active = False
        self._support_durations = {
            "30 min": 30,
            "1 uur": 60,
            "4 uur": 240,
        }
        self._model_signals = ModelSwitchSignals()
        self._model_signals.progress.connect(self._on_model_progress)
        self._model_signals.done.connect(self._on_model_done)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        tabs = QTabWidget()
        tabs.setObjectName("SettingsTabs")
        tabs.addTab(self._system_tab(), "Systeem")
        tabs.addTab(self._advanced_tab(), "Geavanceerd")
        tabs.tabBar().setObjectName("SettingsTabsBar")
        layout.addWidget(tabs, 1)

        QTimer.singleShot(0, self._load_models)
        QTimer.singleShot(0, self._load_support_status)

    def _system_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        card = self._settings_card()
        body = QWidget()
        grid = QGridLayout(body)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(12)
        grid.setColumnStretch(1, 1)
        grid.addWidget(QLabel("Tijdzone"), 0, 0)
        self._timezone_combo = QComboBox()
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
        self._timezone_combo.currentTextChanged.connect(self._on_timezone_changed)
        timezone_wrap = QHBoxLayout()
        timezone_wrap.addWidget(self._timezone_combo)
        timezone_wrap.addStretch(1)
        grid.addLayout(timezone_wrap, 0, 1)

        grid.addWidget(QLabel("Taal"), 1, 0)
        self._language_combo = QComboBox()
        for label, value in self._language_options():
            self._language_combo.addItem(label, value)
        current_language = self._current_language()
        if current_language:
            for index in range(self._language_combo.count()):
                if self._language_combo.itemData(index) == current_language:
                    self._language_combo.setCurrentIndex(index)
                    break
        self._language_combo.currentIndexChanged.connect(self._on_language_changed)
        language_wrap = QHBoxLayout()
        language_wrap.addWidget(self._language_combo)
        language_wrap.addStretch(1)
        grid.addLayout(language_wrap, 1, 1)

        grid.addWidget(QLabel("Beeldscherm timeout"), 2, 0)
        self._display_timeout_combo = QComboBox()
        for label, value in self._display_timeout_options():
            self._display_timeout_combo.addItem(label, value)
        current_timeout = self._current_display_timeout()
        if current_timeout is not None:
            for index in range(self._display_timeout_combo.count()):
                if self._display_timeout_combo.itemData(index) == current_timeout:
                    self._display_timeout_combo.setCurrentIndex(index)
                    break
        self._display_timeout_combo.currentIndexChanged.connect(
            self._on_display_timeout_changed
        )
        timeout_wrap = QHBoxLayout()
        timeout_wrap.addWidget(self._display_timeout_combo)
        timeout_wrap.addStretch(1)
        grid.addLayout(timeout_wrap, 2, 1)
        self._system_loading = False
        card.layout().addWidget(body)
        layout.addWidget(card)
        return tab

    def _advanced_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        model_card = self._settings_card("Ollama model")
        model_body = QWidget()
        model_layout = QGridLayout(model_body)
        model_layout.setHorizontalSpacing(12)
        model_layout.addWidget(QLabel("Model"), 0, 0)
        self._ollama_combo = QComboBox()
        self._ollama_combo.setEnabled(False)
        model_layout.addWidget(self._ollama_combo, 0, 1)
        self._ollama_apply = QPushButton("Gebruik")
        self._ollama_apply.setEnabled(False)
        self._ollama_apply.clicked.connect(self._on_apply_model)
        model_layout.addWidget(self._ollama_apply, 0, 2)
        self._ollama_status = QLabel("Beschikbare modellen laden...")
        self._ollama_status.setStyleSheet("color:#6b7280; font-size:12px;")
        model_layout.addWidget(self._ollama_status, 1, 0, 1, 3)
        model_card.layout().addWidget(model_body)
        layout.addWidget(model_card)

        support_card = self._settings_card("Remote support (Tailscale)")
        support_body = QWidget()
        support_layout = QVBoxLayout(support_body)
        support_layout.setSpacing(10)
        support_hint = QLabel(
            "Schakel alleen in met expliciete toestemming van de klant. "
            "We starten tijdelijk een Tailscale-verbinding voor support en sluiten automatisch."
        )
        support_hint.setWordWrap(True)
        support_hint.setStyleSheet("color:#6b7280; font-size:12px;")
        support_layout.addWidget(support_hint)

        support_form = QGridLayout()
        support_form.setHorizontalSpacing(12)
        support_form.addWidget(QLabel("Duur"), 0, 0)
        self._support_duration = QComboBox()
        self._support_duration.addItems(list(self._support_durations.keys()))
        support_form.addWidget(self._support_duration, 0, 1)
        support_layout.addLayout(support_form)

        self._support_status = QLabel("Support status laden...")
        self._support_status.setStyleSheet("color:#6b7280; font-size:12px;")
        support_layout.addWidget(self._support_status)

        support_actions = QHBoxLayout()
        self._support_enable = QPushButton("Activeer ondersteuning")
        self._support_disable = QPushButton("Stop ondersteuning")
        self._support_disable.setEnabled(False)
        support_actions.addWidget(self._support_enable)
        support_actions.addWidget(self._support_disable)
        support_layout.addLayout(support_actions)
        self._support_enable.clicked.connect(self._on_support_enable)
        self._support_disable.clicked.connect(self._on_support_disable)

        support_card.layout().addWidget(support_body)
        layout.addWidget(support_card)
        return tab

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

    @staticmethod
    def _display_timeout_options() -> list[tuple[str, int]]:
        return [
            ("Nooit", 0),
            ("1 minuut", 1),
            ("5 minuten", 5),
            ("15 minuten", 15),
            ("30 minuten", 30),
            ("1 uur", 60),
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

    def _current_display_timeout(self) -> int | None:
        env_value = os.environ.get("DISPLAY_TIMEOUT_MINUTES")
        if env_value:
            return self._parse_timeout(env_value)
        value = self._read_env_value("DISPLAY_TIMEOUT_MINUTES")
        if value:
            return self._parse_timeout(value)
        return None

    @staticmethod
    def _parse_timeout(value: str) -> int | None:
        try:
            return int(str(value).strip())
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _env_file_path() -> Path:
        return Path(__file__).resolve().parents[3] / ".env"

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

    def _set_env_value(self, key: str, value: str) -> None:
        path = self._env_file_path()
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except FileNotFoundError:
            lines = []
        updated = False
        new_lines: list[str] = []
        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in line:
                new_lines.append(line)
                continue
            name, _ = line.split("=", 1)
            if name.strip() == key:
                new_lines.append(f"{key}={value}")
                updated = True
            else:
                new_lines.append(line)
        if not updated:
            if new_lines and new_lines[-1].strip():
                new_lines.append("")
            new_lines.append(f"{key}={value}")
        path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")

    def _on_timezone_changed(self, timezone: str) -> None:
        if self._timezone_loading:
            return
        value = timezone.strip()
        if not value:
            return
        try:
            self._set_env_value("TIMEZONE", value)
            os.environ["TIMEZONE"] = value
        except Exception as exc:
            show_error_dialog(self, "Fout", f"Kon tijdzone niet opslaan: {exc}")

    def _on_language_changed(self, _index: int | None = None) -> None:
        if self._system_loading or not self._language_combo:
            return
        value = self._language_combo.currentData()
        if not value:
            return
        try:
            self._set_env_value("LANGUAGE", str(value))
            os.environ["LANGUAGE"] = str(value)
        except Exception as exc:
            show_error_dialog(self, "Fout", f"Kon taal niet opslaan: {exc}")

    def _on_display_timeout_changed(self, _index: int | None = None) -> None:
        if self._system_loading or not self._display_timeout_combo:
            return
        value = self._display_timeout_combo.currentData()
        if value is None:
            return
        try:
            self._set_env_value("DISPLAY_TIMEOUT_MINUTES", str(value))
            os.environ["DISPLAY_TIMEOUT_MINUTES"] = str(value)
        except Exception as exc:
            show_error_dialog(self, "Fout", f"Kon beeldscherm timeout niet opslaan: {exc}")

    def _auth_headers(self) -> dict:
        if BACKEND_BEARER_TOKEN:
            return {"Authorization": f"Bearer {BACKEND_BEARER_TOKEN}"}
        return {}

    def _load_models(self) -> None:
        if not self._ollama_combo or not self._ollama_status:
            return
        asyncio.create_task(self._load_models_async())

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
                self._ollama_combo.clear()
                self._ollama_combo.addItems(fallback)
                self._ollama_combo.setEnabled(True)
                self._ollama_apply.setEnabled(True)
                self._ollama_status.setText(
                    "Backend niet bereikbaar; lokaal modellenlijstje geladen."
                )
                return
            self._ollama_status.setText(f"Kon modellen niet ophalen: {exc}")
            return

        available = payload.get("available", [])
        current = payload.get("current")
        self._current_model = current
        self._ollama_combo.clear()
        self._ollama_combo.addItems(available)
        if current in available:
            self._ollama_combo.setCurrentText(current)
        self._ollama_combo.setEnabled(bool(available))
        self._ollama_apply.setEnabled(bool(available))
        if current:
            self._ollama_status.setText(f"Huidig model: {current}")
        else:
            self._ollama_status.setText("Geen actief model ingesteld.")

    def _on_apply_model(self) -> None:
        if not self._ollama_combo or not self._ollama_status:
            return
        model = self._ollama_combo.currentText().strip()
        if not model:
            return
        if model == self._current_model:
            self._ollama_status.setText(f"Model {model} is al actief.")
            return

        self._show_busy(f"Ollama haalt {model} op...")
        asyncio.create_task(self._apply_model_async(model))

    async def _apply_model_async(self, model: str) -> None:
        try:
            await asyncio.to_thread(self._stream_model_switch, model)
        except Exception as exc:
            self._hide_busy()
            self._ollama_status.setText(f"Switchen mislukt: {exc}")
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
            self._busy_dialog.setWindowTitle("Ollama bezig")
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
            self._ollama_status.setText(f"Switchen mislukt: {error}")
            return
        if current:
            self._current_model = current
            self._ollama_status.setText(f"Huidig model: {current}")
            self._ollama_combo.setCurrentText(current)

    def _load_support_status(self) -> None:
        if not self._support_status:
            return
        asyncio.create_task(self._load_support_status_async())

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
            self._support_status.setText(f"Kon support status niet laden: {exc}")
            return
        self._apply_support_state(payload)

    def _fetch_support_status(self) -> dict:
        resp = requests.get(
            f"{BACKEND_HTTP}/api/v1/support/ssh",
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
            "Remote support inschakelen",
            "Dit opent tijdelijke SSH-toegang voor support. "
            "Schakel alleen in met expliciete toestemming. Doorgaan?",
        ):
            return
        duration = self._selected_support_duration()
        self._set_support_busy(True, "Ondersteuning activeren...")
        asyncio.create_task(self._enable_support_async(duration))

    async def _enable_support_async(self, duration: int) -> None:
        try:
            payload = await asyncio.to_thread(
                self._post_support_enable,
                duration,
            )
        except requests.HTTPError as exc:
            self._set_support_busy(False)
            show_error_dialog(self, "Fout", self._support_error_message(exc))
            return
        except Exception as exc:
            self._set_support_busy(False)
            show_error_dialog(self, "Fout", str(exc))
            return
        self._set_support_busy(False)
        self._apply_support_state(payload)

    def _post_support_enable(self, duration: int) -> dict:
        payload = {"duration_minutes": duration}
        resp = requests.post(
            f"{BACKEND_HTTP}/api/v1/support/ssh/enable",
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
            "Remote support uitschakelen",
            "Weet je zeker dat je de supporttoegang wilt afsluiten?",
        ):
            return
        self._set_support_busy(True, "Ondersteuning afsluiten...")
        asyncio.create_task(self._disable_support_async())

    async def _disable_support_async(self) -> None:
        try:
            payload = await asyncio.to_thread(self._post_support_disable)
        except requests.HTTPError as exc:
            self._set_support_busy(False)
            show_error_dialog(self, "Fout", self._support_error_message(exc))
            return
        except Exception as exc:
            self._set_support_busy(False)
            show_error_dialog(self, "Fout", str(exc))
            return
        self._set_support_busy(False)
        self._apply_support_state(payload)

    def _post_support_disable(self) -> dict:
        resp = requests.post(
            f"{BACKEND_HTTP}/api/v1/support/ssh/disable",
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
            return (
                "Backend verwacht een Bearer token. "
                "Stel BACKEND_BEARER_TOKEN in op het apparaat."
            )
        if detail:
            return detail
        return str(exc)

    def _apply_support_state(self, payload: dict) -> None:
        active = bool(payload.get("active"))
        session_id = payload.get("session_id")
        expires_at = self._format_support_timestamp(payload.get("expires_at"))
        last_error = payload.get("last_error")
        self._support_active = active
        if self._support_status:
            if active:
                parts = ["Actief"]
                if expires_at:
                    parts.append(f"tot {expires_at}")
                if session_id:
                    parts.append(f"(sessie {session_id})")
                self._support_status.setText(" ".join(parts))
            else:
                message = "Uitgeschakeld"
                if last_error:
                    message = f"{message} (laatste fout: {last_error})"
                self._support_status.setText(message)
        if self._support_enable:
            self._support_enable.setEnabled(not active)
        if self._support_disable:
            self._support_disable.setEnabled(active)

    def _set_support_busy(self, busy: bool, message: str | None = None) -> None:
        if self._support_enable:
            self._support_enable.setEnabled(not busy and not self._support_active)
        if self._support_disable:
            self._support_disable.setEnabled(not busy and self._support_active)
        if message and self._support_status:
            self._support_status.setText(message)

    def _selected_support_duration(self) -> int:
        if not self._support_duration:
            return 60
        return self._support_durations.get(self._support_duration.currentText(), 60)

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


class ModelSwitchSignals(QObject):
    progress = Signal(int, str)
    done = Signal(str, str)


class QLineEditPlaceholder(QLabel):
    """Simple placeholder widget used for display-only fields."""

    def __init__(self, text: str):
        super().__init__(text)
        self.setStyleSheet(
            "border:1px solid #d6d3ce; border-radius:20px; padding:12px 16px;"
            "color:#1f1f1f; background:#fcfbf9;"
        )
