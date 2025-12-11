import asyncio
import json

import requests
from PySide6.QtCore import QObject, Signal, Slot
from PySide6.QtGui import QTextCursor
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
    queue_position = Signal(int)


class ChatPage(QWidget):
    def __init__(self, ws_client):
        super().__init__()
        self.ws_client = ws_client
        self.signals = ChatSignals()
        self.current_message = ""  # Buffer for accumulating tokens

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        self.history = QTextEdit()
        self.history.setReadOnly(True)
        self.history.setPlaceholderText("Welkom bij AITJE…")
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
        self.signals.queue_position.connect(self._on_queue_position)

    @Slot()
    def _on_send(self):
        text = self.input.text().strip()
        if not text:
            return
        self.history.append(f"<b>YOU:</b> {text}")
        self.input.clear()
        self.current_message = ""  # Reset message buffer
        asyncio.create_task(self._stream(text))

    async def _stream(self, prompt: str):
        try:
            await asyncio.to_thread(self._stream_sse, prompt)
            return
        except requests.HTTPError as exc:
            status = getattr(exc.response, "status_code", None)
            if status != 404:
                self.signals.token.emit(f"[fout] {exc}")
                self.signals.done.emit()
                return
            # 404 betekent dat streaming endpoint nog niet bestaat -> fallback
        except Exception as exc:
            self.signals.token.emit(f"[fout] {exc}")
            self.signals.done.emit()
            return

        try:
            message = await asyncio.to_thread(self._legacy_post, prompt)
        except Exception as exc:
            self.signals.token.emit(f"[fout] {exc}")
        else:
            self.signals.token.emit(message)
        self.signals.done.emit()

    def _stream_sse(self, prompt: str) -> None:
        """Stream SSE events van het backend (incl. wachtrij status)."""

        url = f"{API_BASE}/api/v1/ask/stream"
        with requests.post(
            url,
            json={"prompt": prompt, "max_new_tokens": 128},
            stream=True,
            timeout=60,
        ) as resp:
            resp.raise_for_status()

            for line in resp.iter_lines():
                if not line:
                    continue

                decoded = line.decode("utf-8")
                if not decoded.startswith("data: "):
                    continue
                event_data_str = decoded[6:]
                try:
                    event_data = json.loads(event_data_str)
                except json.JSONDecodeError:
                    continue

                if event_data.get("status") == "queued":
                    position = event_data.get("position", 0)
                    self.signals.queue_position.emit(position)
                    continue

                if "token" in event_data and not event_data.get("done"):
                    token = event_data.get("token") or ""
                    if token:
                        self.signals.token.emit(token)
                    continue

                if event_data.get("done"):
                    self.signals.done.emit()
                    return

        # Als de stream eindigt zonder done-event, sluit netjes af.
        self.signals.done.emit()

    def _legacy_post(self, prompt: str) -> str:
        """Fallback naar het niet-streamende endpoint."""

        endpoints = ["/api/v1/ask"]
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

    @Slot(int)
    def _on_queue_position(self, position: int):
        """Update UI with queue position."""
        if position > 0:
            # Update or append queue status
            if not self.current_message:
                self.history.append(f"<i>Queue position: {position}</i>")
                self.current_message = "queued"
            else:
                # Update the last line with new position
                cursor = self.history.textCursor()
                cursor.movePosition(QTextCursor.MoveOperation.End)
                cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
                cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock, QTextCursor.MoveMode.KeepAnchor)
                cursor.removeSelectedText()
                cursor.insertHtml(f"<i>Queue position: {position}</i>")
                self.history.setTextCursor(cursor)
        else:
            # Position 0 - clear queue message and start response
            if self.current_message == "queued":
                cursor = self.history.textCursor()
                cursor.movePosition(QTextCursor.MoveOperation.End)
                cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
                cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock, QTextCursor.MoveMode.KeepAnchor)
                cursor.removeSelectedText()
                cursor.deletePreviousChar()  # Remove the newline
                self.history.setTextCursor(cursor)
                self.current_message = ""

    @Slot(str)
    def _on_token(self, token: str):
        """Append token to the current message."""
        if not self.current_message and not token.startswith("[fout]"):
            # First token - add "AITJE:" prefix if not already there
            self.history.append(f"<b>AITJE:</b> {token}")
            self.current_message = token
        elif token.startswith("[fout]"):
            # Error message
            self.history.append(token)
            self.current_message = token
        else:
            # Append token to current message
            cursor = self.history.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.End)
            cursor.insertText(token)
            self.history.setTextCursor(cursor)
            self.current_message += token

    @Slot()
    def _on_done(self):
        """Finalize the current message."""
        self.history.append("")
        self.current_message = ""
