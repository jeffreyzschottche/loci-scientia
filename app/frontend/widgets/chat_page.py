from __future__ import annotations

import asyncio
import html
import json
import os
import uuid

import requests
from datetime import datetime
from PySide6.QtCore import QObject, QSize, Qt, QTimer, Signal, Slot
from PySide6.QtGui import QColor, QFontMetrics, QPainter, QTextDocument, QTextOption
from PySide6.QtPrintSupport import QPrintDialog, QPrinter
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTextBrowser,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ..config import BACKEND_BEARER_TOKEN, BACKEND_HTTP, PROMPT_MODES
from ..translations import t, register_language_change_callback

API_BASE = BACKEND_HTTP
MAX_BUBBLE_WIDTH = 680
ROW_GAP = 12
SIDE_PADDING = 12
ASSISTANT_AVATAR_SIZE = 32
ASSISTANT_MAX_WIDTH = 900
ASSISTANT_MIN_WIDTH = 640
class ChatSignals(QObject):
    response_token = Signal(int, str)
    thinking_token = Signal(int, str)
    final_payload = Signal(int, str, str)
    done = Signal(int)
    queue_position = Signal(int, int)


class IosSwitch(QWidget):
    toggled = Signal(bool)

    def __init__(self, checked: bool = False, parent=None):
        super().__init__(parent)
        self._checked = checked
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
        track_color = QColor("#facc15" if self._checked else "#e5e7eb")
        border_color = QColor("#facc15" if self._checked else "#d1d5db")
        painter.setPen(border_color)
        painter.setBrush(track_color)
        painter.drawRoundedRect(track_rect, 16, 16)

        thumb_diameter = 26
        thumb_y = (self.height() - thumb_diameter) // 2
        thumb_x = self.width() - thumb_diameter - 3 if self._checked else 3
        painter.setPen(QColor(0, 0, 0, 20))
        painter.setBrush(QColor("#ffffff"))
        painter.drawEllipse(thumb_x, thumb_y, thumb_diameter, thumb_diameter)


class TypingDotsWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._active_index = 0
        self._timer = QTimer(self)
        self._timer.setInterval(180)
        self._timer.timeout.connect(self._advance)
        self.setFixedSize(44, 12)

    def start(self) -> None:
        self._active_index = 0
        self._timer.start()
        self.update()

    def stop(self) -> None:
        if self._timer.isActive():
            self._timer.stop()
        self.update()

    def _advance(self) -> None:
        self._active_index = (self._active_index + 1) % 3
        self.update()

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        base_color = QColor("#d1d5db")
        active_color = QColor("#111111")
        diameter = 8
        spacing = 6
        y = (self.height() - diameter) // 2
        for idx in range(3):
            x = idx * (diameter + spacing)
            painter.setPen(Qt.NoPen)
            painter.setBrush(active_color if idx == self._active_index else base_color)
            painter.drawEllipse(x, y, diameter, diameter)


class AutoSizingMarkdownView(QTextBrowser):
    def __init__(self):
        super().__init__()
        self._plain_text = ""
        self._syncing_height = False
        self.setReadOnly(True)
        self.setOpenExternalLinks(True)
        self.setFrameShape(QFrame.NoFrame)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setLineWrapMode(QTextBrowser.WidgetWidth)
        self.setStyleSheet("background:transparent; border:none;")
        self.document().setDocumentMargin(0)
        option = self.document().defaultTextOption()
        option.setWrapMode(QTextOption.WrapAtWordBoundaryOrAnywhere)
        self.document().setDefaultTextOption(option)
        self.document().setDefaultStyleSheet(
            """
            body { color:#111827; font-size:14px; line-height:1.55; overflow-wrap:anywhere; word-break:break-word; }
            p { margin:0 0 10px 0; overflow-wrap:anywhere; word-break:break-word; }
            h1, h2, h3, h4 { margin:14px 0 8px 0; color:#111111; font-weight:700; }
            ul, ol { margin:0 0 10px 20px; }
            li { margin:0 0 4px 0; overflow-wrap:anywhere; word-break:break-word; }
            a { color:#0f766e; text-decoration:none; }
            blockquote {
                margin:10px 0;
                padding:8px 12px;
                border-left:4px solid #f59e0b;
                background:#fffbeb;
                color:#44403c;
                overflow-wrap:anywhere;
                word-break:break-word;
            }
            code {
                font-family:"SFMono-Regular","Cascadia Mono","DejaVu Sans Mono",monospace;
                background:#f3f4f6;
                padding:2px 5px;
                border-radius:6px;
                overflow-wrap:anywhere;
                word-break:break-word;
            }
            pre {
                margin:10px 0;
                padding:12px 14px;
                background:#111827;
                color:#f9fafb;
                border-radius:12px;
                white-space:pre-wrap;
                word-wrap:break-word;
                overflow-wrap:anywhere;
                word-break:break-word;
            }
            pre code {
                background:transparent;
                padding:0;
            }
            """
        )
        layout = self.document().documentLayout()
        if layout is not None:
            layout.documentSizeChanged.connect(self._queue_sync_height)

    def set_markdown_text(self, text: str, placeholder: str = "") -> None:
        self._plain_text = text or ""
        if self._plain_text.strip():
            self.setMarkdown(self._plain_text)
        elif placeholder:
            self.setHtml(f"<p>{html.escape(placeholder)}</p>")
        else:
            self.setHtml("")
        self._queue_sync_height()

    def plain_text(self) -> str:
        return self._plain_text

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._queue_sync_height()

    def _queue_sync_height(self, *_args) -> None:
        if self._syncing_height:
            return
        QTimer.singleShot(0, self._sync_height)

    def _sync_height(self) -> None:
        if self._syncing_height:
            return
        self._syncing_height = True
        try:
            width = max(0, self.viewport().width() - 4)
            if abs(self.document().textWidth() - width) > 1:
                self.document().setTextWidth(width)
            self.document().adjustSize()
            height = int(self.document().size().height()) + 8
            self.setFixedHeight(max(28, height))
            self.updateGeometry()
            parent = self.parentWidget()
            if parent is not None:
                parent.updateGeometry()
                parent.adjustSize()
        finally:
            self._syncing_height = False


