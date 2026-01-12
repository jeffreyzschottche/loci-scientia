import asyncio

import requests
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QProgressDialog,
    QPushButton,
    QSlider,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ..config import BACKEND_BEARER_TOKEN, BACKEND_HTTP, OLLAMA_MODELS

class SettingsPage(QWidget):
    def __init__(self):
        super().__init__()
        self._ollama_combo: QComboBox | None = None
        self._ollama_apply: QPushButton | None = None
        self._ollama_status: QLabel | None = None
        self._current_model: str | None = None
        self._busy_dialog: QProgressDialog | None = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        tabs = QTabWidget()
        tabs.setObjectName("SettingsTabs")
        tabs.addTab(self._appearance_tab(), "Uiterlijk")
        tabs.addTab(self._system_tab(), "Systeem")
        tabs.addTab(self._network_tab(), "Netwerk")
        tabs.addTab(self._security_tab(), "Beveiliging")
        tabs.addTab(self._advanced_tab(), "Geavanceerd")
        tabs.tabBar().setObjectName("SettingsTabsBar")
        layout.addWidget(tabs, 1)

        QTimer.singleShot(0, self._load_models)

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
        body = QWidget()
        grid = QGridLayout(body)
        grid.addWidget(QLabel("Tijdzone"), 0, 0)
        tz = QComboBox()
        tz.addItems(["Europe/Amsterdam", "UTC"])
        grid.addWidget(tz, 0, 1)
        grid.addWidget(QLabel("Updates"), 1, 0)
        grid.addWidget(QCheckBox("Automatisch installeren"), 1, 1)
        card.layout().addWidget(body)
        layout.addWidget(card)
        return tab

    def _network_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        card = self._settings_card("Netwerk")
        body = QWidget()
        grid = QGridLayout(body)
        grid.addWidget(QLabel("WiFi SSID"), 0, 0)
        grid.addWidget(QLineEditPlaceholder("AITJE-Net"), 0, 1)
        grid.addWidget(QLabel("VPN Status"), 1, 0)
        vpn = QLabel("UITGESCHAKELD")
        vpn.setStyleSheet("color:#6b7280; letter-spacing:0.3em; font-size:11px;")
        grid.addWidget(vpn, 1, 1)
        card.layout().addWidget(body)
        layout.addWidget(card)
        return tab

    def _security_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        card = self._settings_card("Beveiliging")
        body = QWidget()
        vbox = QVBoxLayout(body)
        vbox.addWidget(QCheckBox("2FA vereisen voor admin"))
        vbox.addWidget(QCheckBox("Automatisch vergrendelen na 5 minuten"))
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

        card = self._settings_card("Geavanceerde opties")
        body = QWidget()
        vbox = QVBoxLayout(body)
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
        card.layout().addWidget(body)
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
            response = await asyncio.to_thread(
                requests.post,
                f"{BACKEND_HTTP}/api/v1/ollama/model",
                json={"model": model},
                timeout=600,
                headers=self._auth_headers(),
            )
            response.raise_for_status()
            payload = response.json()
        except Exception as exc:
            self._hide_busy()
            self._ollama_status.setText(f"Switchen mislukt: {exc}")
            return

        self._hide_busy()
        self._current_model = payload.get("current", model)
        if self._current_model:
            self._ollama_status.setText(f"Huidig model: {self._current_model}")
            self._ollama_combo.setCurrentText(self._current_model)

    def _show_busy(self, message: str) -> None:
        if self._busy_dialog is None:
            self._busy_dialog = QProgressDialog(self)
            self._busy_dialog.setWindowModality(Qt.ApplicationModal)
            self._busy_dialog.setCancelButton(None)
            self._busy_dialog.setRange(0, 0)
            self._busy_dialog.setMinimumDuration(0)
            self._busy_dialog.setWindowTitle("Ollama bezig")
            self._busy_dialog.setAutoClose(False)
            self._busy_dialog.setAutoReset(False)
        self._busy_dialog.setLabelText(message)
        self._busy_dialog.show()

    def _hide_busy(self) -> None:
        if self._busy_dialog is not None:
            self._busy_dialog.hide()


class QLineEditPlaceholder(QLabel):
    """Simple placeholder widget used for display-only fields."""

    def __init__(self, text: str):
        super().__init__(text)
        self.setStyleSheet(
            "border:1px solid #d6d3ce; border-radius:20px; padding:12px 16px;"
            "color:#1f1f1f; background:#fcfbf9;"
        )
