from PySide6.QtCore import QEvent, QEventLoop, QTimer, Qt
from PySide6.QtGui import QColor, QMouseEvent, QPainter
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from ..translations import t

DEFAULT_DIALOG_WIDTH = 500
DEFAULT_DIALOG_HEIGHT = 550
COMPACT_DIALOG_WIDTH = 420
COMPACT_DIALOG_HEIGHT = 260

BUTTON_WIDTH = 120
BUTTON_HEIGHT = 36

CARD_QSS = """
QFrame#OverlayCard {
  background: #ffffff;
  border-radius: 28px;
  color: #0f172a;
}
QScrollArea {
  background: #ffffff;
  border: none;
}
QScrollArea > QWidget > QWidget {
  background: #ffffff;
}
QLabel {
  color: #0f172a;
  font-weight: 600;
  font-size: 13px;
}
QLineEdit,
QPlainTextEdit,
QComboBox,
QSpinBox {
  background: #ffffff;
  border: 1px solid #111111;
  border-radius: 18px;
  padding: 8px 14px;
  min-height: 36px;
  color: #0f172a;
  font-weight: 400;
}
QLineEdit:focus,
QPlainTextEdit:focus,
QComboBox:focus,
QSpinBox:focus {
  border: 1px solid #facc15;
}
QComboBox::drop-down {
  border: none;
  width: 24px;
}
QComboBox::down-arrow {
  image: none;
}
QDialogButtonBox {
  border: none;
  padding-top: 16px;
}
QPushButton {
  background: #facc15;
  color: #050505;
  border: none;
  padding: 6px 16px;
  font-weight: 600;
  min-height: 36px;
  min-width: 100px;
  border-radius: 18px;
  font-size: 13px;
}
QPushButton:hover {
  background: #050505;
  color: #facc15;
}
QPushButton:disabled {
  background: #fde68a;
  color: #9ca3af;
}
"""

# Keep MODAL_QSS as alias for backward compat with files using it directly
MODAL_QSS = CARD_QSS

CLOSE_BTN_QSS = (
    "QPushButton#OverlayCloseBtn {"
    "  background: transparent;"
    "  color: #0f172a;"
    "  border: none;"
    "  border-radius: 0px;"
    "  font-size: 22px;"
    "  font-weight: 700;"
    "  min-width: 0px;"
    "  min-height: 0px;"
    "  padding: 0px;"
    "}"
    "QPushButton#OverlayCloseBtn:hover {"
    "  color: #facc15;"
    "  background: transparent;"
    "}"
)


class OverlayDialog(QDialog):
    """A frameless dialog rendered as an in-app overlay with a centered card."""

    def __init__(self, parent=None, *, width: int = DEFAULT_DIALOG_WIDTH, height: int = DEFAULT_DIALOG_HEIGHT):
        root_parent = self._overlay_parent(parent)
        super().__init__(root_parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Widget)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowModality(Qt.ApplicationModal)
        self._card_width = width
        self._card_height = height
        self._watched_window = None

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        self.card = QFrame()
        self.card.setObjectName("OverlayCard")
        self.card.setFixedSize(self._card_width, self._card_height)
        self.card.setStyleSheet(CARD_QSS)
        outer.addWidget(self.card, 0, Qt.AlignCenter)

        self.card_layout = QVBoxLayout(self.card)
        self.card_layout.setContentsMargins(28, 20, 28, 24)
        self.card_layout.setSpacing(16)

        # Close X button top-right
        close_row = QHBoxLayout()
        close_row.setContentsMargins(0, 12, 18, 0)
        close_row.addStretch(1)
        self._close_btn = QPushButton("\u2715")
        self._close_btn.setObjectName("OverlayCloseBtn")
        self._close_btn.setFixedSize(24, 24)
        self._close_btn.setCursor(Qt.PointingHandCursor)
        self._close_btn.setStyleSheet(CLOSE_BTN_QSS)
        self._close_btn.clicked.connect(self.reject)
        close_row.addWidget(self._close_btn)
        self.card_layout.addLayout(close_row)

    @staticmethod
    def _overlay_parent(parent):
        if parent is None:
            return None
        win = parent.window()
        if hasattr(win, "centralWidget") and win.centralWidget() is not None:
            return win.centralWidget()
        return win

    def exec(self) -> int:
        self.setResult(0)
        self.show()
        self.raise_()
        self.activateWindow()
        loop = QEventLoop(self)
        self.finished.connect(loop.quit)
        loop.exec()
        return self.result()

    def showEvent(self, event):
        super().showEvent(event)
        self._install_parent_window_filter()
        self._sync_to_parent_window()
        QTimer.singleShot(0, self._sync_to_parent_window)

    def hideEvent(self, event):
        self._remove_parent_window_filter()
        super().hideEvent(event)

    def eventFilter(self, watched, event):
        if watched is self._watched_window and event.type() in {
            QEvent.Move,
            QEvent.Resize,
            QEvent.WindowStateChange,
            QEvent.Show,
        }:
            QTimer.singleShot(0, self._sync_to_parent_window)
        return super().eventFilter(watched, event)

    def _install_parent_window_filter(self) -> None:
        parent = self.parent()
        if parent is None:
            return
        if parent is self._watched_window:
            return
        self._remove_parent_window_filter()
        self._watched_window = parent
        parent.installEventFilter(self)

    def _remove_parent_window_filter(self) -> None:
        if self._watched_window is not None:
            self._watched_window.removeEventFilter(self)
            self._watched_window = None

    def _sync_to_parent_window(self) -> None:
        parent = self.parent()
        if parent is not None:
            self.setGeometry(parent.rect())

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 120))
        painter.end()

    def mousePressEvent(self, event: QMouseEvent):
        # Close when clicking outside the card
        card_rect = self.card.geometry()
        if not card_rect.contains(event.pos()):
            self.reject()
            return
        super().mousePressEvent(event)


