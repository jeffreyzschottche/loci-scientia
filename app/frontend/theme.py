DARK_QSS = """
* { font-family: Inter, Arial; }
QMainWindow, QWidget { background-color: #0b0f19; color: #ffffff; }
#Sidebar { background: #111827; border-right: 1px solid #1f2937; }
#Header { background: #111827; border-bottom: 1px solid #1f2937; }
QPushButton {
  background: transparent; color: #9ca3af; border: 0; padding: 8px 12px; text-align: left;
}
QPushButton:hover { background: rgba(255,255,255,0.06); color: #fff; }
QPushButton[active="true"] {
  background: #1f2937; color: #fff; border-left: 4px solid #2563eb; padding-left: 8px;
}
QFrame#Card {
  background: #111827; border: 1px solid #1f2937; border-radius: 12px;
}
QLineEdit, QTextEdit, QPlainTextEdit {
  background: #111827; border: 1px solid #374151; border-radius: 8px; padding: 6px;
}
QProgressBar {
  background: #111827; border: 1px solid #1f2937; border-radius: 8px; text-align: center;
}
QProgressBar::chunk { background: #2563eb; border-radius: 8px; }
QTableWidget {
  background: #0f172a; border: 1px solid #1f2937; border-radius: 12px; gridline-color: #1f2937;
}
QTableWidget::item { padding: 8px; }
QListWidget {
  background: #0f172a; border: 1px solid #1f2937; border-radius: 12px;
}
QTabWidget::pane {
  border: 1px solid #1f2937; border-radius: 12px; margin-top: 6px;
}
QTabBar::tab {
  background: #111827; border: 1px solid #1f2937; border-radius: 8px;
  padding: 6px 12px; color: #9ca3af; margin-right: 6px;
}
QTabBar::tab:selected {
  background: #2563eb; color: white; border-color: #2563eb;
}
"""
