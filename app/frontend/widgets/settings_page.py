from __future__ import annotations

import requests

from PySide6.QtCore import QThread, Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QSlider,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ..config import BACKEND_HTTP, BACKEND_TIMEOUT


API_BASE = BACKEND_HTTP


class ModelTask(QThread):
    success = Signal(object)
    failure = Signal(str)

    def __init__(self, task_fn):
        super().__init__()
        self._task_fn = task_fn

    def run(self):
        try:
            result = self._task_fn()
        except Exception as exc:  # pragma: no cover - UI feedback only
            self.failure.emit(str(exc))
        else:
            self.success.emit(result)

class SettingsPage(QWidget):
    def __init__(self):
        super().__init__()
        self._tasks: list[ModelTask] = []
        self._current_model: str | None = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        self._tabs = QTabWidget()
        self._tabs.setObjectName("SettingsTabs")
        self._tabs.addTab(self._appearance_tab(), "Uiterlijk")
        self._tabs.addTab(self._system_tab(), "Systeem")
        self._tabs.addTab(self._network_tab(), "Netwerk")
        self._tabs.addTab(self._security_tab(), "Beveiliging")
        self._tabs.addTab(self._advanced_tab(), "Geavanceerd")
        self._tabs.tabBar().setObjectName("SettingsTabsBar")
        layout.addWidget(self._tabs, 1)

        self._busy_overlay = QFrame(self)
        self._busy_overlay.setStyleSheet(
            "background: rgba(15, 23, 42, 0.35); border-radius: 20px;"
        )
        self._busy_overlay.hide()
        overlay_layout = QVBoxLayout(self._busy_overlay)
        overlay_layout.setAlignment(Qt.AlignCenter)
        self._busy_label = QLabel("Ollama model wordt geladen…")
        self._busy_label.setStyleSheet("color: #ffffff; font-weight: 600;")
        self._busy_spinner = QProgressBar()
        self._busy_spinner.setRange(0, 0)
        self._busy_spinner.setFixedWidth(240)
        overlay_layout.addWidget(self._busy_label, 0, Qt.AlignCenter)
        overlay_layout.addWidget(self._busy_spinner, 0, Qt.AlignCenter)

        self._load_models()

    def _appearance_tab(self) -> QWidget:
        tab = QWidget()
        vbox = QVBoxLayout(tab)
        vbox.setSpacing(12)

        theme_box = self._settings_card("Interface Instellingen")
        theme_layout = QVBoxLayout(theme_box)
        theme_layout.setSpacing(12)
        theme_selector = QHBoxLayout()
        theme_selector.addWidget(QLabel("Thema"))
        combo = QComboBox()
        combo.addItems(["Donker", "Licht"])
        theme_selector.addWidget(combo)
        theme_layout.addLayout(theme_selector)

        font_layout = QHBoxLayout()
        font_layout.addWidget(QLabel("Lettergrootte"))
        slider = QSlider(Qt.Horizontal)
        slider.setValue(50)
        font_layout.addWidget(slider)
        theme_layout.addLayout(font_layout)

        checkbox = QCheckBox("Toon systeem notificaties")
        checkbox.setChecked(True)
        theme_layout.addWidget(checkbox)

        compact = QCheckBox("Compacte modus")
        theme_layout.addWidget(compact)

        vbox.addWidget(theme_box)
        return tab

    def _system_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        card = self._settings_card("Systeem")
        grid = QGridLayout(card)
        grid.addWidget(QLabel("Tijdzone"), 0, 0)
        tz = QComboBox()
        tz.addItems(["Europe/Amsterdam", "UTC"])
        grid.addWidget(tz, 0, 1)
        grid.addWidget(QLabel("Updates"), 1, 0)
        grid.addWidget(QCheckBox("Automatisch installeren"), 1, 1)
        layout.addWidget(card)

        model_card = self._settings_card("Ollama Model")
        model_layout = QVBoxLayout(model_card)
        row = QHBoxLayout()
        row.addWidget(QLabel("Actief model"))
        self._model_combo = QComboBox()
        self._model_combo.setMinimumWidth(200)
        row.addWidget(self._model_combo, 1)
        model_layout.addLayout(row)
        self._model_status = QLabel("Beschikbare modellen ophalen…")
        self._model_status.setStyleSheet("color:#6b7280; font-size:12px;")
        model_layout.addWidget(self._model_status)
        self._model_switch_btn = QPushButton("Model wisselen")
        self._model_switch_btn.setCursor(Qt.PointingHandCursor)
        self._model_switch_btn.setStyleSheet(
            "QPushButton {"
            "  background:#111827;"
            "  color:#ffffff;"
            "  border-radius:999px;"
            "  padding:8px 20px;"
            "  font-weight:600;"
            "}"
            "QPushButton:hover { background:#1f2937; }"
        )
        self._model_switch_btn.clicked.connect(self._switch_model)
        model_layout.addWidget(self._model_switch_btn, 0, Qt.AlignLeft)
        layout.addWidget(model_card)
        return tab

    def _network_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        card = self._settings_card("Netwerk")
        grid = QGridLayout(card)
        grid.addWidget(QLabel("WiFi SSID"), 0, 0)
        grid.addWidget(QLineEditPlaceholder("AITJE-Net"), 0, 1)
        grid.addWidget(QLabel("VPN Status"), 1, 0)
        vpn = QLabel("UITGESCHAKELD")
        vpn.setStyleSheet("color:#6b7280; letter-spacing:0.3em; font-size:11px;")
        grid.addWidget(vpn, 1, 1)
        layout.addWidget(card)
        return tab

    def _security_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        card = self._settings_card("Beveiliging")
        vbox = QVBoxLayout(card)
        vbox.addWidget(QCheckBox("2FA vereisen voor admin"))
        vbox.addWidget(QCheckBox("Automatisch vergrendelen na 5 minuten"))
        layout.addWidget(card)
        return tab

    def _advanced_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        card = self._settings_card("Geavanceerde opties")
        vbox = QVBoxLayout(card)
        flush = QPushButton("Cache legen")
        flush.setStyleSheet(
            "QPushButton {"
            "  background:#facc15;"
            "  color:#050505;"
            "  border-radius:999px;"
            "  padding:8px 24px;"
            "  font-weight:600;"
            "}"
            "QPushButton:hover { background:#050505; color:#facc15; }"
        )
        vbox.addWidget(flush)
        layout.addWidget(card)
        return tab

    @staticmethod
    def _settings_card(title: str) -> QFrame:
        card = QFrame()
        card.setObjectName("Card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 16, 16, 16)
        label = QLabel(title)
        label.setStyleSheet("font-weight:700; letter-spacing:0.02em;")
        layout.addWidget(label)
        return card

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._busy_overlay.setGeometry(self.rect())

    def _set_busy(self, busy: bool, message: str | None = None) -> None:
        if message:
            self._busy_label.setText(message)
        if busy:
            self._busy_overlay.setGeometry(self.rect())
        self._busy_overlay.setVisible(busy)
        if busy:
            self._busy_overlay.raise_()
        if hasattr(self, "_model_switch_btn"):
            self._model_switch_btn.setEnabled(not busy)
        if hasattr(self, "_model_combo"):
            self._model_combo.setEnabled(not busy)

    def _start_task(self, task_fn, on_success, on_failure) -> None:
        task = ModelTask(task_fn)
        task.success.connect(on_success)
        task.failure.connect(on_failure)
        task.finished.connect(lambda: self._tasks.remove(task))
        task.finished.connect(task.deleteLater)
        self._tasks.append(task)
        task.start()

    def _load_models(self) -> None:
        def task():
            resp = requests.get(f"{API_BASE}/api/v1/ollama/models", timeout=BACKEND_TIMEOUT)
            resp.raise_for_status()
            return resp.json()

        def on_success(payload):
            models = payload.get("available_models", [])
            current = payload.get("current_model")
            self._current_model = current
            self._model_combo.clear()
            if models:
                self._model_combo.addItems(models)
            if current:
                index = self._model_combo.findText(current)
                if index >= 0:
                    self._model_combo.setCurrentIndex(index)
            self._model_status.setText(f"Huidig model: {current}" if current else "Modelstatus onbekend.")

        def on_failure(message: str):
            self._model_status.setText(f"Kon modellen niet laden: {message}")

        self._start_task(task, on_success, on_failure)

    def _switch_model(self) -> None:
        if not self._model_combo.currentText():
            self._model_status.setText("Selecteer eerst een model.")
            return
        selected = self._model_combo.currentText()
        if selected == self._current_model:
            self._model_status.setText(f"'{selected}' is al actief.")
            return

        def task():
            resp = requests.post(
                f"{API_BASE}/api/v1/ollama/model",
                json={"model": selected},
                timeout=600,
            )
            resp.raise_for_status()
            return resp.json()

        def on_success(payload):
            current = payload.get("current_model")
            self._current_model = current
            self._model_status.setText(f"Model gewijzigd naar {current}.")
            self._set_busy(False)

        def on_failure(message: str):
            self._model_status.setText(f"Wisselen mislukt: {message}")
            self._set_busy(False)

        self._set_busy(True, "Ollama model wordt geladen…")
        self._start_task(task, on_success, on_failure)


class QLineEditPlaceholder(QLabel):
    """Simple placeholder widget used for display-only fields."""

    def __init__(self, text: str):
        super().__init__(text)
        self.setStyleSheet(
            "border:1px solid #d6d3ce; border-radius:20px; padding:12px 16px;"
            "color:#1f1f1f; background:#fcfbf9;"
        )