def center_dialog(dialog: QDialog) -> None:
    """For OverlayDialog this is a no-op (handled in showEvent).
    For plain QDialog fallback, centers on parent."""
    if isinstance(dialog, OverlayDialog):
        return
    dialog.setFixedSize(DEFAULT_DIALOG_WIDTH, DEFAULT_DIALOG_HEIGHT)
    parent = dialog.parent()
    if parent is not None:
        parent_geo = parent.window().geometry()
        x = parent_geo.x() + (parent_geo.width() - DEFAULT_DIALOG_WIDTH) // 2
        y = parent_geo.y() + (parent_geo.height() - DEFAULT_DIALOG_HEIGHT) // 2
        dialog.move(x, y)


def _styled_button(text: str) -> QPushButton:
    btn = QPushButton(text)
    btn.setCursor(Qt.PointingHandCursor)
    btn.setStyleSheet(
        "QPushButton {"
        "  background:#facc15;"
        "  color:#050505;"
        "  border:none;"
        "  border-radius:18px;"
        "  padding:6px 16px;"
        "  font-weight:600;"
        "  font-size:13px;"
        "  text-align:center;"
        "}"
        "QPushButton:hover { background:#050505; color:#facc15; }"
    )
    btn.setFixedSize(BUTTON_WIDTH, BUTTON_HEIGHT)
    return btn


def _base_dialog(parent, title: str, text: str, *, compact: bool = False) -> tuple[OverlayDialog, QVBoxLayout]:
    dialog = OverlayDialog(
        parent,
        width=COMPACT_DIALOG_WIDTH if compact else DEFAULT_DIALOG_WIDTH,
        height=COMPACT_DIALOG_HEIGHT if compact else DEFAULT_DIALOG_HEIGHT,
    )
    dialog.setWindowTitle(title)
    label = QLabel(text)
    label.setWordWrap(True)
    label.setStyleSheet("font-size:15px; font-weight:600; line-height:1.4;")
    dialog.card_layout.addWidget(label)
    return dialog, dialog.card_layout


def show_info_dialog(parent, title: str, text: str, *, compact: bool = False) -> None:
    dialog, layout = _base_dialog(parent, title, text, compact=compact)
    btn = _styled_button(t("ok"))
    btn.clicked.connect(dialog.accept)
    layout.addStretch(1)
    layout.addWidget(btn, 0, Qt.AlignCenter)
    dialog.exec()


def show_warning_dialog(parent, title: str, text: str, *, compact: bool = False) -> None:
    show_info_dialog(parent, title, text, compact=compact)


def show_error_dialog(parent, title: str, text: str, *, compact: bool = False) -> None:
    show_info_dialog(parent, title, text, compact=compact)


def ask_yes_no_dialog(
    parent,
    title: str,
    text: str,
    *,
    default_to_no: bool = True,
) -> bool:
    dialog, layout = _base_dialog(parent, title, text, compact=True)
    layout.addStretch(1)
    buttons = QHBoxLayout()
    buttons.setSpacing(12)
    no_btn = _styled_button(t("no"))
    yes_btn = _styled_button(t("yes"))
    if default_to_no:
        no_btn.setDefault(True)
    else:
        yes_btn.setDefault(True)
    no_btn.clicked.connect(lambda: dialog.done(0))
    yes_btn.clicked.connect(lambda: dialog.done(1))
    buttons.addStretch(1)
    buttons.addWidget(no_btn)
    buttons.addWidget(yes_btn)
    buttons.addStretch(1)
    layout.addLayout(buttons)
    return bool(dialog.exec())
