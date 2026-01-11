from PySide6.QtCore import Qt
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
import requests

from ..config import BACKEND_HTTP, BACKEND_TIMEOUT, OLLAMA_MODELS


class SettingsPage(QWidget):
    def __init__(self):
        super().__init__()
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

        self._ollama_progress = QProgressDialog(
            "Ollama model wordt geladen...",
            None,
            0,
            0,
            self,
        )
        self._ollama_progress.setWindowModality(Qt.WindowModal)
        self._ollama_progress.setCancelButton(None)
        self._ollama_progress.setAutoClose(False)
        self._ollama_progress.setAutoReset(False)
        self._ollama_progress.close()
        self._load_ollama_models()

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
        model_card = self._settings_card("Ollama model")
        model_layout = QVBoxLayout(model_card)
        model_layout.setSpacing(12)

        row = QHBoxLayout()
        row.addWidget(QLabel("Model"))
        self._ollama_combo = QComboBox()
        self._ollama_combo.addItems(OLLAMA_MODELS)
        row.addWidget(self._ollama_combo, 1)
        self._ollama_apply_button = QPushButton("Switch")
        self._ollama_apply_button.clicked.connect(self._apply_ollama_model)
        row.addWidget(self._ollama_apply_button)
        model_layout.addLayout(row)

        status_row = QHBoxLayout()
        self._ollama_status = QLabel("Huidig model: onbekend")
        status_row.addWidget(self._ollama_status, 1)
        status_row.addStretch()
        model_layout.addLayout(status_row)

        layout.addWidget(model_card)
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

    def _set_ollama_busy(self, busy: bool, message: str | None = None) -> None:
        if message:
            self._ollama_progress.setLabelText(message)
        if busy:
            self._ollama_progress.show()
        else:
            self._ollama_progress.hide()
        self._ollama_apply_button.setEnabled(not busy)
        self._ollama_combo.setEnabled(not busy)
        self._tabs.tabBar().setEnabled(not busy)

    def _populate_ollama_models(self, models: list[str], current_model: str | None) -> None:
        self._ollama_combo.blockSignals(True)
        self._ollama_combo.clear()
        self._ollama_combo.addItems(models)
        if current_model and current_model in models:
            self._ollama_combo.setCurrentText(current_model)
        self._ollama_combo.blockSignals(False)

    def _load_ollama_models(self) -> None:
        self._set_ollama_busy(True, "Ollama modellen ophalen...")
        try:
            resp = requests.get(
                f"{BACKEND_HTTP}/api/v1/ollama/models",
                timeout=BACKEND_TIMEOUT,
            )
            resp.raise_for_status()
            data = resp.json()
            models = data.get("models") or OLLAMA_MODELS
            current = data.get("current_model") or (models[0] if models else "")
            self._populate_ollama_models(models, current)
            self._ollama_status.setText(f"Huidig model: {current or 'onbekend'}")
        except requests.RequestException as exc:  # pragma: no cover - UI feedback only
            self._populate_ollama_models(OLLAMA_MODELS, None)
            self._ollama_status.setText(f"Kon Ollama-modellen niet laden: {exc}")
        finally:
            self._set_ollama_busy(False)

    def _apply_ollama_model(self) -> None:
        model = self._ollama_combo.currentText().strip()
        if not model:
            return
        self._set_ollama_busy(True, f"Ollama model '{model}' wordt opgehaald...")
        timeout = max(BACKEND_TIMEOUT, 90)
        try:
            resp = requests.post(
                f"{BACKEND_HTTP}/api/v1/ollama/model",
                json={"model": model},
                timeout=timeout,
            )
            resp.raise_for_status()
            data = resp.json()
            models = data.get("models") or OLLAMA_MODELS
            current = data.get("current_model") or model
            self._populate_ollama_models(models, current)
            self._ollama_status.setText(f"Huidig model: {current}")
        except requests.RequestException as exc:  # pragma: no cover - UI feedback only
            self._ollama_status.setText(f"Kon model niet wisselen: {exc}")
        finally:
            self._set_ollama_busy(False)

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


class QLineEditPlaceholder(QLabel):
    """Simple placeholder widget used for display-only fields."""

    def __init__(self, text: str):
        super().__init__(text)
        self.setStyleSheet(
            "border:1px solid #d6d3ce; border-radius:20px; padding:12px 16px;"
            "color:#1f1f1f; background:#fcfbf9;"
        )
