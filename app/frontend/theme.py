AITJE_QSS = """
* { font-family: 'Inter', 'Helvetica Neue', Arial, sans-serif; color: #111111; }
QLabel {
  border: none;
  background: transparent;
}
QMainWindow, QWidget#RootWidget {
  background: #ffffff;
  color: #111111;
}
#CenterContainer, #ContentArea {
  background: #f5f5f5;
}
QScrollArea {
  background: #f5f5f5;
  border: none;
}
QScrollBar:vertical, QScrollBar:horizontal {
  background: transparent;
  border: none;
}
QScrollBar:vertical {
  width: 10px;
  margin: 12px 4px 12px 4px;
}
QScrollBar:horizontal {
  height: 10px;
  margin: 4px 12px 4px 12px;
}
QScrollBar::handle {
  background: #ffffff;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
}
QScrollBar::handle:vertical {
  min-height: 32px;
}
QScrollBar::handle:horizontal {
  min-width: 32px;
}
QScrollBar::add-line, QScrollBar::sub-line {
  border: none;
  background: transparent;
  width: 0;
  height: 0;
}
QScrollBar::add-page, QScrollBar::sub-page {
  background: transparent;
}
#Sidebar, #Sidebar QWidget {
  background: #ffffff;
}
#Sidebar {
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
QFrame#MapFrame {
  background: transparent;
  border: none;
  border-radius: 0;
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
QTabWidget#SettingsTabs::pane {
  border: none;
  background: transparent;
  margin-top: 12px;
}
QTabWidget#SettingsTabs::tab-bar {
  alignment: left;
  margin-left: 8px;
  margin-right: 8px;
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
QTabBar#SettingsTabsBar::tab {
  background: #f3f4f6;
  border: none;
  border-radius: 18px;
  padding: 10px 22px;
  margin: 0 6px;
  color: #6b7280;
  font-weight: 600;
}
QTabBar#SettingsTabsBar::tab:selected {
  background: #facc15;
  color: #050505;
}
QTabBar#SettingsTabsBar::tab:hover {
  background: #e5e7eb;
  color: #111111;
}
QFrame#UserBubble, QWidget#UserBubble {
  background: #111111;
  border: 1px solid #111111;
  border-radius: 20px;
}
QFrame#AssistantBubble, QWidget#AssistantBubble {
  background: #ffffff;
  border: 1px solid #e5e7eb;
  border-radius: 20px;
}
QLabel#AssistantAvatar {
  background: #f5d24a;
  color: #1c1917;
  border-radius: 50%;
  font-weight: 800;
  font-size: 14px;
}
QLabel#UserAvatar {
  background: #ffffff;
  color: #111111;
  border: 1px solid #e5e7eb;
  border-radius: 50%;
  font-weight: 700;
  font-size: 14px;
}
QPushButton#CopyButton {
  background: #f3f4f6;
  border: 1px solid #e5e7eb;
  border-radius: 14px;
  padding: 0 12px;
  color: #111111;
  font-size: 11px;
  font-weight: 600;
}
QPushButton#CopyButton:hover {
  background: #111111;
  color: #f5d24a;
}
QLabel#MapMeta {
  background: rgba(15, 23, 42, 0.92);
  color: #f8fafc;
  border-radius: 18px;
  padding: 10px 16px;
  font-size: 12px;
  line-height: 1.4em;
}
QFrame#MapControls {
  background: rgba(255, 255, 255, 0.95);
  border-radius: 26px;
  border: 1px solid #e5e7eb;
}
QPushButton#MapZoomButton {
  background: #ffffff;
  color: #050505;
  border-radius: 18px;
  border: 1px solid #e5e7eb;
  font-weight: 700;
  font-size: 18px;
  padding: 0;
  text-align: center;
}
QPushButton#MapZoomButton:hover {
  border-color: #facc15;
  color: #050505;
  background: #facc15;
}
QPushButton#MapPrimaryButton {
  background: #facc15;
  color: #111111;
  border-radius: 15px;
  border: none;
  font-weight: 700;
  padding: 8px 16px;
}
QPushButton#MapPrimaryButton:hover {
  background: #fbbf24;
}
QPushButton#MapPrimaryButton:disabled {
  background: #fde68a;
  color: #9ca3af;
}
QLabel#ContactPanelTitle {
  font-size: 18px;
  font-weight: 700;
}
QLabel#ContactPanelSubtitle {
  color: #6b7280;
  font-size: 13px;
}
QLabel#ContactEmptyState {
  background: #f8fafc;
  border-radius: 18px;
  padding: 12px 16px;
  color: #94a3b8;
  font-size: 12px;
}
QCheckBox#ContactSelectAll {
  font-weight: 600;
  color: #0f172a;
}
QCheckBox#ContactSelectAll::indicator {
  width: 18px;
  height: 18px;
  border-radius: 6px;
  border: 1px solid #cbd5f5;
  background: #ffffff;
}
QCheckBox#ContactSelectAll::indicator:checked {
  background: #facc15;
  border-color: #facc15;
}
QCheckBox#ContactSelectAll::indicator:indeterminate {
  background: #fde68a;
  border-color: #fbbf24;
}
QPushButton#ContactReloadButton {
  background: #ffffff;
  border-radius: 15px;
  border: 1px solid #e5eaf0;
  font-weight: 600;
  font-size: 13px;
  padding: 0 14px;
}
QPushButton#ContactReloadButton:hover {
  border-color: #facc15;
}
QPushButton#ContactSecondaryButton {
  background: #ffffff;
  border-radius: 18px;
  border: 1px solid #e2e8f0;
  padding: 10px 14px;
  font-weight: 600;
  font-size: 13px;
}
QPushButton#ContactSecondaryButton:hover {
  border-color: #facc15;
  color: #111111;
}
QPushButton#ContactSecondaryButton:disabled {
  color: #94a3b8;
  border-color: #f1f5f9;
}
QPushButton#ContactDangerButton {
  background: #fee2e2;
  color: #991b1b;
  border-radius: 18px;
  border: 1px solid #fecaca;
  padding: 10px 14px;
  font-weight: 600;
  font-size: 13px;
}
QPushButton#ContactDangerButton:hover {
  background: #fecaca;
  border-color: #f87171;
  color: #7f1d1d;
}
QPushButton#ContactDangerButton:disabled {
  color: #fca5a5;
  border-color: #ffe4e6;
}
QListWidget#ContactList {
  background: transparent;
  border: none;
  padding: 0;
}
QListWidget#ContactList::item {
  margin: 4px 0;
}
"""
