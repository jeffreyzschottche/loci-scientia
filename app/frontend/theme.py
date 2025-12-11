AITJE_QSS = """
* { font-family: 'Inter', 'Helvetica Neue', Arial; color: #0a0a0a; }
QMainWindow, QWidget#RootWidget { background: #f5f5f4; color: #0a0a0a; }
#Sidebar { background: #ffffff; border-right: 1px solid #e4e4e7; }
#Header {
  background: #050505;
  border-bottom: 1px solid #27272a;
  color: #fefce8;
}
QPushButton {
  background: transparent;
  color: #0a0a0a;
  border: 0;
  padding: 10px 16px;
  text-align: left;
  border-radius: 10px;
}
QPushButton:hover {
  background: rgba(250, 204, 21, 0.15);
  color: #0f172a;
}
QPushButton[active="true"] {
  background: #facc15;
  color: #0a0a0a;
  font-weight: 600;
}
QFrame#Card, QWidget#Card {
  background: #ffffff;
  border: 1px solid #e4e4e7;
  border-radius: 16px;
}
QLineEdit, QTextEdit, QPlainTextEdit {
  background: #ffffff;
  border: 1px solid #d4d4d8;
  border-radius: 12px;
  padding: 10px;
  color: #0a0a0a;
}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {
  border: 1px solid #facc15;
}
QProgressBar {
  background: #f4f4f5;
  border: 1px solid #d4d4d8;
  border-radius: 12px;
  text-align: center;
  color: #0f172a;
}
QProgressBar::chunk {
  background: QLinearGradient(x1:0, y1:0, x2:1, y2:0, stop:0 #facc15, stop:1 #f97316);
  border-radius: 12px;
}
QTableWidget {
  background: #ffffff;
  border: 1px solid #e4e4e7;
  border-radius: 16px;
  gridline-color: #f4f4f5;
}
QTableWidget::item { padding: 10px; }
QListWidget {
  background: #ffffff;
  border: 1px solid #e4e4e7;
  border-radius: 16px;
}
QTabWidget::pane {
  border: 1px solid #e4e4e7;
  border-radius: 16px;
  margin-top: 8px;
}
QTabBar::tab {
  background: #f5f5f4;
  border: 1px solid #e4e4e7;
  border-radius: 10px;
  padding: 8px 16px;
  color: #52525b;
  margin-right: 8px;
}
QTabBar::tab:selected {
  background: #0f172a;
  color: #fefce8;
  border-color: #0f172a;
}
"""
