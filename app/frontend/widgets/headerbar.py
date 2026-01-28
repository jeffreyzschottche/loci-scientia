import os
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from ..translations import t, get_current_language, set_language, register_language_change_callback


class LanguageSelectorButton(QPushButton):
    """A button that displays the current language flag and allows switching."""

    language_changed = Signal(str)

    FLAG_STYLES = """
        QPushButton {{
            background-color: transparent;
            border: 2px solid {border_color};
            border-radius: 4px;
            padding: 4px 8px;
            font-size: 14px;
            font-weight: 600;
            min-width: 50px;
        }}
        QPushButton:hover {{
            background-color: #f3f4f6;
            border-color: #facc15;
        }}
    """

    def __init__(self):
        super().__init__()
        self.setCursor(Qt.PointingHandCursor)
        self._current_lang = get_current_language()
        self._update_display()
        self.clicked.connect(self._toggle_language)

    def _update_display(self):
        """Update button text and style based on current language."""
        if self._current_lang == "nl":
            self.setText("🇳🇱 NL")
            border_color = "#facc15"
        else:
            self.setText("🇬🇧 EN")
            border_color = "#facc15"
        self.setStyleSheet(self.FLAG_STYLES.format(border_color=border_color))

    def _toggle_language(self):
        """Toggle between NL and EN."""
        if self._current_lang == "nl":
            self._current_lang = "en"
            os.environ["LANGUAGE"] = "en-US"
        else:
            self._current_lang = "nl"
            os.environ["LANGUAGE"] = "nl-NL"
        set_language(self._current_lang)
        self._update_display()
        self.language_changed.emit(self._current_lang)

    def refresh(self):
        """Refresh the display from current language setting."""
        self._current_lang = get_current_language()
        self._update_display()


class HeaderBar(QWidget):
    home_requested = Signal()
    language_changed = Signal(str)

    def __init__(self, title: str, subtitle: Optional[str] = None):
        super().__init__()
        self.setObjectName("Header")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(24, 12, 24, 12)
        layout.setSpacing(16)
        self.setFixedHeight(80)

        brand = QWidget()
        brand_layout = QVBoxLayout(brand)
        brand_layout.setContentsMargins(0, 0, 0, 0)
        brand_layout.setSpacing(2)

        self.title = QLabel(title)
        self.title.setStyleSheet(
            "font-size:26px; font-weight:800; letter-spacing:0.02em; color:#111111;"
        )
        self.subtitle = QLabel(subtitle or t("subtitle_local_ai_console"))
        self.subtitle.setStyleSheet(
            "color:#9ca3af; font-size:11px; letter-spacing:0.45em;"
        )
        brand_layout.addWidget(self.title)
        brand_layout.addWidget(self.subtitle)

        layout.addWidget(brand, 0, Qt.AlignVCenter)
        layout.addStretch(1)

        self._is_online = True
        self.status = QLabel()
        self.status.setObjectName("HeaderStatus")
        self._update_online_text()
        layout.addWidget(self.status, 0, Qt.AlignVCenter)

        self.lang_selector = LanguageSelectorButton()
        self.lang_selector.language_changed.connect(self._on_language_changed)
        layout.addWidget(self.lang_selector, 0, Qt.AlignVCenter)

        self.home_btn = QPushButton("Chat")
        self.home_btn.setObjectName("HeaderHomeButton")
        self.home_btn.setCursor(Qt.PointingHandCursor)
        self.home_btn.setStyleSheet(
            "QPushButton {"
            "  background-color: #facc15;"
            "  color: #050505;"
            "  font-weight: 600;"
            "  border-radius: 20px;"
            "  padding: 12px 32px;"
            "  border: 0;"
            "}"
            "QPushButton:hover { background-color: #050505; color: #facc15; }"
        )
        self.home_btn.setMinimumHeight(40)
        self.home_btn.clicked.connect(self.home_requested.emit)
        layout.addWidget(self.home_btn, 0, Qt.AlignVCenter)

        register_language_change_callback(self._on_language_update)

    def _on_language_changed(self, lang: str):
        """Handle language change from selector."""
        self._update_online_text()
        self.language_changed.emit(lang)

    def _on_language_update(self):
        """Update UI when language changes."""
        self._update_online_text()
        self.lang_selector.refresh()

    def _update_online_text(self):
        """Update online/offline text based on current language."""
        if self._is_online:
            text = f"● {t('online')}"
            color = "#16a34a"
        else:
            text = f"● {t('offline')}"
            color = "#ef4444"
        self.status.setText(text)
        self.status.setStyleSheet(
            f"color:{color}; font-weight:600; letter-spacing:0.08em;"
        )

    def set_title(self, title: str):
        self.title.setText(title)

    def set_subtitle(self, subtitle: str):
        self.subtitle.setText(subtitle)

    def set_online(self, online: bool):
        self._is_online = online
        self._update_online_text()
