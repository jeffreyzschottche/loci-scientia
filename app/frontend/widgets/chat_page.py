import asyncio

from PySide6.QtCore import QObject, Signal, Slot
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class ChatSignals(QObject):
    token = Signal(str)
    done = Signal()


class ChatPage(QWidget):
    def __init__(self, ws_client):
        super().__init__()
        self.ws_client = ws_client
        self.signals = ChatSignals()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        self.history = QTextEdit()
        self.history.setReadOnly(True)
        self.history.setPlaceholderText("Welkom bij Loci Scientia…")
        layout.addWidget(self.history)

        input_card = QFrame()
        input_card.setObjectName("Card")
        input_layout = QHBoxLayout(input_card)
        input_layout.setContentsMargins(12, 12, 12, 12)
        input_layout.setSpacing(8)

        self.input = QLineEdit()
        self.input.setPlaceholderText("Stel een vraag aan de assistent…")
        self.send_btn = QPushButton("Send")
        input_layout.addWidget(self.input, 1)
        input_layout.addWidget(self.send_btn)
        layout.addWidget(input_card)

        self.send_btn.clicked.connect(self._on_send)
        self.signals.token.connect(self._on_token)
        self.signals.done.connect(self._on_done)

    @Slot()
    def _on_send(self):
        text = self.input.text().strip()
        if not text:
            return
        self.history.append(f"<b>YOU:</b> {text}")
        self.history.append("<b>AI:</b> ")
        self.input.clear()
        asyncio.create_task(self._stream(text))

    async def _stream(self, prompt: str):
        async for token in self.ws_client.stream_echo(prompt):
            self.signals.token.emit(token)
        self.signals.done.emit()

    @Slot(str)
    def _on_token(self, token: str):
        cursor = self.history.textCursor()
        cursor.movePosition(cursor.End)
        self.history.setTextCursor(cursor)
        self.history.insertPlainText(token)

    @Slot()
    def _on_done(self):
        self.history.append("")
