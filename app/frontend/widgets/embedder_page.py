from __future__ import annotations

import io
from typing import Optional

import requests
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ..config import BACKEND_HTTP, PUBLIC_BASE_URL
from ..translations import register_language_change_callback, t


def _render_qr_pixmap(text: str, size: int = 280) -> Optional[QPixmap]:
    try:
        import qrcode  # type: ignore
    except ImportError:
        return None
    try:
        qr = qrcode.QRCode(border=2, box_size=10)
        qr.add_data(text)
        qr.make(fit=True)
        img = qr.make_image(fill_color="#0f172a", back_color="white").convert("RGB")
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        pixmap = QPixmap()
        if not pixmap.loadFromData(buffer.getvalue(), "PNG"):
            return None
        return pixmap.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    except Exception:
        return None


def _embedder_url() -> str:
    return (PUBLIC_BASE_URL or BACKEND_HTTP).rstrip("/") + "/embedder/"


class EmbedderPage(QWidget):
    """Toont een QR-code en URL voor de Embedding Application.

    Het idee: een medewerker scant de QR met een eigen laptop/tablet om de
    embedding-admin te openen, zonder dat dit toestel zelf gebruikt hoeft te
    worden. Status wordt elke paar seconden ge-pingt zodat duidelijk is of
    de Laravel-backend en de SPA daadwerkelijk draaien.
    """

    STATUS_POLL_MS = 5000
    CARD_WIDTH = 480

    def __init__(self):
        super().__init__()
        # Geen WA_StyledBackground: laat de pagina transparant zodat het
        # binnenste EmbedderCard mooi vrijstaat op de grijze content-area.
        # (main.py zet objectName="Card", maar zonder StyledBackground
        # rendert die regel niet — wat we hier juist willen.)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(48, 24, 48, 48)
        outer.setSpacing(0)
        # De subtitel op de pagina-header (main.py page_subtitle) levert al de
        # uitleg; we hebben hier geen extra intro-paragraaf nodig en daarmee
        # geen wrap/heightForWidth-gepuzzel.

        # ---- Card with QR + URL + copy button --------------------------------
        card = QFrame()
        card.setObjectName("EmbedderCard")
        card.setStyleSheet(
            "QFrame#EmbedderCard {"
            "  background:#ffffff;"
            "  border:1px solid #ececec;"
            "  border-radius:28px;"
            "}"
        )
        card.setFixedWidth(self.CARD_WIDTH)
        card.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Maximum)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(32, 28, 32, 32)
        card_layout.setSpacing(18)
        # GEEN setAlignment(AlignHCenter) op het layout — dat zou children
        # hun sizeHint laten gebruiken en wrapped tekst afkappen.

        # Status badge — centered horizontally via the addWidget alignment flag
        self._status_badge = QLabel()
        self._status_badge.setAlignment(Qt.AlignCenter)
        self._status_badge.setFixedHeight(28)
        self._status_badge.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
        self._set_status(False)
        card_layout.addWidget(self._status_badge, 0, Qt.AlignHCenter)

        # QR code (square, centered)
        self._qr_label = QLabel()
        self._qr_label.setAlignment(Qt.AlignCenter)
        self._qr_label.setFixedSize(320, 320)
        self._qr_label.setStyleSheet(
            "QLabel {"
            "  background:#ffffff;"
            "  border:1px solid #e7dcc0;"
            "  border-radius:20px;"
            "  padding:14px;"
            "}"
        )
        card_layout.addWidget(self._qr_label, 0, Qt.AlignHCenter)

        # QR hint — single short line; no wordWrap → no clipping risk.
        self._qr_hint = QLabel(t("embedder_qr_hint"))
        self._qr_hint.setAlignment(Qt.AlignCenter)
        self._qr_hint.setStyleSheet("color:#6b7280; font-size:12px;")
        card_layout.addWidget(self._qr_hint)

        # URL pill — fills card width so a long URL doesn't get truncated.
        self._url_label = QLabel()
        self._url_label.setAlignment(Qt.AlignCenter)
        self._url_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self._url_label.setWordWrap(True)
        self._url_label.setStyleSheet(
            "QLabel {"
            "  font-size:14px; font-weight:700; color:#0f172a;"
            "  background:#f8f6ef; border:1px solid #e7dcc0;"
            "  border-radius:14px;"
            "  padding:10px 18px;"
            "}"
        )
        card_layout.addWidget(self._url_label)

        outer.addWidget(card, 0, Qt.AlignHCenter)
        outer.addStretch(1)

        # ---- Initial paint + status polling ---------------------------------
        self._refresh_url_and_qr()

        self._status_timer = QTimer(self)
        self._status_timer.setInterval(self.STATUS_POLL_MS)
        self._status_timer.timeout.connect(self._check_status)
        self._status_timer.start()
        QTimer.singleShot(0, self._check_status)

        register_language_change_callback(self._update_translations)

    # ------------------------------------------------------------------ helpers

    def _refresh_url_and_qr(self) -> None:
        url = _embedder_url()
        self._url_label.setText(url)
        pixmap = _render_qr_pixmap(url, size=280)
        if pixmap is not None:
            self._qr_label.setPixmap(pixmap)
        else:
            self._qr_label.setText(t("embedder_qr_missing"))

    def _set_status(self, online: bool) -> None:
        if online:
            self._status_badge.setText(f"●  {t('embedder_status_online')}")
            self._status_badge.setStyleSheet(
                "QLabel {"
                "  color:#15803d; background:#ecfdf5;"
                "  border:1px solid #bbf7d0; border-radius:14px;"
                "  padding:4px 16px; font-size:11px; font-weight:700;"
                "  letter-spacing:0.18em;"
                "}"
            )
        else:
            self._status_badge.setText(f"○  {t('embedder_status_offline')}")
            self._status_badge.setStyleSheet(
                "QLabel {"
                "  color:#6b7280; background:#f3f4f6;"
                "  border:1px solid #e5e7eb; border-radius:14px;"
                "  padding:4px 16px; font-size:11px; font-weight:700;"
                "  letter-spacing:0.18em;"
                "}"
            )

    def _check_status(self) -> None:
        try:
            resp = requests.head(
                f"{BACKEND_HTTP.rstrip('/')}/embedder/",
                timeout=1.5,
                allow_redirects=True,
            )
            self._set_status(resp.status_code < 400)
        except requests.RequestException:
            self._set_status(False)

    def _update_translations(self) -> None:
        self._qr_hint.setText(t("embedder_qr_hint"))
        self._check_status()
        self._refresh_url_and_qr()

    def on_page_shown(self) -> None:
        self._refresh_url_and_qr()
        self._check_status()