class AssistantMessageWidget(QWidget):
    thinking_toggled = Signal(bool)

    def __init__(self):
        super().__init__()
        self._response_text = ""
        self._thinking_text = ""
        self._thinking_initialized = False
        self._showing_typing = False
        self._feedback_mode = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        self.setMinimumWidth(ASSISTANT_MIN_WIDTH)

        self.thinking_card = QFrame()
        self.thinking_card.setStyleSheet(
            "QFrame {"
            "  background:#fff8db;"
            "  border:1px solid #f4d76a;"
            "  border-radius:16px;"
            "}"
        )
        thinking_layout = QVBoxLayout(self.thinking_card)
        thinking_layout.setContentsMargins(12, 10, 12, 12)
        thinking_layout.setSpacing(8)

        self.thinking_toggle = QToolButton()
        self.thinking_toggle.setCheckable(True)
        self.thinking_toggle.setChecked(True)
        self.thinking_toggle.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.thinking_toggle.setStyleSheet(
            "QToolButton {"
            "  border:none;"
            "  color:#8a6700;"
            "  font-size:12px;"
            "  font-weight:700;"
            "  text-align:left;"
            "}"
        )
        self.thinking_toggle.clicked.connect(self._toggle_thinking)
        thinking_layout.addWidget(self.thinking_toggle, 0, Qt.AlignLeft)

        self.thinking_view = QLabel()
        self.thinking_view.setWordWrap(True)
        self.thinking_view.setTextFormat(Qt.PlainText)
        self.thinking_view.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.thinking_view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        self.thinking_view.setStyleSheet(
            "background:transparent; border:none; color:#5f4a00; line-height:1.5;"
        )
        thinking_layout.addWidget(self.thinking_view)
        layout.addWidget(self.thinking_card)

        self.response_view = AutoSizingMarkdownView()
        self.response_view.setStyleSheet("background:transparent; border:none; color:#111827;")
        layout.addWidget(self.response_view)

        self.feedback_label = QLabel()
        self.feedback_label.setWordWrap(True)
        self.feedback_label.setTextInteractionFlags(Qt.NoTextInteraction)
        self.feedback_label.setStyleSheet(
            "background:transparent; border:none; color:#6b7280; font-style:italic;"
        )
        self.feedback_label.hide()
        layout.addWidget(self.feedback_label)

        self.typing_dots = TypingDotsWidget()
        layout.addWidget(self.typing_dots, 0, Qt.AlignLeft)
        self.typing_dots.hide()

        self.set_thinking_text("")
        self.set_response_text("")

    def set_response_text(self, text: str) -> None:
        self._response_text = text or ""
        self.typing_dots.hide()
        self.typing_dots.stop()
        self._showing_typing = False
        self._feedback_mode = False
        self.feedback_label.hide()
        self.response_view.show()
        self.response_view.set_markdown_text(self._response_text)

    def show_typing_indicator(self) -> None:
        self._response_text = ""
        self._feedback_mode = False
        self.feedback_label.hide()
        self.response_view.hide()
        self.response_view.set_markdown_text("")
        self.typing_dots.show()
        self.typing_dots.start()
        self._showing_typing = True

    def show_feedback_message(self, text: str) -> None:
        self._response_text = text or ""
        self._feedback_mode = True
        self.typing_dots.hide()
        self.typing_dots.stop()
        self._showing_typing = False
        self.response_view.hide()
        self.feedback_label.setText(text)
        self.feedback_label.show()

    def set_thinking_text(self, text: str) -> None:
        self._thinking_text = text or ""
        has_thinking = bool(self._thinking_text.strip())
        if has_thinking and self._showing_typing:
            self.typing_dots.hide()
            self.typing_dots.stop()
            self._showing_typing = False
        self.thinking_card.setVisible(has_thinking)
        self.thinking_toggle.setText(t("chat_thinking_block"))
        if has_thinking:
            self.thinking_view.setText(self._thinking_text)
            if not self._thinking_initialized:
                self._thinking_initialized = True
                self.set_thinking_expanded(False)
            else:
                self._update_thinking_arrow()
        else:
            self.thinking_view.setText("")
            self._update_thinking_arrow()

    def response_text(self) -> str:
        return self._response_text

    def thinking_text(self) -> str:
        return self._thinking_text

    def has_thinking(self) -> bool:
        return bool(self._thinking_text.strip())

    def is_thinking_expanded(self) -> bool:
        return self.thinking_toggle.isChecked()

    def set_thinking_expanded(self, expanded: bool) -> None:
        self.thinking_toggle.setChecked(expanded)
        self._update_thinking_arrow()
        self.thinking_toggled.emit(expanded)

    def _toggle_thinking(self) -> None:
        self.set_thinking_expanded(self.thinking_toggle.isChecked())

    def _update_thinking_arrow(self) -> None:
        self.thinking_toggle.setArrowType(
            Qt.DownArrow if self.thinking_toggle.isChecked() else Qt.RightArrow
        )
        self.thinking_view.setVisible(self.thinking_toggle.isChecked())


