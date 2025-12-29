from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

MODAL_QSS = """
QDialog {
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
  padding-top: 8px;
}
QPushButton {
  background: #facc15;
  color: #050505;
  border: none;
  padding: 8px 20px;
  font-weight: 600;
  min-height: 32px;
  border-radius: 16px;
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


def _styled_button(text: str) -> QPushButton:
    btn = QPushButton(text)
    btn.setCursor(Qt.PointingHandCursor)
    btn.setStyleSheet(
        "QPushButton {"
        "  background:#facc15;"
        "  color:#050505;"
        "  border:none;"
        "  border-radius:24px;"
        "  padding:12px 32px;"
        "  font-weight:600;"
        "}"
        "QPushButton:hover { background:#050505; color:#facc15; }"
    )
    btn.setFixedHeight(48)
    return btn


def _base_dialog(parent, title: str, text: str) -> tuple[QDialog, QVBoxLayout]:
    dialog = QDialog(parent)
    dialog.setWindowTitle(title)
    dialog.setStyleSheet(MODAL_QSS)
    layout = QVBoxLayout(dialog)
    layout.setContentsMargins(24, 24, 24, 24)
    layout.setSpacing(16)
    label = QLabel(text)
    label.setWordWrap(True)
    label.setStyleSheet("font-size:16px; font-weight:600; line-height:1.4;")
    layout.addWidget(label)
    return dialog, layout


def show_info_dialog(parent, title: str, text: str) -> None:
    dialog, layout = _base_dialog(parent, title, text)
    btn = _styled_button("Oké")
    btn.clicked.connect(dialog.accept)
    layout.addWidget(btn, 0, Qt.AlignRight)
    dialog.exec()


def show_warning_dialog(parent, title: str, text: str) -> None:
    show_info_dialog(parent, title, text)


def show_error_dialog(parent, title: str, text: str) -> None:
    show_info_dialog(parent, title, text)


def ask_yes_no_dialog(
    parent,
    title: str,
    text: str,
    *,
    default_to_no: bool = True,
) -> bool:
    dialog, layout = _base_dialog(parent, title, text)
    buttons = QHBoxLayout()
    buttons.setSpacing(12)
    no_btn = _styled_button("Nee")
    yes_btn = _styled_button("Ja")
    if default_to_no:
        no_btn.setDefault(True)
    else:
        yes_btn.setDefault(True)
    no_btn.clicked.connect(lambda: dialog.done(0))
    yes_btn.clicked.connect(lambda: dialog.done(1))
    buttons.addWidget(no_btn)
    buttons.addWidget(yes_btn)
    layout.addLayout(buttons)
    return bool(dialog.exec())
