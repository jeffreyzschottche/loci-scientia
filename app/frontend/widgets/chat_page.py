from __future__ import annotations

import asyncio
import html
import json

import requests
from datetime import datetime
from PySide6.QtCore import QObject, Qt, QTimer, Signal, Slot
from PySide6.QtGui import QTextDocument, QTextOption
from PySide6.QtPrintSupport import QPrintDialog, QPrinter
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
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
MODE_DEFAULT_KEY = "__default__"


class ChatSignals(QObject):
    response_token = Signal(str)
    thinking_token = Signal(str)
    final_payload = Signal(str, str)
    done = Signal()
    queue_position = Signal(int)


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
        finally:
            self._syncing_height = False


class AssistantMessageWidget(QWidget):
    thinking_toggled = Signal(bool)

    def __init__(self):
        super().__init__()
        self._response_text = ""
        self._thinking_text = ""
        self._thinking_initialized = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        self.setMinimumWidth(ASSISTANT_MIN_WIDTH)

        self.thinking_card = QFrame()
        self.thinking_card.setStyleSheet(
            "QFrame {"
            "  background:#f8fafc;"
            "  border:1px solid #dbe4ef;"
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
            "  color:#334155;"
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
            "background:transparent; border:none; color:#334155; line-height:1.5;"
        )
        thinking_layout.addWidget(self.thinking_view)
        layout.addWidget(self.thinking_card)

        self.response_view = AutoSizingMarkdownView()
        self.response_view.setStyleSheet("background:transparent; border:none; color:#111827;")
        layout.addWidget(self.response_view)

        self.set_thinking_text("")
        self.set_response_text("")

    def set_response_text(self, text: str) -> None:
        self._response_text = text or ""
        self.response_view.set_markdown_text(self._response_text)

    def set_thinking_text(self, text: str) -> None:
        self._thinking_text = text or ""
        has_thinking = bool(self._thinking_text.strip())
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
        self.selected_mode: str | None = None
        self.mode_buttons: dict[str, QPushButton] = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        controls = QHBoxLayout()
        controls.setContentsMargins(0, 0, 0, 0)
        controls.addStretch(1)
        self.new_chat_btn = QPushButton(t("chat_start_new"))
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

        self.mode_card = QFrame()
        self.mode_card.setObjectName("ChatModeCard")
        self.mode_card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.mode_card.setMaximumHeight(44)
        self.mode_card.setStyleSheet(
            "QFrame#ChatModeCard {"
            "  background: transparent;"
            "  border: none;"
            "}"
            "QPushButton[modeChip='true'] {"
            "  background:#ffffff;"
            "  border:1px solid #e5e7eb;"
            "  border-radius:999px;"
            "  color:#374151;"
            "  font-weight:600;"
            "  padding:3px 14px;"
            "}"
            "QPushButton[modeChip='true']:hover { border-color:#111111; color:#111111; }"
            "QPushButton[modeChip='true'][active='true'] {"
            "  background:#111111;"
            "  border-color:#111111;"
            "  color:#facc15;"
            "}"
        )
        mode_layout = QVBoxLayout(self.mode_card)
        mode_layout.setContentsMargins(0, 0, 0, 0)
        mode_layout.setSpacing(0)

        mode_scroll = QScrollArea()
        mode_scroll.setWidgetResizable(True)
        mode_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        mode_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        mode_scroll.setFrameShape(QFrame.NoFrame)
        mode_scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        mode_scroll.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        mode_scroll.setFixedHeight(30)

        mode_container = QWidget()
        self.mode_chip_layout = QHBoxLayout(mode_container)
        self.mode_chip_layout.setContentsMargins(0, 0, 0, 0)
        self.mode_chip_layout.setSpacing(8)
        self._create_mode_chip(t("chat_mode_default"), None)
        for mode in self.available_modes:
            self._create_mode_chip(mode, mode)
        self.mode_chip_layout.addStretch(1)
        mode_scroll.setWidget(mode_container)
        mode_layout.addWidget(mode_scroll)
        layout.addWidget(self.mode_card)
        self._set_selected_mode(None)

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
        self.empty_label = QLabel(t("chat_welcome"))
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
        self.input.setPlaceholderText(t("chat_placeholder"))
        self.send_btn = QPushButton(t("chat_send"))
        input_layout.addWidget(self.input, 1)
        input_layout.addWidget(self.send_btn)
        layout.addWidget(input_card)

        self.send_btn.clicked.connect(self._on_send)
        self.input.returnPressed.connect(self._on_send)
        self.signals.response_token.connect(self._on_response_token)
        self.signals.thinking_token.connect(self._on_thinking_token)
        self.signals.final_payload.connect(self._on_final_payload)
        self.signals.done.connect(self._on_done)
        self.signals.queue_position.connect(self._on_queue_position)

        register_language_change_callback(self._update_translations)
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


    def _update_translations(self) -> None:
        """Update UI elements when language changes."""
        self.new_chat_btn.setText(t("chat_start_new"))
        self.input.setPlaceholderText(t("chat_placeholder"))
        self.send_btn.setText(t("chat_send"))
        default_btn = self.mode_buttons.get(MODE_DEFAULT_KEY)
        if default_btn:
            default_btn.setText(t("chat_mode_default"))
        if self.empty_label:
            self.empty_label.setText(t("chat_welcome"))

    def _create_mode_chip(self, label: str, mode: str | None) -> QPushButton:
        key = mode or MODE_DEFAULT_KEY
        button = QPushButton(label)
        button.setCursor(Qt.PointingHandCursor)
        button.setProperty("modeChip", "true")
        button.setProperty("active", "false")
        button.setCheckable(True)
        button.clicked.connect(lambda checked=False, value=mode: self._set_selected_mode(value))
        self.mode_buttons[key] = button
        self.mode_chip_layout.addWidget(button, 0, Qt.AlignLeft)
        return button

    def _set_selected_mode(self, mode: str | None) -> None:
        self.selected_mode = mode
        active_key = mode or MODE_DEFAULT_KEY
        for key, button in self.mode_buttons.items():
            is_active = key == active_key
            button.setChecked(is_active)
            button.setProperty("active", "true" if is_active else "false")
            style = button.style()
            style.unpolish(button)
            style.polish(button)
            button.update()

    def _start_new_chat(self):
        """Reset the conversation history."""
        self._clear_history()
        self.current_response_text = ""
        self.current_thinking_text = ""
        self.current_reply_widget = None
        self.queue_label = None
        asyncio.create_task(self._reset_remote_history())

    @Slot()
    def _on_send(self):
        text = self.input.text().strip()
        if not text:
            return
        self._append_message("user", text)
        self.input.clear()
        self.current_response_text = ""
        self.current_thinking_text = ""
        self.current_reply_widget = None
        self._show_typing_indicator()
        asyncio.create_task(self._stream(text, self.selected_mode))

    def _request_payload(self, prompt: str, mode: str | None = None) -> dict:
        payload = {
            "prompt": prompt,
            "max_new_tokens": 128,
        }
        if mode:
            payload["mode"] = mode
        return payload

    async def _stream(self, prompt: str, mode: str | None):
        try:
            await asyncio.to_thread(self._stream_sse, prompt, mode)
            return
        except requests.HTTPError as exc:
            status = getattr(exc.response, "status_code", None)
            if status == 401:
                # Probeer automatisch een token op te halen voor de lokale admin.
                if self._refresh_auto_token():
                    await asyncio.to_thread(self._stream_sse, prompt, mode)
                    return
                message = (
                    self._auto_token_error
                    or f"{t('chat_error_prefix')} {t('chat_error_401')}"
                )
                self.signals.response_token.emit(message)
                self.signals.done.emit()
                return
            if status != 404:
                self.signals.response_token.emit(f"{t('chat_error_prefix')} {exc}")
                self.signals.done.emit()
                return
            # 404 betekent dat streaming endpoint nog niet bestaat -> fallback
        except Exception as exc:
            self.signals.response_token.emit(f"{t('chat_error_prefix')} {exc}")
            self.signals.done.emit()
            return

        try:
            payload = await asyncio.to_thread(self._legacy_post, prompt, mode)
        except Exception as exc:
            self.signals.response_token.emit(f"{t('chat_error_prefix')} {exc}")
        else:
            self.signals.final_payload.emit(
                payload.get("thinking", ""),
                payload.get("message", ""),
            )
        self.signals.done.emit()

    def _stream_sse(self, prompt: str, mode: str | None = None) -> None:
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

                if "thinking" in event_data and not event_data.get("done"):
                    token = event_data.get("thinking") or ""
                    if token:
                        self.signals.thinking_token.emit(token)
                    continue

                if "token" in event_data and not event_data.get("done"):
                    token = event_data.get("token") or ""
                    if token:
                        self.signals.response_token.emit(token)
                    continue

                if event_data.get("done"):
                    self.signals.final_payload.emit(
                        event_data.get("thinking", "") or "",
                        event_data.get("message", "") or "",
                    )
                    self.signals.done.emit()
                    return

        # Als de stream eindigt zonder done-event, sluit netjes af.
        self.signals.done.emit()

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
    def _on_response_token(self, token: str):
        if token.startswith(t("chat_error_prefix")):
            widget = self._ensure_current_reply_widget()
            self.current_response_text = token
            widget.set_response_text(token)
            widget.set_thinking_text("")
            return

        self._dismiss_queue_label()
        self.current_response_text += token

    @Slot(str)
    def _on_thinking_token(self, token: str):
        if not token:
            return
        self._dismiss_queue_label()
        widget = self._ensure_current_reply_widget()
        self.current_thinking_text += token
        widget.set_thinking_text(self.current_thinking_text)

    @Slot(str, str)
    def _on_final_payload(self, thinking: str, message: str):
        if not thinking and not message:
            return
        widget = self._ensure_current_reply_widget()
        self.current_thinking_text = thinking or self.current_thinking_text
        self.current_response_text = message or self.current_response_text
        widget.set_thinking_text(self.current_thinking_text)
        widget.set_response_text(self.current_response_text)
        self._scroll_to_bottom()

    def _ensure_current_reply_widget(self) -> AssistantMessageWidget:
        if self.current_reply_widget is None:
            self.current_reply_widget = self._append_message("assistant", "")
        return self.current_reply_widget

    def _dismiss_queue_label(self) -> None:
        if not self.queue_label:
            return
        container = self.queue_label.parentWidget()
        self.history_layout.removeWidget(container)
        container.deleteLater()
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
    def _on_done(self):
        """Finalize the current message."""
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
    def _on_queue_position(self, position: int):
        """Update UI with queue position."""
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
        self._scroll_to_bottom()
        return label

    def _append_message(self, role: str, text: str) -> QLabel | AssistantMessageWidget:
        if self.empty_label:
            self.empty_label.hide()

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

            copy_btn = QPushButton(t("chat_copy"))
            copy_btn.setObjectName("CopyButton")
            copy_btn.setCursor(Qt.PointingHandCursor)
            copy_btn.setFixedHeight(26)
            copy_btn.clicked.connect(
                lambda _, widget=content_widget, btn=copy_btn: self._handle_copy_click(widget, btn)
            )
            top_row.addWidget(copy_btn, 0, Qt.AlignRight)

            print_btn = QPushButton(t("chat_print"))
            print_btn.setObjectName("CopyButton")
            print_btn.setCursor(Qt.PointingHandCursor)
            print_btn.setFixedHeight(26)
            print_btn.clicked.connect(lambda _, widget=content_widget: self._print_assistant_text(widget))
            top_row.addWidget(print_btn, 0, Qt.AlignRight)
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

    def _show_typing_indicator(self):
        if self.current_reply_widget is not None:
            return
        self.current_reply_widget = self._append_message("assistant", "")
        self.current_response_text = ""
        self.current_thinking_text = ""

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

    async def _reset_remote_history(self) -> None:
        try:
            await asyncio.to_thread(self._post_reset_history)
        except Exception:
            pass

    def _post_reset_history(self) -> None:
        url = f"{API_BASE}/api/v1/ask/reset"
        headers = self._auth_headers()
        try:
            resp = requests.post(url, timeout=5, headers=headers)
            if resp.status_code == 401 and self._refresh_auto_token():
                headers = self._auth_headers()
                resp = requests.post(url, timeout=5, headers=headers)
            resp.raise_for_status()
        except Exception:
            return
