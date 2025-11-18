from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)


class SettingsPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        title = QLabel("Instellingen")
        title.setStyleSheet("font-size:20px; font-weight:600;")
        subtitle = QLabel("Beheer de systeeminstellingen en voorkeuren voor Loci Scientia OS")
        subtitle.setStyleSheet("color:#9ca3af;")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        tabs = QTabWidget()
        tabs.addTab(self._appearance_tab(), "Uiterlijk")
        tabs.addTab(self._system_tab(), "Systeem")
        tabs.addTab(self._network_tab(), "Netwerk")
        tabs.addTab(self._security_tab(), "Beveiliging")
        tabs.addTab(self._advanced_tab(), "Geavanceerd")
        layout.addWidget(tabs, 1)

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
        grid.addWidget(QLineEditPlaceholder("LociNet"), 0, 1)
        grid.addWidget(QLabel("VPN Status"), 1, 0)
        vpn = QLabel("Uitgeschakeld")
        vpn.setStyleSheet("color:#9ca3af;")
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
        flush.setStyleSheet("border:1px solid #374151; border-radius:8px; padding:6px 12px;")
        vbox.addWidget(flush)
        layout.addWidget(card)
        return tab

    @staticmethod
    def _settings_card(title: str) -> QFrame:
        card = QFrame()
        card.setObjectName("Card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.addWidget(QLabel(title))
        return card


class QLineEditPlaceholder(QLabel):
    """Simple placeholder widget used for display-only fields."""

    def __init__(self, text: str):
        super().__init__(text)
        self.setStyleSheet(
            "border:1px solid #374151; border-radius:8px; padding:6px 8px; color:#d1d5db;"
        )
