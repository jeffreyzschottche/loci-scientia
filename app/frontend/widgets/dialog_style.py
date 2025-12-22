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
