import os
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QRect, Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ..translations import t, get_current_language, set_language, register_language_change_callback
from .dialog_style import COMPACT_DIALOG_HEIGHT, COMPACT_DIALOG_WIDTH, OverlayDialog


class PowerDialog(OverlayDialog):
    action_requested = Signal(str)
    DIALOG_WIDTH = max(COMPACT_DIALOG_WIDTH, 560)
    DIALOG_HEIGHT = COMPACT_DIALOG_HEIGHT

    def __init__(self, parent=None):
        super().__init__(parent, width=self.DIALOG_WIDTH, height=self.DIALOG_HEIGHT)
        self.setWindowTitle(t("power_dialog_title"))

        title = QLabel(t("power_dialog_title"))
        title.setStyleSheet("font-size: 24px; font-weight: 800; color: #111111;")
        self.card_layout.addWidget(title)

        description = QLabel(t("power_dialog_message"))
        description.setWordWrap(True)
        description.setStyleSheet("font-size: 14px; font-weight: 500; color: #6b7280; line-height: 1.4;")
        self.card_layout.addWidget(description)

        self.card_layout.addStretch(1)

        actions = QHBoxLayout()
        actions.setSpacing(12)

        cancel_btn = self._build_button(t("cancel"), variant="secondary")
        cancel_btn.clicked.connect(self.reject)
        actions.addWidget(cancel_btn, 1)

        shutdown_btn = self._build_button(t("power_dialog_shutdown"))
        shutdown_btn.clicked.connect(lambda: self._emit_action("shutdown"))
        actions.addWidget(shutdown_btn, 1)

        restart_btn = self._build_button(t("power_dialog_restart"))
        restart_btn.clicked.connect(lambda: self._emit_action("restart"))
        actions.addWidget(restart_btn, 1)

        self.card_layout.addLayout(actions)

    def _emit_action(self, action: str) -> None:
        self.action_requested.emit(action)
        self.accept()

    @staticmethod
    def _build_button(text: str, *, variant: str = "primary") -> QPushButton:
        button = QPushButton(text)
        button.setCursor(Qt.PointingHandCursor)
        button.setMinimumHeight(52)
        button.setMinimumWidth(150)
        button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        base_style = (
            "QPushButton {"
            "  border-radius: 18px;"
            "  padding: 10px 20px;"
            "  font-size: 13px;"
            "  font-weight: 700;"
            "  text-align: center;"
            "}"
        )
        if variant == "secondary":
            button.setStyleSheet(
                base_style
                + "QPushButton { background: #f3f4f6; color: #111111; border: 1px solid #e5e7eb; }"
                + "QPushButton:hover { background: #e5e7eb; border-color: #d1d5db; }"
            )
        else:
            button.setStyleSheet(
                base_style
                + "QPushButton { background: #facc15; color: #050505; border: 1px solid #facc15; }"
                + "QPushButton:hover { background: #111111; color: #facc15; border-color: #111111; }"
            )
        return button


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
        self._persist_language(os.environ["LANGUAGE"])
        set_language(self._current_lang)
        self._update_display()
        self.language_changed.emit(self._current_lang)

    def refresh(self):
        """Refresh the display from current language setting."""
        self._current_lang = get_current_language()
        self._update_display()

    @staticmethod
    def _env_file_path() -> Path:
        return Path(__file__).resolve().parents[3] / ".env"

    def _persist_language(self, value: str) -> None:
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
            if name.strip() == "LANGUAGE":
                new_lines.append(f"LANGUAGE={value}")
                updated = True
            else:
                new_lines.append(line)
        if not updated:
            if new_lines and new_lines[-1].strip():
                new_lines.append("")
            new_lines.append(f"LANGUAGE={value}")
        try:
            path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
        except OSError:
            pass


class PowerButton(QPushButton):
    """Circular power button using a unicode power symbol."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("HeaderPowerButton")
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(33, 33)
        self.setText("⏻")
        self.setContentsMargins(0, 0, 0, 0)
        self.setToolTip(t("power_dialog_title"))
        self.setStyleSheet(
            "QPushButton {"
            "  background-color: #facc15;"
            "  color: #111111;"
            "  border: 0;"
            "  border-radius: 16px;"
            "  font-size: 21px;"
            "  font-weight: 700;"
            "  padding: 0;"
            "  text-align: center;"
            "}"
            "QPushButton:hover { background-color: #fcd34d; }"
            "QPushButton:pressed { background-color: #eab308; }"
        )


class HeaderBar(QWidget):
    home_requested = Signal()
    language_changed = Signal(str)
    shutdown_requested = Signal()
    restart_requested = Signal()

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

        self.power_btn = PowerButton()
        self.power_btn.clicked.connect(self._show_power_dialog)
        right_layout.addWidget(self.power_btn, 0, Qt.AlignVCenter)

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

    def _show_power_dialog(self) -> None:
        dialog = PowerDialog(self.window())
        dialog.action_requested.connect(self._handle_power_action)
        dialog.exec()

    def _handle_power_action(self, action: str) -> None:
        if action == "shutdown":
            self.shutdown_requested.emit()
        elif action == "restart":
            self.restart_requested.emit()
