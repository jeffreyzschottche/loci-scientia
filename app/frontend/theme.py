AITJE_QSS = """
* { font-family: 'Inter', 'Helvetica Neue', Arial, sans-serif; color: #111111; }
QMainWindow, QWidget#RootWidget {
  background: #ffffff;
  color: #111111;
}
#Sidebar {
  background: #ffffff;
  border-right: 1px solid #ececec;
}
#Header {
  background: #ffffff;
  border-bottom: 1px solid #ececec;
  color: #111111;
}
QLabel#Badge {
  letter-spacing: 0.45em;
  font-size: 11px;
  font-weight: 600;
  color: #facc15;
}
QPushButton {
  background: transparent;
  color: #1c1c1c;
  border: 1px solid transparent;
  padding: 10px 24px;
  text-align: left;
  border-radius: 999px;
  font-weight: 600;
}
QPushButton:hover {
  color: #111111;
  border-color: rgba(17, 17, 17, 0.3);
}
QPushButton[active="true"] {
  background: #ffffff;
  color: #111111;
  border-color: #facc15;
}
QFrame#Card, QWidget#Card {
  background: #ffffff;
  border: 1px solid #ececec;
  border-radius: 28px;
}
QFrame#Card[variant="dark"], QWidget#Card[variant="dark"] {
  background: #111111;
  border: 1px solid rgba(255, 255, 255, 0.12);
  color: #f8fafc;
}
QLineEdit, QTextEdit, QPlainTextEdit {
  background: #fcfbf9;
  border: 1px solid #d6d3ce;
  border-radius: 20px;
  padding: 12px 16px;
  color: #1f1f1f;
}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {
  border: 1px solid #facc15;
}
QProgressBar {
  background: #f1efe8;
  border: 1px solid #dedad1;
  border-radius: 999px;
  text-align: center;
  color: #1c1c1c;
}
QProgressBar::chunk {
  background: #facc15;
  border-radius: 999px;
}
QTableWidget {
  background: #ffffff;
  border: 1px solid #e5e4df;
  border-radius: 32px;
  gridline-color: #f2f0e9;
}
QTableWidget::item { padding: 12px; }
QListWidget {
  background: #ffffff;
  border: 1px solid #e5e4df;
  border-radius: 28px;
}
QTabWidget::pane {
  border: 1px solid #e5e4df;
  border-radius: 28px;
  margin-top: 12px;
}
QTabBar::tab {
  background: #f7f5ef;
  border: 1px solid transparent;
  border-radius: 999px;
  padding: 10px 20px;
  color: #6b7280;
  margin-right: 8px;
  font-weight: 600;
}
QTabBar::tab:selected {
  background: #facc15;
  color: #111111;
  border-color: #facc15;
}
"""