class ChatPage(QWidget):
    def __init__(self, ws_client):
        super().__init__()
        self.ws_client = ws_client
        self.signals = ChatSignals()
        self.current_response_text = ""
        self.current_thinking_text = ""
        self.current_reply_widget: AssistantMessageWidget | None = None
        self.queue_label: QLabel | None = None
        self.message_rows: list[QWidget] = []
        self._bearer_token = BACKEND_BEARER_TOKEN or ""
        self._auto_token_error: str | None = None
        self.available_modes = PROMPT_MODES or ["Developer", "Finance", "Law", "Child"]
        self.selected_mode = self._load_focus_mode()
        self.thinking_enabled = True
        self._is_generating = False
        self._stop_requested = False
        self._request_seq = 0
        self._active_request_id: int | None = None
        self._conversation_id = uuid.uuid4().hex
        self._chat_epoch = 0

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        controls = QHBoxLayout()
        controls.setContentsMargins(0, 0, 0, 0)
        controls.setSpacing(10)
        self.thinking_toggle_wrap = QWidget()
        thinking_wrap_layout = QHBoxLayout(self.thinking_toggle_wrap)
        thinking_wrap_layout.setContentsMargins(0, 0, 0, 0)
        thinking_wrap_layout.setSpacing(10)

        self.thinking_label = QLabel()
        self.thinking_label.setStyleSheet("color:#111111; font-weight:700;")
        thinking_wrap_layout.addWidget(self.thinking_label, 0, Qt.AlignVCenter)

        self.thinking_btn = IosSwitch(self.thinking_enabled)
        self.thinking_btn.toggled.connect(self._toggle_thinking)
        thinking_wrap_layout.addWidget(self.thinking_btn, 0, Qt.AlignVCenter)
        controls.addWidget(self.thinking_toggle_wrap, 0, Qt.AlignLeft)
        controls.addStretch(1)
        self.new_chat_btn = QPushButton(t("chat_start_new"))
        self.new_chat_btn.setCursor(Qt.PointingHandCursor)
        self.new_chat_btn.setStyleSheet(
            "QPushButton {"
            "  background:#ffffff;"
            "  border:1px solid #e5e7eb;"
            "  border-radius:20px;"
            "  padding:8px 18px;"
            "  color:#111111;"
            "  font-weight:600;"
            "  text-align:center;"
            "}"
            "QPushButton:hover { background:#f9fafb; border-color:#d1d5db; }"
        )
        self.new_chat_btn.clicked.connect(self._start_new_chat)
        controls.addWidget(self.new_chat_btn, 0, Qt.AlignRight)
        layout.addLayout(controls)
        self.new_chat_btn.setMinimumHeight(40)
        self._sync_thinking_button()

        self.history_card = QFrame()
        self.history_card.setObjectName("ChatWrapper")
        self.history_card.setStyleSheet(
            "QFrame#ChatWrapper {"
            "  background:#ffffff;"
            "  border:1px solid #ececec;"
            "  border-radius:34px;"
            "}"
        )
        history_card_layout = QVBoxLayout(self.history_card)
        history_card_layout.setContentsMargins(22, 22, 22, 22)
        history_card_layout.setSpacing(0)

        self.history_scroll = QScrollArea()
        self.history_scroll.setWidgetResizable(True)
        self.history_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.history_scroll.setFrameShape(QFrame.NoFrame)
        self.history_scroll.setStyleSheet("QScrollArea { background:transparent; border:none; }")
        self.history_container: QWidget | None = None
        self.history_layout: QVBoxLayout | None = None
        self.empty_state: QWidget | None = None
        self.empty_label: QLabel | None = None
        self._rebuild_history_view()
        history_card_layout.addWidget(self.history_scroll)
        layout.addWidget(self.history_card)

        input_card = QFrame()
        input_card.setObjectName("Card")
        input_card.setStyleSheet(
            "QFrame#Card {"
            "  background:#ffffff;"
            "  border:1px solid #ececec;"
            "  border-radius:30px;"
            "}"
        )
        input_layout = QHBoxLayout(input_card)
        input_layout.setContentsMargins(14, 14, 14, 14)
        input_layout.setSpacing(10)

        self.input = QLineEdit()
        self.input.setPlaceholderText(t("chat_placeholder"))
        self.send_btn = QPushButton(t("chat_send"))
        input_layout.addWidget(self.input, 1)
        input_layout.addWidget(self.send_btn)
        layout.addWidget(input_card)

        self.send_btn.clicked.connect(self._handle_send_button)
        self.input.returnPressed.connect(self._handle_send_button)
        self.signals.response_token.connect(self._on_response_token)
        self.signals.thinking_token.connect(self._on_thinking_token)
        self.signals.final_payload.connect(self._on_final_payload)
        self.signals.done.connect(self._on_done)
        self.signals.queue_position.connect(self._on_queue_position)

        register_language_change_callback(self._update_translations)
        self.send_btn.setStyleSheet(
            "QPushButton {"
            "  background:#111111;"
            "  border:1px solid #111111;"
            "  border-radius:20px;"
            "  padding:8px 18px;"
            "  color:#ffffff;"
            "  font-weight:700;"
            "  text-align:center;"
            "}"
            "QPushButton:hover { background:#1f1f1f; color:#facc15; }"
        )
        self.send_btn.setMinimumWidth(96)
        self.send_btn.setMinimumHeight(40)
        self._sync_send_button()


    def _update_translations(self) -> None:
        """Update UI elements when language changes."""
        self.new_chat_btn.setText(t("chat_start_new"))
        self._sync_thinking_button()
        self.input.setPlaceholderText(t("chat_placeholder"))
        self._sync_send_button()
        if self.empty_label:
            self.empty_label.setText(t("chat_welcome"))

    def _load_focus_mode(self) -> str | None:
        value = os.environ.get("AITJE_DEFAULT_PROMPT_MODE", "").strip()
        if not value:
            return None
        for mode in self.available_modes:
            if mode.lower() == value.lower():
                return mode
        return None

    def _toggle_thinking(self, checked: bool) -> None:
        self.thinking_enabled = checked
        self._sync_thinking_button()

    def _sync_thinking_button(self) -> None:
        if self.thinking_btn.isChecked() != self.thinking_enabled:
            self.thinking_btn.setChecked(self.thinking_enabled)
        enabled_label = t("chat_thinking_enabled")
        disabled_label = t("chat_thinking_disabled")
        metrics = QFontMetrics(self.thinking_label.font())
        self.thinking_label.setFixedWidth(
            max(metrics.horizontalAdvance(enabled_label), metrics.horizontalAdvance(disabled_label)) + 4
        )
        self.thinking_label.setText(
            enabled_label if self.thinking_enabled else disabled_label
        )

    def _start_new_chat(self):
        """Reset the conversation history."""
        self._chat_epoch += 1
        self._stop_generation(show_feedback=False)
        self._remove_current_reply_widget()
        self._clear_history()
        self.current_response_text = ""
        self.current_thinking_text = ""
        self.current_reply_widget = None
        self.queue_label = None
        self._stop_requested = False
        self._is_generating = False
        self._active_request_id = None
        self._conversation_id = uuid.uuid4().hex
        self.input.clear()
        self.input.setPlaceholderText(t("chat_placeholder"))
        self._restore_empty_state()
        self._sync_send_button()

    @Slot()
    def _handle_send_button(self):
        if self._is_generating:
            self._stop_generation()
            return
        self._on_send()

    @Slot()
    def _on_send(self):
        text = self.input.text().strip()
        if not text:
            return
        self.selected_mode = self._load_focus_mode()
        self._stop_requested = False
        self._is_generating = True
        self._request_seq += 1
        request_id = self._request_seq
        self._active_request_id = request_id
        self._sync_send_button()
        self.input.setPlaceholderText(t("chat_placeholder"))
        self._append_message("user", text)
        self.input.clear()
        self.current_response_text = ""
        self.current_thinking_text = ""
        self.current_reply_widget = None
        self.input.setPlaceholderText(t("chat_placeholder"))
        self._show_typing_indicator()
        asyncio.create_task(self._stream(text, self.selected_mode, request_id, self._chat_epoch))

    def _request_payload(self, prompt: str, mode: str | None = None) -> dict:
        payload = {
            "prompt": prompt,
            "request_id": str(self._active_request_id or ""),
            "conversation_id": self._conversation_id,
            "thinking": self.thinking_enabled,
            "max_new_tokens": 128,
        }
        if mode:
            payload["mode"] = mode
        return payload

    async def _stream(
        self,
        prompt: str,
        mode: str | None,
        request_id: int,
        chat_epoch: int,
    ):
        try:
            await asyncio.to_thread(self._stream_sse, prompt, mode, request_id, chat_epoch)
            return
        except requests.HTTPError as exc:
            if chat_epoch != self._chat_epoch:
                return
            status = getattr(exc.response, "status_code", None)
            if status == 401:
                # Probeer automatisch een token op te halen voor de lokale admin.
                if self._refresh_auto_token():
                    await asyncio.to_thread(self._stream_sse, prompt, mode, request_id, chat_epoch)
                    return
                message = (
                    self._auto_token_error
                    or f"{t('chat_error_prefix')} {t('chat_error_401')}"
                )
                self.signals.response_token.emit(request_id, message)
                self.signals.done.emit(request_id)
                return
            if status != 404:
                self.signals.response_token.emit(request_id, f"{t('chat_error_prefix')} {exc}")
                self.signals.done.emit(request_id)
                return
            # 404 betekent dat streaming endpoint nog niet bestaat -> fallback
        except Exception as exc:
            if chat_epoch != self._chat_epoch:
                return
            self.signals.response_token.emit(request_id, f"{t('chat_error_prefix')} {exc}")
            self.signals.done.emit(request_id)
            return

        try:
            if chat_epoch != self._chat_epoch:
                return
            payload = await asyncio.to_thread(self._legacy_post, prompt, mode)
        except Exception as exc:
            if chat_epoch != self._chat_epoch:
                return
            self.signals.response_token.emit(request_id, f"{t('chat_error_prefix')} {exc}")
        else:
            if chat_epoch != self._chat_epoch:
                return
            self.signals.final_payload.emit(
                request_id,
                payload.get("thinking", ""),
                payload.get("message", ""),
            )
        self.signals.done.emit(request_id)

    def _stream_sse(
        self,
        prompt: str,
        mode: str | None = None,
        request_id: int = 0,
        chat_epoch: int = 0,
    ) -> None:
        """Stream SSE events van het backend (incl. wachtrij status)."""

        url = f"{API_BASE}/api/v1/ask/stream"
        payload = self._request_payload(prompt, mode)
        with requests.post(
            url,
            json=payload,
            stream=True,
            timeout=60,
            headers=self._auth_headers(),
        ) as resp:
            if resp.status_code >= 400:
                if resp.status_code in (401, 404):
                    resp.raise_for_status()
                detail = self._format_api_error_response(resp)
                raise RuntimeError(detail)

            for line in resp.iter_lines():
                if chat_epoch != self._chat_epoch:
                    return
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
                    self.signals.queue_position.emit(request_id, position)
                    continue

                if "thinking" in event_data and not event_data.get("done"):
                    token = event_data.get("thinking") or ""
                    if token:
                        self.signals.thinking_token.emit(request_id, token)
                    continue

                if "token" in event_data and not event_data.get("done"):
                    token = event_data.get("token") or ""
                    if token:
                        self.signals.response_token.emit(request_id, token)
                    continue

                if event_data.get("done"):
                    self.signals.final_payload.emit(
                        request_id,
                        event_data.get("thinking", "") or "",
                        event_data.get("message", "") or "",
                    )
                    self.signals.done.emit(request_id)
                    return

        # Als de stream eindigt zonder done-event, sluit netjes af.
        self.signals.done.emit(request_id)

    def _legacy_post(self, prompt: str, mode: str | None = None) -> dict[str, str]:
        """Fallback naar het niet-streamende endpoint."""

        endpoints = ["/api/v1/ask"]
        headers = self._auth_headers()
        last_error: Exception | None = None
        for suffix in endpoints:
            url = f"{API_BASE}{suffix}"
            try:
                resp = requests.post(
                    url,
                    json=self._request_payload(prompt, mode),
                    timeout=5,
                    headers=headers,
                )
            except Exception as exc:  # pragma: no cover - UI feedback only
                last_error = exc
                continue
            if resp.status_code == 404 and suffix != endpoints[-1]:
                continue
            try:
                resp.raise_for_status()
            except Exception:  # pragma: no cover - UI feedback only
                if resp.status_code == 401:
                    last_error = RuntimeError(t("chat_error_401"))
                else:
                    last_error = RuntimeError(self._format_api_error_response(resp))
                continue
            try:
                data = resp.json()
            except ValueError:
                return {"message": resp.text.strip() or t("chat_empty_response"), "thinking": ""}
            if isinstance(data, dict):
                return {
                    "message": data.get("message") or data.get("text") or str(data),
                    "thinking": data.get("thinking") or "",
                }
            return {"message": str(data), "thinking": ""}
        raise last_error or RuntimeError(t("chat_no_valid_response"))

    def _format_http_error(self, exc: requests.HTTPError) -> str:
        response = getattr(exc, "response", None)
        if response is None:
            return f"{t('chat_error_prefix')} {exc}"
        detail = self._format_api_error_response(response)
        return f"{t('chat_error_prefix')} {detail}"

    def _format_api_error_response(self, response: requests.Response) -> str:
        detail_text = ""
        payload = None
        try:
            _ = response.content  # ensure body is read for streamed responses
            payload = response.json()
        except ValueError:
            payload = None

        if isinstance(payload, dict):
            detail = payload.get("detail")
            if detail is None:
                detail = payload.get("message") or payload.get("error")
            detail_text = self._format_api_error_detail(detail)
            if not detail_text and payload:
                try:
                    detail_text = json.dumps(payload)
                except TypeError:
                    detail_text = str(payload)
        elif isinstance(payload, list):
            detail_text = "; ".join(str(item) for item in payload if item)

        if not detail_text:
            text = response.text.strip()
            if text:
                detail_text = text

        if not detail_text:
            reason = response.reason or ""
            detail_text = f"HTTP {response.status_code} {reason}".strip()

        return detail_text

    def _format_api_error_detail(self, detail: object) -> str:
        if isinstance(detail, dict):
            message = detail.get("message") or detail.get("detail") or ""
            estimated = detail.get("estimated_tokens")
            max_context = detail.get("max_context")
            if isinstance(estimated, int) and isinstance(max_context, int):
                token_hint = t(
                    "chat_error_tokens",
                    estimated=estimated,
                    max=max_context,
                )
                if message:
                    return f"{message} ({token_hint})"
                return token_hint
            return message or ""
        if isinstance(detail, list):
            return "; ".join(str(item) for item in detail if item)
        if detail is None:
            return ""
        return str(detail)

    @Slot(str)
    def _on_response_token(self, request_id: int, token: str):
        if request_id != self._active_request_id:
            return
        if self._stop_requested:
            return
        should_stick = self._is_near_bottom()
        if token.startswith(t("chat_error_prefix")):
            widget = self._ensure_current_reply_widget()
            self.current_response_text = token
            widget.set_response_text(token)
            widget.set_thinking_text("")
            return

        self._dismiss_queue_label()
        self.current_response_text += token
        widget = self._ensure_current_reply_widget()
        widget.set_response_text(self.current_response_text)
        if should_stick:
            self._scroll_to_bottom()

    @Slot(str)
    def _on_thinking_token(self, request_id: int, token: str):
        if request_id != self._active_request_id:
            return
        if not token:
            return
        if self._stop_requested:
            return
        should_stick = self._is_near_bottom()
        self._dismiss_queue_label()
        widget = self._ensure_current_reply_widget()
        self.current_thinking_text += token
        widget.set_thinking_text(self.current_thinking_text)
        if should_stick:
            self._scroll_to_bottom()

    @Slot(str, str)
    def _on_final_payload(self, request_id: int, thinking: str, message: str):
        if request_id != self._active_request_id:
            return
        if self._stop_requested:
            return
        if not thinking and not message:
            return
        should_stick = self._is_near_bottom()
        widget = self._ensure_current_reply_widget()
        self.current_thinking_text = thinking or self.current_thinking_text
        self.current_response_text = message or self.current_response_text
        widget.set_thinking_text(self.current_thinking_text)
        widget.set_response_text(self.current_response_text)
        if should_stick:
            self._scroll_to_bottom()

    def _ensure_current_reply_widget(self) -> AssistantMessageWidget:
        if self.current_reply_widget is None:
            self.current_reply_widget = self._append_message("assistant", "")
        return self.current_reply_widget

    def _show_typing_indicator(self) -> None:
        widget = self._ensure_current_reply_widget()
        widget.set_thinking_text("")
        widget.show_typing_indicator()
        self._scroll_to_bottom()

    def _dismiss_queue_label(self) -> None:
        if not self.queue_label:
            return
        container = self.queue_label.parentWidget()
        self._dispose_history_widget(container)
        self.queue_label = None

    def _auth_headers(self) -> dict[str, str] | None:
        token = self._ensure_token()
        if not token:
            return None
        return {"Authorization": f"Bearer {token}"}

    def _ensure_token(self) -> str | None:
        if self._bearer_token:
            return self._bearer_token
        if self._auto_token_error:
            return None
        self._bearer_token = self._fetch_auto_token() or ""
        return self._bearer_token or None

    def _refresh_auto_token(self) -> bool:
        """Forceer opnieuw ophalen als we geen manueel token hebben."""
        if BACKEND_BEARER_TOKEN:
            return False  # Manueel token moet gebruiker fixen
        self._bearer_token = ""
        self._auto_token_error = None
        token = self._fetch_auto_token()
        if token:
            self._bearer_token = token
            return True
        return False

    def _fetch_auto_token(self) -> str | None:
        """Vraag automatisch een token op via het eerste apparaat in /devices."""
        if BACKEND_BEARER_TOKEN:
            return BACKEND_BEARER_TOKEN
        self._auto_token_error = None
        try:
            resp = requests.get(f"{API_BASE}/devices", timeout=5)
            resp.raise_for_status()
            devices = resp.json() or []
        except Exception as exc:
            self._auto_token_error = (
                f"{t('chat_error_prefix')} {t('chat_could_not_fetch_devices')} {exc}"
            )
            return None
        if not devices:
            self._auto_token_error = f"{t('chat_error_prefix')} {t('chat_no_devices_found')}"
            return None
        primary = devices[0]
        payload = {
            "user_name": primary.get("user_name", ""),
            "password": primary.get("password", ""),
        }
        if not payload["user_name"] or not payload["password"]:
            self._auto_token_error = (
                f"{t('chat_error_prefix')} {t('chat_incomplete_device_data')}"
            )
            return None
        try:
            resp = requests.post(
                f"{API_BASE}/api/v1/signon",
                json=payload,
                timeout=5,
            )
            resp.raise_for_status()
            data = resp.json() or {}
            token = data.get("token")
            if not token:
                self._auto_token_error = f"{t('chat_error_prefix')} {t('chat_signon_no_token')}"
                return None
            return token
        except Exception as exc:
            self._auto_token_error = (
                f"{t('chat_error_prefix')} {t('chat_auto_token_failed')} {exc}"
            )
            return None

    @Slot()
    def _on_done(self, request_id: int):
        """Finalize the current message."""
        if request_id != self._active_request_id:
            return
        self._is_generating = False
        self._active_request_id = None
        self._sync_send_button()
        if self._stop_requested:
            self._stop_requested = False
            self.current_response_text = ""
            self.current_thinking_text = ""
            self.current_reply_widget = None
            return
        assistant_text = self.current_response_text.strip()
        if assistant_text and self.current_reply_widget is None:
            self.current_reply_widget = self._append_message("assistant", "")
            self.current_reply_widget.set_thinking_text(self.current_thinking_text)
            self.current_reply_widget.set_response_text(assistant_text)
        if self.current_reply_widget and not assistant_text:
            fallback = t("chat_no_response")
            self.current_reply_widget.set_response_text(fallback)
            assistant_text = fallback
        self.current_response_text = ""
        self.current_thinking_text = ""
        self.current_reply_widget = None

    @Slot(int)
    def _on_queue_position(self, request_id: int, position: int):
        """Update UI with queue position."""
        if request_id != self._active_request_id:
            return
        if position > 0:
            if not self.queue_label:
                self.queue_label = self._append_system_message(
                    t("chat_in_queue", position=position)
                )
            else:
                self.queue_label.setText(t("chat_in_queue", position=position))
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
        self.message_rows.append(row)
        self._scroll_to_bottom()
        return label

    def _append_message(self, role: str, text: str) -> QLabel | AssistantMessageWidget:
        self._set_empty_state_visible(False)

        row_outer = QWidget()
        row_outer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        row_outer_layout = QHBoxLayout(row_outer)
        row_outer_layout.setContentsMargins(0, 4, 0, 4)
        row_outer_layout.setSpacing(0)

        row_inner = QWidget()
        row_inner.setMaximumWidth(ASSISTANT_MAX_WIDTH if role == "assistant" else MAX_BUBBLE_WIDTH)
        row_inner.setSizePolicy(
            QSizePolicy.Expanding if role == "assistant" else QSizePolicy.Maximum,
            QSizePolicy.Maximum,
        )
        inner_layout = QHBoxLayout(row_inner)
        inner_layout.setContentsMargins(0, 0, 0, 0)
        inner_layout.setSpacing(12)

        bubble = QFrame()
        bubble.setObjectName("UserBubble" if role == "user" else "AssistantBubble")
        if role == "user":
            bubble.setStyleSheet("background:#111111; border:1px solid #111111; border-radius:20px;")
        self._apply_bubble_shadow(bubble)
        max_width = ASSISTANT_MAX_WIDTH if role == "assistant" else MAX_BUBBLE_WIDTH
        bubble.setMaximumWidth(int(max_width * (0.82 if role == "user" else 1.0)))
        bubble.setSizePolicy(
            QSizePolicy.Expanding if role == "assistant" else QSizePolicy.Maximum,
            QSizePolicy.Maximum,
        )
        bubble_layout = QVBoxLayout(bubble)
        bubble_layout.setContentsMargins(18, 14, 18, 14)
        bubble_layout.setSpacing(8)

        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(8)
        role_chip = QLabel(t("chat_role_user") if role == "user" else t("chat_role_assistant"))
        role_chip.setStyleSheet(
            "font-size:11px; font-weight:600; letter-spacing:0.08em; color:#a1a1aa;"
        )
        top_row.addWidget(role_chip, 0, Qt.AlignLeft)
        top_row.addStretch(1)
        timestamp_label = QLabel(datetime.now().strftime("%H:%M"))
        timestamp_label.setStyleSheet(
            f"font-size:11px; color:{'#ffffff' if role == 'user' else '#6b7280'};"
        )

        if role == "assistant":
            content_widget = AssistantMessageWidget()
            content_widget.set_response_text(text)
        else:
            label = QLabel()
            label.setWordWrap(True)
            label.setStyleSheet("border:none; background:transparent; color:#ffffff;")
            label.setTextInteractionFlags(Qt.TextSelectableByMouse)
            self._set_label_text(label, text)

        bubble_layout.addLayout(top_row)
        if role == "assistant":
            bubble_layout.addWidget(content_widget)
        else:
            bubble_layout.addWidget(label)

        bubble_layout.addWidget(timestamp_label, 0, Qt.AlignRight if role == "user" else Qt.AlignLeft)

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
        return content_widget if role == "assistant" else label

    def _build_assistant_avatar(self) -> QLabel:
        avatar = QLabel("🥚")
        avatar.setObjectName("AssistantAvatar")
        avatar.setAlignment(Qt.AlignCenter)
        avatar.setFixedSize(ASSISTANT_AVATAR_SIZE, ASSISTANT_AVATAR_SIZE)
        return avatar

    def _sync_send_button(self):
        self.send_btn.setText(t("chat_stop") if self._is_generating else t("chat_send"))

    def _stop_generation(self, show_feedback: bool = True):
        request_id = self._active_request_id
        if request_id is None and not self._is_generating and self.current_reply_widget is None:
            return
        if request_id is not None:
            asyncio.create_task(self._cancel_active_request(request_id))
        self._stop_requested = True
        self._is_generating = False
        self._active_request_id = None
        self.current_response_text = ""
        self.current_thinking_text = ""
        if self.current_reply_widget is not None and show_feedback:
            self.current_reply_widget.set_thinking_text("")
            self.current_reply_widget.show_feedback_message(t("chat_stop_feedback"))
        elif self.current_reply_widget is not None:
            self._remove_current_reply_widget()
        self._dismiss_queue_label()
        self._sync_send_button()
        if show_feedback:
            self.input.setPlaceholderText(t("chat_stop_feedback"))
            self.input.setFocus()
        else:
            self.input.setPlaceholderText(t("chat_placeholder"))

    def _remove_current_reply_widget(self) -> None:
        if self.current_reply_widget is None:
            return
        container = self.current_reply_widget.parentWidget()
        while container is not None and container not in self.message_rows:
            container = container.parentWidget()
        if container is not None:
            if container in self.message_rows:
                self.message_rows.remove(container)
            self._dispose_history_widget(container)
        self.current_reply_widget = None

    async def _cancel_active_request(self, request_id: int) -> None:
        try:
            await asyncio.to_thread(self._post_cancel_request, request_id)
        except Exception:
            pass

    def _post_cancel_request(self, request_id: int) -> None:
        requests.post(
            f"{API_BASE}/api/v1/ask/cancel",
            json={"request_id": str(request_id)},
            timeout=5,
            headers=self._auth_headers(),
        )

    def _copy_text(self, text: str):
        clipboard = QApplication.clipboard()
        clipboard.setText(text)

    def _copy_assistant_text(self, widget: AssistantMessageWidget):
        text = widget.response_text() or widget.thinking_text()
        if text:
            self._copy_text(text)

    def _handle_copy_click(self, widget: AssistantMessageWidget, button: QPushButton):
        self._copy_assistant_text(widget)
        original = button.text()
        button.setText(t("chat_copied"))
        button.setEnabled(False)

        def _restore():
            button.setText(original)
            button.setEnabled(True)

        QTimer.singleShot(2000, _restore)

    def _print_assistant_text(self, widget: AssistantMessageWidget):
        text = widget.response_text() or widget.thinking_text()
        if not text:
            return
        printer = QPrinter()
        dialog = QPrintDialog(printer, self)
        if dialog.exec() == QPrintDialog.Accepted:
            doc = QTextDocument()
            doc.setPlainText(text)
            doc.print_(printer)

    def _set_label_text(self, label: QLabel, text: str):
        safe = html.escape(text).replace("\n", "<br>")
        label.setText(safe)
        label.setProperty("_plain_text", text)

    def _rebuild_history_view(self) -> None:
        old_container = self.history_container

        self.history_container = QWidget()
        self.history_container.setStyleSheet("background:transparent;")
        self.history_layout = QVBoxLayout(self.history_container)
        self.history_layout.setContentsMargins(SIDE_PADDING, 16, SIDE_PADDING, 16)
        self.history_layout.setSpacing(ROW_GAP)

        self.empty_state = QWidget()
        self.empty_state.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        empty_state_layout = QVBoxLayout(self.empty_state)
        empty_state_layout.setContentsMargins(0, 0, 0, 0)
        empty_state_layout.setSpacing(0)
        empty_state_layout.addStretch(1)

        self.empty_label = QLabel(t("chat_welcome"))
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.setStyleSheet("color:#9ca3af; font-size:14px; background:transparent;")
        empty_state_layout.addWidget(self.empty_label, 0, Qt.AlignCenter)
        empty_state_layout.addStretch(1)

        self.history_layout.addWidget(self.empty_state, 1)
        self.history_layout.addStretch(1)
        self.history_scroll.setWidget(self.history_container)

        if old_container is not None:
            old_container.hide()
            old_container.setParent(None)
            old_container.deleteLater()

    def _insert_history_row(self, row: QWidget):
        index = max(0, self.history_layout.count() - 1)
        self.history_layout.insertWidget(index, row)

    def _dispose_history_widget(self, widget: QWidget | None) -> None:
        if widget is None:
            return
        self.history_layout.removeWidget(widget)
        widget.hide()
        widget.setParent(None)
        widget.deleteLater()

    def _set_empty_state_visible(self, visible: bool) -> None:
        if self.empty_state is None:
            return
        self.empty_state.setVisible(visible)
        if visible:
            self.empty_label.setText(t("chat_welcome"))
            self.history_scroll.verticalScrollBar().setValue(0)

    def _restore_empty_state(self) -> None:
        if not self.empty_label:
            return
        self._set_empty_state_visible(True)

    def _clear_history(self):
        self.message_rows.clear()
        self.queue_label = None
        self.current_reply_widget = None
        self._rebuild_history_view()
        self._restore_empty_state()

    def _apply_bubble_shadow(self, widget: QWidget) -> None:
        shadow = QGraphicsDropShadowEffect(widget)
        shadow.setBlurRadius(16)
        shadow.setOffset(0, 2)
        shadow.setColor(QColor(17, 17, 17, 18))
        widget.setGraphicsEffect(shadow)

    def _is_near_bottom(self, threshold: int = 48) -> bool:
        bar = self.history_scroll.verticalScrollBar()
        return (bar.maximum() - bar.value()) <= threshold

    def _scroll_to_bottom(self):
        def _do_scroll():
            bar = self.history_scroll.verticalScrollBar()
            bar.setValue(bar.maximum())

        QTimer.singleShot(0, _do_scroll)
