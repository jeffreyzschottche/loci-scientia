from __future__ import annotations

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QWidget


class IosSwitch(QWidget):
    """iOS-style sliding toggle in the AITJE palette.

    Shared by the chat composer and the settings page so every on/off control
    looks the same. Emits ``toggled(bool)`` on state change; use
    ``blockSignals(True)`` around programmatic ``setChecked`` to set the visual
    state without triggering side effects.
    """

    toggled = Signal(bool)

    def __init__(self, checked: bool = False, parent=None, on_color: str = "#facc15"):
        super().__init__(parent)
        self._checked = checked
        self._on_color = on_color
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(52, 32)

    def isChecked(self) -> bool:
        return self._checked

    def setChecked(self, checked: bool) -> None:
        checked = bool(checked)
        if self._checked == checked:
            return
        self._checked = checked
        self.update()
        self.toggled.emit(self._checked)

    def sizeHint(self) -> QSize:
        return QSize(52, 32)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.setChecked(not self._checked)
            event.accept()
            return
        super().mousePressEvent(event)

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        track_rect = self.rect().adjusted(1, 1, -1, -1)
        track_color = QColor(self._on_color if self._checked else "#e5e7eb")
        border_color = QColor(self._on_color if self._checked else "#d1d5db")
        painter.setPen(border_color)
        painter.setBrush(track_color)
        painter.drawRoundedRect(track_rect, 16, 16)

        thumb_diameter = 26
        thumb_y = (self.height() - thumb_diameter) // 2
        thumb_x = self.width() - thumb_diameter - 3 if self._checked else 3
        painter.setPen(QColor(0, 0, 0, 20))
        painter.setBrush(QColor("#ffffff"))
        painter.drawEllipse(thumb_x, thumb_y, thumb_diameter, thumb_diameter)
