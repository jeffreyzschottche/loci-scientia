from __future__ import annotations

import os
import shutil
from datetime import datetime
from pathlib import Path

import requests
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..config import BACKEND_BEARER_TOKEN, BACKEND_HTTP, BACKEND_TIMEOUT
from ..translations import t, register_language_change_callback
from ...backend.kennisbank_sync import _knowledge_embedded_path
from .dialog_style import show_error_dialog
from .embedder_page import _embedder_qr_payload, _embedder_url, _render_qr_pixmap


class KnowledgePage(QWidget):
    def __init__(self):
        super().__init__()
        self._main_layout = QVBoxLayout(self)
        self._main_layout.setContentsMargins(16, 16, 16, 16)
        self._main_layout.setSpacing(16)

        self._stat_title_labels: list[QLabel] = []
        self._stat_value_labels: list[QLabel] = []
        self._stat_detail_labels: list[QLabel] = []
        self._vector_title_label: QLabel | None = None
        self._vector_entry_labels: list[QLabel] = []
        self._vector_value_summary_labels: list[QLabel] = []
        self._vector_progress_bars: list[QProgressBar] = []
        self._actions_documents_title_label: QLabel | None = None
        self._actions_documents_value_label: QLabel | None = None
        self._actions_documents_detail_label: QLabel | None = None
        self._embedder_status_badge: QLabel | None = None
        self._embedder_qr_label: QLabel | None = None
        self._embedder_qr_hint: QLabel | None = None
        self._embedder_url_label: QLabel | None = None
        self._documents_title_label: QLabel | None = None
        self._documents_search_input: QLineEdit | None = None
        self._documents_refresh_button: QPushButton | None = None
        self._documents_table: QTableWidget | None = None
        self._preview_title_label: QLabel | None = None
        self._preview_meta_label: QLabel | None = None
        self._preview_text: QTextEdit | None = None
        self._sync_status_label: QLabel | None = None
        self._sync_details_label: QLabel | None = None
        self._sync_meta_label: QLabel | None = None

        self._documents_data: list[dict] = []
        self._filtered_documents_data: list[dict] = []
        self._sync_state: dict | None = None
        self._preview_cache: dict[str, dict] = {}
        self._latest_stats: dict | None = None
        self._latest_qdrant: dict | None = None

        top_grid = QGridLayout()
        top_grid.setHorizontalSpacing(16)
        top_grid.setVerticalSpacing(16)
        top_grid.setColumnStretch(0, 3)
        top_grid.setColumnStretch(1, 1)
        top_grid.addWidget(self._sync_status_card(), 0, 0)
        top_grid.addWidget(self._embedder_access_card(), 0, 1)
        self._main_layout.addLayout(top_grid)

        self._main_layout.addLayout(self._stats_grid())

        self._main_layout.addLayout(self._documents_section())

        self._refresh_sync_state()
        self._refresh_library()
        self._refresh_embedder_access()
        self._embedder_status_timer = QTimer(self)
        self._embedder_status_timer.setInterval(5000)
        self._embedder_status_timer.timeout.connect(self._check_embedder_status)
        self._embedder_status_timer.start()
        QTimer.singleShot(0, self._check_embedder_status)
        register_language_change_callback(self._update_translations)

    def _update_translations(self) -> None:
        if self._sync_status_label and self._sync_state:
            self._update_sync_labels(self._sync_state)

        stat_titles = [
            t("kb_vector_db_title"),
        ]
        for idx, label in enumerate(self._stat_title_labels):
            if idx < len(stat_titles):
                label.setText(stat_titles[idx].upper())

        if self._actions_documents_title_label:
            self._actions_documents_title_label.setText(t("kb_stat_documents").upper())
        if self._embedder_qr_hint:
            self._embedder_qr_hint.setText(t("embedder_qr_hint"))
        self._refresh_embedder_access()

        if self._vector_title_label:
            self._vector_title_label.setText(t("kb_vector_db_title"))
        vector_labels = [
            t("kb_vector_progress_storage"),
            t("kb_vector_progress_embeddings"),
        ]
        for idx, label in enumerate(self._vector_entry_labels):
            if idx < len(vector_labels):
                label.setText(vector_labels[idx].upper())
        for idx, label in enumerate(self._vector_value_summary_labels):
            if idx == 0:
                label.setText("0 GB / 0 GB")
            elif idx == 1:
                label.setText("0 / 0 docs")

        if self._documents_title_label:
            self._documents_title_label.setText(t("kb_documents"))
        if self._documents_search_input:
            self._documents_search_input.setPlaceholderText(t("kb_documents_search_placeholder"))
        if self._documents_refresh_button:
            self._documents_refresh_button.setText(t("kb_documents_refresh"))
            self._documents_refresh_button.setToolTip(t("kb_documents_refresh_tooltip"))
        if self._documents_table:
            self._documents_table.setHorizontalHeaderLabels(
                [
                    t("kb_table_document"),
                    t("kb_table_category"),
                    t("kb_table_priority"),
                    t("kb_table_chunks"),
                    t("kb_table_content_date"),
                ]
            )
        if self._preview_title_label and not self._preview_title_label.text():
            self._preview_title_label.setText(t("kb_preview_empty_title"))
        if self._preview_meta_label and not self._preview_meta_label.text():
            self._preview_meta_label.setText(t("kb_preview_empty_body"))

    def _pill_button(self, text: str, primary: bool = False) -> QPushButton:
        btn = QPushButton(text)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet("text-align:center;")
        if primary:
            btn.setStyleSheet(
                "QPushButton {"
                "  background:#facc15;"
                "  color:#050505;"
                "  border-radius:20px;"
                "  padding:10px 28px;"
                "  font-weight:600;"
                "  text-align:center;"
                "}"
                "QPushButton:hover { background:#050505; color:#facc15; }"
            )
        else:
            btn.setStyleSheet(
                "QPushButton {"
                "  background:transparent;"
                "  border:1px solid rgba(33,33,33,0.2);"
                "  color:#111111;"
                "  border-radius:20px;"
                "  padding:10px 28px;"
                "  font-weight:600;"
                "  text-align:center;"
                "}"
                "QPushButton:hover { border-color:rgba(33,33,33,0.45); }"
            )
        btn.setFixedHeight(40)
        return btn

    def _embedder_access_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("Card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 18)
        layout.setSpacing(8)

        self._embedder_status_badge = QLabel()
        self._embedder_status_badge.setAlignment(Qt.AlignCenter)
        self._embedder_status_badge.setFixedHeight(26)
        layout.addWidget(self._embedder_status_badge, 0, Qt.AlignHCenter)

        self._embedder_qr_label = QLabel()
        self._embedder_qr_label.setAlignment(Qt.AlignCenter)
        self._embedder_qr_label.setFixedSize(178, 178)
        self._embedder_qr_label.setStyleSheet(
            "QLabel {"
            "  background:#ffffff;"
            "  border:1px solid #e7dcc0;"
            "  border-radius:18px;"
            "  padding:10px;"
            "}"
        )
        layout.addWidget(self._embedder_qr_label, 0, Qt.AlignHCenter)

        self._embedder_qr_hint = QLabel(t("embedder_qr_hint"))
        self._embedder_qr_hint.setAlignment(Qt.AlignCenter)
        self._embedder_qr_hint.setWordWrap(True)
        self._embedder_qr_hint.setStyleSheet("color:#6b7280; font-size:11px;")
        layout.addWidget(self._embedder_qr_hint)

        self._embedder_url_label = QLabel()
        self._embedder_url_label.setAlignment(Qt.AlignCenter)
        self._embedder_url_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self._embedder_url_label.setWordWrap(True)
        self._embedder_url_label.setStyleSheet(
            "QLabel {"
            "  font-size:12px; font-weight:700; color:#0f172a;"
            "  background:#f8f6ef; border:1px solid #e7dcc0;"
            "  border-radius:12px;"
            "  padding:8px 12px;"
            "}"
        )
        layout.addWidget(self._embedder_url_label)
        return card

    def _sync_status_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("Card")
        card.setMaximumHeight(230)
        layout = QHBoxLayout(card)
        layout.setContentsMargins(16, 8, 16, 8)
        layout.setSpacing(24)

        sync_panel = QWidget()
        sync_layout = QVBoxLayout(sync_panel)
        sync_layout.setContentsMargins(0, 12, 0, 14)
        sync_layout.setSpacing(6)

        title = QLabel(t("kb_sync_last").upper())
        title.setStyleSheet("color:#6b7280; letter-spacing:0.35em; font-size:11px;")
        sync_layout.addWidget(title)

        self._sync_status_label = QLabel(t("kb_sync_never"))
        self._sync_status_label.setStyleSheet(
            "font-size:16px; font-weight:600; color:#111111; margin:0; padding:0; line-height:1.0;"
        )
        sync_layout.addWidget(self._sync_status_label)

        self._sync_details_label = QLabel("")
        self._sync_details_label.setStyleSheet("color:#4b5563; font-size:15px; font-weight:600;")
        sync_layout.addWidget(self._sync_details_label)

        self._sync_meta_label = QLabel("")
        self._sync_meta_label.setWordWrap(True)
        self._sync_meta_label.setStyleSheet("color:#4b5563; font-size:14px; line-height:1.45;")
        sync_layout.addWidget(self._sync_meta_label)

        divider = QFrame()
        divider.setFrameShape(QFrame.VLine)
        divider.setStyleSheet("color:#ece7dc; background:#ece7dc; min-width:1px; max-width:1px;")

        layout.addWidget(sync_panel, 1)
        layout.addWidget(divider)
        layout.addWidget(self._vector_status_card(), 2)
        return card

    def _stats_grid(self) -> QGridLayout:
        grid = QGridLayout()
        grid.setSpacing(12)
        grid.setColumnStretch(0, 1)
        return grid

    def _vector_status_card(self) -> QFrame:
        card = QFrame()
        card.setStyleSheet("QFrame { background:transparent; border:none; }")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(0, 12, 0, 14)
        layout.setSpacing(18)
        self._vector_title_label = QLabel(t("kb_vector_db_title"))
        self._vector_title_label.setStyleSheet("font-size:20px; font-weight:700; letter-spacing:0.02em;")
        layout.addWidget(self._vector_title_label)

        rows = [
            t("kb_vector_progress_storage"),
            t("kb_vector_progress_embeddings"),
        ]
        for label_text in rows:
            block = QVBoxLayout()
            block.setSpacing(8)

            header_row = QHBoxLayout()
            header_row.setSpacing(16)

            lbl = QLabel(label_text.upper())
            lbl.setStyleSheet("color:#6b7280; letter-spacing:0.28em; font-size:11px; font-weight:600;")
            self._vector_entry_labels.append(lbl)
            header_row.addWidget(lbl, 0)
            header_row.addStretch(1)

            value_lbl = QLabel("-")
            value_lbl.setStyleSheet("color:#4b5563; font-size:12px; font-weight:600;")
            self._vector_value_summary_labels.append(value_lbl)
            header_row.addWidget(value_lbl, 0, Qt.AlignRight)
            block.addLayout(header_row)

            bar = QProgressBar()
            bar.setRange(0, 100)
            bar.setValue(0)
            bar.setTextVisible(False)
            bar.setFixedHeight(12)
            bar.setStyleSheet(
                "QProgressBar {"
                "  background:#ece7dc;"
                "  border:none;"
                "  border-radius:6px;"
                "}"
                "QProgressBar::chunk {"
                "  background:#facc15;"
                "  border-radius:6px;"
                "}"
            )
            self._vector_progress_bars.append(bar)
            block.addWidget(bar)

            layout.addLayout(block)
        return card

    def _documents_section(self) -> QHBoxLayout:
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        layout.addWidget(self._documents_table_widget(), 9, Qt.AlignTop)
        layout.addWidget(self._preview_card(), 11)
        return layout

    def _documents_table_widget(self) -> QFrame:
        card = QFrame()
        card.setObjectName("Card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 16, 16, 16)
        card_layout.setSpacing(12)

        self._documents_title_label = QLabel(t("kb_documents"))
        self._documents_title_label.setStyleSheet(
            "font-size:20px; font-weight:700; letter-spacing:0.02em;"
        )
        card_layout.addWidget(self._documents_title_label)

        self._documents_search_input = QLineEdit()
        self._documents_search_input.setPlaceholderText(t("kb_documents_search_placeholder"))
        self._documents_search_input.setStyleSheet(
            "QLineEdit {"
            "  background:#fcfbf8;"
            "  border:1px solid #ece7dc;"
            "  border-radius:16px;"
            "  padding:10px 14px;"
            "  color:#111111;"
            "}"
        )
        self._documents_search_input.textChanged.connect(self._apply_documents_filter)

        self._documents_refresh_button = QPushButton(t("kb_documents_refresh"))
        self._documents_refresh_button.setToolTip(t("kb_documents_refresh_tooltip"))
        self._documents_refresh_button.setCursor(Qt.PointingHandCursor)
        self._documents_refresh_button.setStyleSheet(
            "QPushButton {"
            "  background:#fcfbf8;"
            "  border:1px solid #ece7dc;"
            "  border-radius:16px;"
            "  padding:10px 18px;"
            "  color:#111111;"
            "  font-weight:600;"
            "}"
            "QPushButton:hover { background:#f4eeda; border-color:#d6cdb4; }"
            "QPushButton:disabled { color:#9a9183; }"
        )
        self._documents_refresh_button.clicked.connect(self._handle_refresh_clicked)

        search_row = QHBoxLayout()
        search_row.setSpacing(8)
        search_row.addWidget(self._documents_search_input, 1)
        search_row.addWidget(self._documents_refresh_button)
        card_layout.addLayout(search_row)

        self._documents_table = QTableWidget()
        self._documents_table.setColumnCount(5)
        self._documents_table.setHorizontalHeaderLabels(
            [
                t("kb_table_document"),
                t("kb_table_category"),
                t("kb_table_priority"),
                t("kb_table_chunks"),
                t("kb_table_content_date"),
            ]
        )
        self._documents_table.verticalHeader().setVisible(False)
        self._documents_table.setShowGrid(False)
        self._documents_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._documents_table.setSelectionMode(QTableWidget.SingleSelection)
        self._documents_table.setSelectionBehavior(QTableWidget.SelectRows)
        self._documents_table.setAlternatingRowColors(False)
        self._documents_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._documents_table.cellClicked.connect(self._handle_document_selected)
        self._documents_table.setWordWrap(False)

        header = self._documents_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        for idx in range(1, 5):
            header.setSectionResizeMode(idx, QHeaderView.ResizeToContents)
        header.setStyleSheet(
            "QHeaderView::section { background:#ffffff; color:#111111; border:0; font-weight:600; }"
        )
        self._documents_table.setStyleSheet(
            "QTableWidget { background:#ffffff; border:0; }"
            "QTableWidget::item { border-bottom:1px solid #f4f4f5; }"
        )
        card_layout.addWidget(self._documents_table)
        return card

    def _preview_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("Card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        title = QLabel(t("kb_preview_title"))
        title.setStyleSheet("font-size:20px; font-weight:700; letter-spacing:0.02em;")
        layout.addWidget(title)

        self._preview_title_label = QLabel(t("kb_preview_empty_title"))
        self._preview_title_label.setWordWrap(True)
        self._preview_title_label.setStyleSheet("font-size:18px; font-weight:700; color:#111111;")
        layout.addWidget(self._preview_title_label)

        self._preview_meta_label = QLabel(t("kb_preview_empty_body"))
        self._preview_meta_label.setWordWrap(True)
        self._preview_meta_label.setStyleSheet("color:#6b7280;")
        layout.addWidget(self._preview_meta_label)

        self._preview_text = QTextEdit()
        self._preview_text.setReadOnly(True)
        self._preview_text.setPlaceholderText(t("kb_preview_empty_body"))
        self._preview_text.setStyleSheet(
            "QTextEdit { background:#fcfbf8; border:1px solid #ece7dc; border-radius:18px; padding:14px; }"
        )
        layout.addWidget(self._preview_text, 1)
        return card

    def _api_headers(self) -> dict:
        headers = {"Accept": "application/json"}
        if BACKEND_BEARER_TOKEN:
            headers["Authorization"] = f"Bearer {BACKEND_BEARER_TOKEN}"
        return headers

    def _refresh_embedder_access(self) -> None:
        if self._embedder_url_label:
            self._embedder_url_label.setText(_embedder_url())
        if self._embedder_qr_label:
            pixmap = _render_qr_pixmap(_embedder_qr_payload(), size=150)
            if pixmap is not None:
                self._embedder_qr_label.setPixmap(pixmap)
                self._embedder_qr_label.setText("")
            else:
                self._embedder_qr_label.setPixmap(QPixmap())
                self._embedder_qr_label.setText(t("embedder_qr_missing"))
        self._check_embedder_status()

    def _set_embedder_status(self, online: bool) -> None:
        if not self._embedder_status_badge:
            return
        if online:
            self._embedder_status_badge.setText(f"●  {t('embedder_status_online')}")
            self._embedder_status_badge.setStyleSheet(
                "QLabel {"
                "  color:#15803d; background:#ecfdf5;"
                "  border:1px solid #bbf7d0; border-radius:13px;"
                "  padding:4px 14px; font-size:10px; font-weight:700;"
                "  letter-spacing:0.18em;"
                "}"
            )
        else:
            self._embedder_status_badge.setText(f"○  {t('embedder_status_offline')}")
            self._embedder_status_badge.setStyleSheet(
                "QLabel {"
                "  color:#6b7280; background:#f3f4f6;"
                "  border:1px solid #e5e7eb; border-radius:13px;"
                "  padding:4px 14px; font-size:10px; font-weight:700;"
                "  letter-spacing:0.18em;"
                "}"
            )

    def _check_embedder_status(self) -> None:
        try:
            resp = requests.head(
                f"{BACKEND_HTTP.rstrip('/')}/embedder/",
                timeout=1.5,
                allow_redirects=True,
            )
            self._set_embedder_status(resp.status_code < 400)
        except requests.RequestException:
            self._set_embedder_status(False)

    def _refresh_sync_state(self) -> None:
        if not BACKEND_BEARER_TOKEN:
            if self._sync_status_label:
                self._set_sync_status_badge("Failed", "#dc2626")
            return
        try:
            resp = requests.get(
                f"{BACKEND_HTTP}/api/v1/kennisbank/sync-state",
                headers=self._api_headers(),
                timeout=max(10, BACKEND_TIMEOUT),
            )
            resp.raise_for_status()
            data = resp.json()
            self._sync_state = data
            self._update_sync_labels(data)
            stats = data.get("stats") or {}
            qdrant = data.get("qdrant") if isinstance(data.get("qdrant"), dict) else data
            self._latest_stats = stats
            self._latest_qdrant = qdrant or {}
            self._update_stats_view(stats, qdrant)
            self._update_vector_view(stats, qdrant)
        except requests.RequestException as exc:
            if self._sync_status_label:
                self._set_sync_status_badge("Failed", "#dc2626")
            if self._sync_details_label:
                self._sync_details_label.setText(str(exc))

    def _refresh_library(self) -> None:
        if not BACKEND_BEARER_TOKEN:
            return
        try:
            resp = requests.get(
                f"{BACKEND_HTTP}/api/v1/kennisbank/library",
                headers=self._api_headers(),
                timeout=max(10, BACKEND_TIMEOUT),
            )
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as exc:
            show_error_dialog(self, t("kb_sync_error"), str(exc))
            return

        self._documents_data = data.get("documents", []) or []
        self._filtered_documents_data = list(self._documents_data)
        self._populate_documents_table()
        if self._latest_stats is not None or self._latest_qdrant is not None:
            self._update_vector_view(self._latest_stats, self._latest_qdrant)

    def _populate_documents_table(self) -> None:
        if not self._documents_table:
            return
        self._documents_table.setRowCount(len(self._filtered_documents_data))
        for row_idx, doc in enumerate(self._filtered_documents_data):
            values = [
                doc.get("title") or doc.get("doc_id") or "-",
                doc.get("category") or "-",
                str(doc.get("priority")) if doc.get("priority") is not None else "-",
                str(doc.get("chunk_count") or 0),
                doc.get("content_date") or "-",
            ]
            for col_idx, value in enumerate(values):
                item = QTableWidgetItem(value)
                if col_idx != 0:
                    item.setTextAlignment(Qt.AlignCenter)
                item.setData(Qt.UserRole, doc.get("doc_id"))
                self._documents_table.setItem(row_idx, col_idx, item)
        if self._filtered_documents_data:
            self._documents_table.selectRow(0)
            self._handle_document_selected(0, 0)
        else:
            self._update_preview_view(None)

    def _apply_documents_filter(self, value: str) -> None:
        query = (value or "").strip().lower()
        if not query:
            self._filtered_documents_data = list(self._documents_data)
        else:
            self._filtered_documents_data = [
                doc
                for doc in self._documents_data
                if query in (doc.get("title") or "").lower()
                or query in (doc.get("category") or "").lower()
                or query in (doc.get("doc_id") or "").lower()
                or query in str(doc.get("content_date") or "").lower()
            ]
        self._populate_documents_table()

    def _handle_document_selected(self, row: int, _column: int) -> None:
        if not (0 <= row < len(self._filtered_documents_data)):
            self._update_preview_view(None)
            return
        doc = self._filtered_documents_data[row]
        self._load_preview(doc)

    def _load_preview(self, doc: dict) -> None:
        doc_id = doc.get("doc_id")
        if not doc_id:
            self._update_preview_view(None)
            return
        if doc_id in self._preview_cache:
            self._update_preview_view(self._preview_cache[doc_id], doc)
            return
        try:
            resp = requests.get(
                f"{BACKEND_HTTP}/api/v1/kennisbank/library/documents/{doc_id}",
                headers=self._api_headers(),
                timeout=max(10, BACKEND_TIMEOUT),
            )
            resp.raise_for_status()
            payload = resp.json().get("document") or {}
            self._preview_cache[doc_id] = payload
            self._update_preview_view(payload, doc)
        except requests.RequestException:
            self._update_preview_view({}, doc)

    def _update_preview_view(self, detail: dict | None, doc: dict | None = None) -> None:
        if not self._preview_title_label or not self._preview_meta_label or not self._preview_text:
            return
        if not doc:
            self._preview_title_label.setText(t("kb_preview_empty_title"))
            self._preview_meta_label.setText(t("kb_preview_empty_body"))
            self._preview_text.setPlainText("")
            return

        title = detail.get("name") if detail else None
        self._preview_title_label.setText(title or doc.get("title") or doc.get("doc_id") or "-")

        meta_parts = []
        if doc.get("category"):
            meta_parts.append(str(doc["category"]))
        if doc.get("content_date"):
            meta_parts.append(str(doc["content_date"]))
        if doc.get("chunk_count") is not None:
            meta_parts.append(t("kb_preview_chunks", count=str(doc["chunk_count"])))
        self._preview_meta_label.setText(" • ".join(meta_parts) or t("kb_preview_empty_body"))

        text = self._extract_preview_text(detail or {})
        self._preview_text.setPlainText(text or t("kb_preview_unavailable"))

    def _extract_preview_text(self, detail: dict) -> str:
        parts: list[str] = []
        description = detail.get("description")
        if isinstance(description, str) and description.strip():
            parts.append(description.strip())

        for section in detail.get("hasPart") or []:
            if not isinstance(section, dict):
                continue
            name = section.get("name")
            text = section.get("text")
            if isinstance(name, str) and name.strip():
                parts.append(name.strip())
            if isinstance(text, str) and text.strip():
                parts.append(text.strip())
            if sum(len(p) for p in parts) > 3000:
                break

        article_section = detail.get("articleSection")
        if not parts and isinstance(article_section, str) and article_section.strip():
            parts.append(article_section.strip())

        preview = "\n\n".join(parts).strip()
        return preview[:4000]

    def _update_stats_view(self, stats: dict | None, qdrant: dict | None) -> None:
        doc_count = stats.get("document_count", 0) if stats else 0

        values = [
            (doc_count, t("kb_stat_documents_detail", count=str(doc_count))),
        ]

        for idx, (value, detail) in enumerate(values):
            if idx < len(self._stat_value_labels):
                self._stat_value_labels[idx].setText(f"{value:,}".replace(",", "."))
            if idx < len(self._stat_detail_labels):
                self._stat_detail_labels[idx].setText(detail)

        if self._actions_documents_value_label:
            self._actions_documents_value_label.setText(f"{doc_count:,}".replace(",", "."))
        if self._actions_documents_detail_label:
            self._actions_documents_detail_label.setText(
                t("kb_stat_documents_detail", count=str(doc_count))
            )

    def _update_vector_view(self, stats: dict | None, qdrant: dict | None) -> None:
        total_docs = max(
            len(self._documents_data),
            int((stats or {}).get("document_count") or 0),
            int((stats or {}).get("total_documents") or 0),
        )
        total_chunks = max(
            int((stats or {}).get("chunk_count") or 0),
            int((stats or {}).get("total_chunks") or 0),
            sum(int(doc.get("chunk_count") or 0) for doc in self._documents_data),
        )
        qdrant_size_bytes = self._directory_size(_knowledge_embedded_path())
        disk_total, disk_used, disk_free = self._disk_usage(_knowledge_embedded_path())
        model = (stats or {}).get("model", {}).get("model") if stats else None
        total_vectors = int((qdrant or {}).get("points") or 0)

        if len(self._vector_progress_bars) >= 2:
            storage_pct = int((disk_used / disk_total) * 100) if disk_total else 0
            possible_chunks = self._estimated_possible_units(qdrant_size_bytes, disk_free, total_chunks)
            embeddings_pct = int((total_chunks / possible_chunks) * 100) if possible_chunks else 0
            self._vector_progress_bars[0].setValue(max(0, min(100, storage_pct)))
            self._vector_progress_bars[1].setValue(max(0, min(100, embeddings_pct)))
        if len(self._vector_value_summary_labels) >= 2:
            self._vector_value_summary_labels[0].setText(
                f"{self._format_gb(disk_used)} / {self._format_gb(disk_total)}"
            )
            self._vector_value_summary_labels[1].setText(
                f"{total_chunks} / {self._estimated_possible_units(qdrant_size_bytes, disk_free, total_chunks)} chunks"
            )

        if self._sync_meta_label:
            self._sync_meta_label.setText(
                "".join(
                    [
                        '<div style="margin:8px 0;">• <b>'
                        f'{t("kb_total_vectors")}</b>: {total_vectors}</div>',
                        '<div style="margin:8px 0;">• <b>'
                        f'{t("kb_embedding_model")}</b>: {model or "-"}</div>',
                        '<div style="margin:8px 0;">• <b>'
                        f'{t("kb_database_engine")}</b>: {"Qdrant (embedded)" if not os.getenv("QDRANT_HOST") else "Qdrant (remote)"}</div>',
                        '<div style="margin:8px 0 16px 0;">• <b>'
                        f'{t("kb_index_status")}</b>: {t("kb_optimal") if total_vectors else t("kb_sync_pending")}</div>',
                    ]
                )
            )

    def _directory_size(self, path: Path) -> int:
        if not path.exists():
            return 0
        total = 0
        for entry in path.rglob("*"):
            if entry.is_file():
                try:
                    total += entry.stat().st_size
                except OSError:
                    continue
        return total

    def _disk_usage(self, path: Path) -> tuple[int, int, int]:
        target = path if path.exists() else Path.cwd()
        usage = shutil.disk_usage(target)
        return usage.total, usage.used, usage.free

    def _format_gb(self, value: int) -> str:
        return f"{value / (1024 ** 3):.1f}GB"

    def _estimated_possible_units(self, qdrant_size_bytes: int, disk_free: int, current_units: int) -> int:
        if current_units <= 0:
            return 0
        if qdrant_size_bytes <= 0:
            return current_units
        estimated = int((disk_free / qdrant_size_bytes) * current_units)
        return max(current_units, estimated)

    def _update_sync_labels(self, data: dict) -> None:
        if not self._sync_status_label or not self._sync_details_label or not self._sync_meta_label:
            return

        if not data.get("synced"):
            self._set_sync_status_badge("Failed", "#dc2626")
            self._sync_details_label.setText("")
            self._sync_meta_label.setText("")
            return

        synced_at = data.get("synced_at")
        self._set_sync_status_badge("Success", "#16a34a")
        self._sync_details_label.setText(self._format_timestamp(synced_at) if synced_at else "")

    def _set_sync_status_badge(self, label: str, color: str) -> None:
        if not self._sync_status_label:
            return
        self._sync_status_label.setText(
            f'Sync Status - <span style="color:{color};">●</span> {label}'
        )

    def _format_timestamp(self, value: str) -> str:
        try:
            normalized = value.replace("Z", "+00:00")
            dt = datetime.fromisoformat(normalized)
        except ValueError:
            return value
        local_dt = dt.astimezone()
        return local_dt.strftime("%d %b %Y %H:%M")

    def on_page_shown(self) -> None:
        # main.py roept dit aan wanneer de tab opent. We hebben geen handmatige
        # sync-knop meer (de embedder pusht over LAN); deze hook is hoe de UI
        # zich up-to-date houdt zonder polling.
        self._refresh_sync_state()
        self._refresh_library()
        self._refresh_embedder_access()

    def _handle_refresh_clicked(self) -> None:
        # Disable de knop tijdens de blocking HTTP-calls zodat de user niet
        # twee keer klikt; Qt verwerkt events pas weer als we hieruit terug zijn.
        if self._documents_refresh_button:
            self._documents_refresh_button.setEnabled(False)
        try:
            self._refresh_sync_state()
            self._refresh_library()
        finally:
            if self._documents_refresh_button:
                self._documents_refresh_button.setEnabled(True)
