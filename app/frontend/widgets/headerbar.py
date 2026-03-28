import os
from typing import Optional

from PySide6.QtCore import QRect, Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..translations import t, get_current_language, set_language, register_language_change_callback


class LanguageSelectorButton(QPushButton):
    """A button that displays the current language flag and allows switching."""

    language_changed = Signal(str)

    FLAG_STYLES = """
        QPushButton {{
            background-color: #f3f4f6;
            border: 1px solid #d1d5db;
            border-radius: 12px;
            padding: 6px 10px;
            font-size: 14px;
            font-weight: 600;
            min-width: 50px;
        }}
        QPushButton:hover {{
            background-color: #ffffff;
            border-color: {border_color};
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
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(24, 12, 24, 12)
        self._layout.setSpacing(18)
        self.setFixedHeight(72)

        self._brand = QWidget()
        brand_layout = QVBoxLayout(self._brand)
        brand_layout.setContentsMargins(0, 0, 0, 0)
        brand_layout.setSpacing(0)

        self.title = QLabel()
        self.title.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        images_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "images"))
        image_path = os.path.join(images_dir, "aitje.png")
        if os.path.exists(image_path):
            pixmap = QPixmap(image_path)
            # Crop the logo to its visible bounds so Qt does not scale the large transparent canvas.
            pixmap = pixmap.copy(QRect(63, 73, 1231, 513)).scaled(
                126, 36, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            self.title.setPixmap(pixmap)
            self.title.setGraphicsEffect(None)
        else:
            self.title.setText(title)
            self.title.setStyleSheet(
                "font-size:20px; font-weight:800; letter-spacing:0.12em; color:#111111;"
            )
        brand_layout.addWidget(self.title)

        self._layout.addWidget(self._brand, 0, Qt.AlignVCenter)

        self._center = QWidget()
        self._center_layout = QHBoxLayout(self._center)
        self._center_layout.setContentsMargins(0, 0, 0, 0)
        self._center_layout.setSpacing(0)
        self._center_layout.addStretch(1)
        self._layout.addWidget(self._center, 1)

        self._right = QWidget()
        right_layout = QHBoxLayout(self._right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(14)

        self._is_online = True
        self.status = QLabel()
        self.status.setObjectName("HeaderStatus")
        self._update_online_text()
        right_layout.addWidget(self.status, 0, Qt.AlignVCenter)

        self.lang_selector = LanguageSelectorButton()
        self.lang_selector.language_changed.connect(self._on_language_changed)
        right_layout.addWidget(self.lang_selector, 0, Qt.AlignVCenter)

        self.home_btn = QPushButton("Chat")
        self.home_btn.setObjectName("HeaderHomeButton")
        self.home_btn.setCursor(Qt.PointingHandCursor)
        self.home_btn.setStyleSheet(
            "QPushButton {"
            "  background-color: #facc15;"
            "  color: #050505;"
            "  font-weight: 700;"
            "  border-radius: 18px;"
            "  padding: 10px 28px;"
            "  border: 0;"
            "}"
            "QPushButton:hover { background-color: #050505; color: #facc15; }"
        )
        self.home_btn.setMinimumHeight(40)
        self.home_btn.clicked.connect(self.home_requested.emit)
        right_layout.addWidget(self.home_btn, 0, Qt.AlignVCenter)

        self._layout.addWidget(self._right, 0, Qt.AlignVCenter)

        self.setGraphicsEffect(None)

        register_language_change_callback(self._on_language_update)

    def set_center_widget(self, widget: QWidget) -> None:
        while self._center_layout.count():
            item = self._center_layout.takeAt(0)
            child = item.widget()
            if child is not None:
                child.setParent(None)
        self._center_layout.addStretch(1)
        self._center_layout.addWidget(widget, 0, Qt.AlignCenter)
        self._center_layout.addStretch(1)

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
        pass

    def set_online(self, online: bool):
        self._is_online = online
        self._update_online_text()
