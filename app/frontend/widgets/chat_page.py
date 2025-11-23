import asyncio

import requests
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

from ..config import BACKEND_HTTP

API_BASE = BACKEND_HTTP


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
        self.input.returnPressed.connect(self._on_send)
        self.signals.token.connect(self._on_token)
        self.signals.done.connect(self._on_done)

    @Slot()
    def _on_send(self):
        text = self.input.text().strip()
        if not text:
            return
        self.history.append(f"<b>YOU:</b> {text}")
        self.input.clear()
        asyncio.create_task(self._stream(text))

    async def _stream(self, prompt: str):
        endpoints = ["/api/v1/ask"]

        def _post():
            last_error: Exception | None = None
            for suffix in endpoints:
                url = f"{API_BASE}{suffix}"
                try:
                    resp = requests.post(
                        url,
                        json={"prompt": prompt},
                        timeout=5,
                    )
                except Exception as exc:  # pragma: no cover - UI feedback only
                    last_error = exc
                    continue
                if resp.status_code == 404 and suffix != endpoints[-1]:
                    # probeer legacy endpoint als /api/v1/ask nog niet bestaat
                    continue
                try:
                    resp.raise_for_status()
                except Exception as exc:  # pragma: no cover - UI feedback only
                    last_error = exc
                    continue
                try:
                    data = resp.json()
                except ValueError:
                    return resp.text.strip() or "<leeg antwoord>"
                if isinstance(data, dict):
                    return data.get("message") or data.get("text") or str(data)
                return str(data)
            raise last_error or RuntimeError("Geen geldig antwoord van backend")

        try:
            message = await asyncio.to_thread(_post)
        except Exception as exc:
            message = f"[fout] {exc}"
        self.signals.token.emit(message)
        self.signals.done.emit()

    @Slot(str)
    def _on_token(self, token: str):
        self.history.append(f"<b>Loci:</b> {token}")

    @Slot()
    def _on_done(self):
        self.history.append("")
