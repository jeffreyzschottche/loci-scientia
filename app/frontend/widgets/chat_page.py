import asyncio
import html
import json

import requests
from datetime import datetime
from PySide6.QtCore import QObject, Qt, QTimer, Signal, Slot
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ..config import BACKEND_HTTP

API_BASE = BACKEND_HTTP
MAX_BUBBLE_WIDTH = 680
ROW_GAP = 12
SIDE_PADDING = 28
ASSISTANT_AVATAR_SIZE = 32


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
        self.current_reply_label: QLabel | None = None
        self.queue_label: QLabel | None = None
        self.message_rows: list[QWidget] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        controls = QHBoxLayout()
        controls.setContentsMargins(0, 0, 0, 0)
        controls.addStretch(1)
        self.new_chat_btn = QPushButton("Start nieuwe chat")
        self.new_chat_btn.setCursor(Qt.PointingHandCursor)
        self.new_chat_btn.setStyleSheet(
            "QPushButton {"
            "  background: transparent;"
            "  border: 1px solid #d4d4d8;"
            "  border-radius: 20px;"
            "  padding: 6px 18px;"
            "  color: #4b5563;"
            "  font-weight:600;"
            "}"
            "QPushButton:hover { border-color:#111111; color:#111111; }"
        )
        self.new_chat_btn.clicked.connect(self._start_new_chat)
        controls.addWidget(self.new_chat_btn, 0, Qt.AlignRight)
        layout.addLayout(controls)
        self.new_chat_btn.setMinimumHeight(40)


        self.history_card = QFrame()
        self.history_card.setObjectName("ChatWrapper")
        self.history_card.setStyleSheet(
            "QFrame#ChatWrapper { background:#ffffff; border:1px solid #e4e4e7; border-radius:24px; }"
        )
        history_card_layout = QVBoxLayout(self.history_card)
        history_card_layout.setContentsMargins(16, 16, 16, 16)
        history_card_layout.setSpacing(0)

        self.history_scroll = QScrollArea()
        self.history_scroll.setWidgetResizable(True)
        self.history_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.history_scroll.setFrameShape(QFrame.NoFrame)
        self.history_scroll.setStyleSheet("QScrollArea { background:transparent; border:none; }")
        self.history_container = QWidget()
        self.history_container.setStyleSheet("background:transparent;")
        self.history_layout = QVBoxLayout(self.history_container)
        self.history_layout.setContentsMargins(SIDE_PADDING, 16, SIDE_PADDING, 16)
        self.history_layout.setSpacing(ROW_GAP)
        self.empty_label = QLabel("Welkom bij AITJE…")
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.setStyleSheet("color:#9ca3af; font-size:14px; background:transparent;")
        self.history_layout.addWidget(self.empty_label, 0, Qt.AlignCenter)
        self.history_layout.addStretch(1)
        self.history_scroll.setWidget(self.history_container)
        history_card_layout.addWidget(self.history_scroll)
        layout.addWidget(self.history_card)

        input_card = QFrame()
        input_card.setObjectName("Card")
        input_layout = QHBoxLayout(input_card)
        input_layout.setContentsMargins(12, 12, 12, 12)
        input_layout.setSpacing(8)

        self.input = QLineEdit()
        self.input.setPlaceholderText("Stel een vraag aan Aitje.")
        self.send_btn = QPushButton("Stuur")
        input_layout.addWidget(self.input, 1)
        input_layout.addWidget(self.send_btn)
        layout.addWidget(input_card)

        self.send_btn.clicked.connect(self._on_send)
        self.input.returnPressed.connect(self._on_send)
        self.signals.token.connect(self._on_token)
        self.signals.done.connect(self._on_done)
        self.signals.queue_position.connect(self._on_queue_position)
        self.send_btn.setStyleSheet(
            "QPushButton {"
            "  background: black;"
            "  border: 1px solid black;"
            "  border-radius: 20px;"
            "  padding: 6px 18px;"
            "  color: white;"
            "  font-weight:600;"
            "}"
            "QPushButton:hover { color:#facc15; }"
        )
        self.send_btn.setMinimumHeight(40)


    def _start_new_chat(self):
        """Reset the conversation history."""
        self._clear_history()
        self.current_message = ""
        self.current_reply_label = None
        self.queue_label = None

    @Slot()
    def _on_send(self):
        text = self.input.text().strip()
        if not text:
            return
        self._append_message("user", text)
        self.input.clear()
        self.current_message = ""  # Reset message buffer
        self.current_reply_label = None
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

    @Slot(str)
    def _on_token(self, token: str):
        """Append token to the current message."""
        if token.startswith("[fout]"):
            self.current_reply_label = self._append_message("assistant", token)
            self.current_message = token
            return

        if self.queue_label:
            container = self.queue_label.parentWidget()
            self.history_layout.removeWidget(container)
            container.deleteLater()
            self.queue_label = None

        if self.current_reply_label is None:
            self.current_reply_label = self._append_message("assistant", token)
            self.current_message = token
        else:
            self.current_message += token
            self._set_label_text(self.current_reply_label, self.current_message)

    @Slot()
    def _on_done(self):
        """Finalize the current message."""
        self.current_message = ""
        self.current_reply_label = None

    @Slot(int)
    def _on_queue_position(self, position: int):
        """Update UI with queue position."""
        if position > 0:
            if not self.queue_label:
                self.queue_label = self._append_system_message(
                    f"In wachtrij... positie {position}"
                )
            else:
                self.queue_label.setText(f"In wachtrij... positie {position}")
        elif self.queue_label:
            container = self.queue_label.parentWidget()
            self.history_layout.removeWidget(container)
            container.deleteLater()
            self.queue_label = None

    def _append_system_message(self, text: str) -> QLabel:
        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(0)
        label = QLabel(text)
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("color:#9ca3af; font-style:italic;")
        row_layout.addWidget(label)
        self._insert_history_row(row)
        self._scroll_to_bottom()
        return label

    def _append_message(self, role: str, text: str) -> QLabel:
        if self.empty_label:
            self.empty_label.hide()

        row_outer = QWidget()
        row_outer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        row_outer_layout = QHBoxLayout(row_outer)
        row_outer_layout.setContentsMargins(0, 4, 0, 4)
        row_outer_layout.setSpacing(0)

        row_inner = QWidget()
        row_inner.setMaximumWidth(MAX_BUBBLE_WIDTH)
        row_inner.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        inner_layout = QHBoxLayout(row_inner)
        inner_layout.setContentsMargins(0, 0, 0, 0)
        inner_layout.setSpacing(12)

        bubble = QFrame()
        bubble.setObjectName("UserBubble" if role == "user" else "AssistantBubble")
        if role == "user":
            bubble.setStyleSheet("background:#111111; border:1px solid #111111; border-radius:20px;")
        bubble.setMaximumWidth(int(MAX_BUBBLE_WIDTH * (0.82 if role == "user" else 0.9)))
        bubble.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        bubble_layout = QVBoxLayout(bubble)
        bubble_layout.setContentsMargins(18, 14, 18, 14)
        bubble_layout.setSpacing(8)

        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(8)
        role_chip = QLabel("IK" if role == "user" else "AITJE")
        role_chip.setStyleSheet(
            "font-size:11px; font-weight:600; letter-spacing:0.08em; color:#a1a1aa;"
        )
        top_row.addWidget(role_chip, 0, Qt.AlignLeft)
        top_row.addStretch(1)

        label = QLabel()
        label.setWordWrap(True)
        text_color = "#ffffff" if role == "user" else "#111111"
        label.setStyleSheet(f"border:none; background:transparent; color:{text_color};")
        label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self._set_label_text(label, text)

        timestamp_label = QLabel(datetime.now().strftime("%H:%M"))
        timestamp_label.setStyleSheet(
            f"font-size:11px; color:{text_color if role == 'user' else '#6b7280'};"
        )

        if role == "assistant":
            copy_btn = QPushButton("Kopieer")
            copy_btn.setObjectName("CopyButton")
            copy_btn.setCursor(Qt.PointingHandCursor)
            copy_btn.setFixedHeight(26)
            copy_btn.clicked.connect(lambda _, lbl=label: self._copy_label_text(lbl))
            top_row.addWidget(copy_btn, 0, Qt.AlignRight)

        bubble_layout.addLayout(top_row)
        bubble_layout.addWidget(label)
        bubble_layout.addWidget(
            timestamp_label, 0, Qt.AlignRight if role == "user" else Qt.AlignLeft
        )

        if role == "user":
            user_avatar = QLabel("👤")
            user_avatar.setObjectName("UserAvatar")
            user_avatar.setAlignment(Qt.AlignCenter)
            user_avatar.setFixedSize(ASSISTANT_AVATAR_SIZE, ASSISTANT_AVATAR_SIZE)
            inner_layout.addStretch(1)
            inner_layout.addWidget(bubble, 0, Qt.AlignRight)
            inner_layout.addWidget(user_avatar, 0, Qt.AlignBottom)
            row_outer_layout.addStretch(1)
            row_outer_layout.addWidget(row_inner, 0, Qt.AlignRight)
            row_outer_layout.addStretch(0)
        else:
            inner_layout.addWidget(self._build_assistant_avatar(), 0, Qt.AlignTop)
            inner_layout.addWidget(bubble, 0, Qt.AlignLeft)
            inner_layout.addStretch(1)
            row_outer_layout.addStretch(0)
            row_outer_layout.addWidget(row_inner, 0, Qt.AlignLeft)
            row_outer_layout.addStretch(1)

        self._insert_history_row(row_outer)
        self.message_rows.append(row_outer)
        self._scroll_to_bottom()
        return label

    def _build_assistant_avatar(self) -> QLabel:
        avatar = QLabel("🤖")
        avatar.setObjectName("AssistantAvatar")
        avatar.setAlignment(Qt.AlignCenter)
        avatar.setFixedSize(ASSISTANT_AVATAR_SIZE, ASSISTANT_AVATAR_SIZE)
        return avatar

    def _copy_text(self, text: str):
        clipboard = QApplication.clipboard()
        clipboard.setText(text)

    def _copy_label_text(self, label: QLabel):
        text = label.property("_plain_text") or label.text()
        if isinstance(text, str):
            self._copy_text(text)

    def _set_label_text(self, label: QLabel, text: str):
        safe = html.escape(text).replace("\n", "<br>")
        label.setText(safe)
        label.setProperty("_plain_text", text)

    def _insert_history_row(self, row: QWidget):
        index = max(0, self.history_layout.count() - 1)
        self.history_layout.insertWidget(index, row)

    def _clear_history(self):
        for row in self.message_rows:
            self.history_layout.removeWidget(row)
            row.deleteLater()
        self.message_rows.clear()
        if self.queue_label:
            container = self.queue_label.parentWidget()
            if container:
                self.history_layout.removeWidget(container)
                container.deleteLater()
        self.queue_label = None
        if self.empty_label:
            self.empty_label.show()

    def _scroll_to_bottom(self):
        def _do_scroll():
            bar = self.history_scroll.verticalScrollBar()
            bar.setValue(bar.maximum())

        QTimer.singleShot(0, _do_scroll)
