from __future__ import annotations

import json
import os
import threading
from datetime import datetime
from queue import Queue, Empty

import requests
from PySide6.QtCore import Qt, QTimer, Signal, QObject
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QProgressBar,
    QProgressDialog,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QHeaderView,
)

from ..config import BACKEND_BEARER_TOKEN, BACKEND_HTTP, BACKEND_TIMEOUT
from ..translations import t, register_language_change_callback
from .dialog_style import OverlayDialog, show_error_dialog


class SyncProgressDialog(QDialog):
    """Progress dialog voor kennisbank sync met SSE streaming."""

    progress_updated = Signal(int, str)
    sync_finished = Signal(dict)
    sync_error = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(t("kb_syncing"))
        self.setModal(True)
        self.setFixedSize(400, 150)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        self._status_label = QLabel(t("kb_sync_starting"))
        self._status_label.setStyleSheet("font-size: 14px; font-weight: 600;")
        layout.addWidget(self._status_label)

        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        self._progress_bar.setTextVisible(True)
        self._progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #e5e7eb;
                border-radius: 8px;
                background: #f3f4f6;
                height: 24px;
                text-align: center;
            }
            QProgressBar::chunk {
                background: #facc15;
                border-radius: 7px;
            }
        """)
        layout.addWidget(self._progress_bar)

        self._detail_label = QLabel("")
        self._detail_label.setStyleSheet("color: #6b7280; font-size: 12px;")
        layout.addWidget(self._detail_label)

        # Connect signals
        self.progress_updated.connect(self._on_progress)
        self.sync_finished.connect(self._on_finished)
        self.sync_error.connect(self._on_error)

        self._result = None
        self._error = None

    def _on_progress(self, progress: int, status: str):
        self._progress_bar.setValue(progress)
        self._status_label.setText(status)

    def _on_finished(self, result: dict):
        self._result = result
        self.accept()

    def _on_error(self, error: str):
        self._error = error
        self.reject()

    def start_sync(self):
        """Start de sync in een background thread."""
        thread = threading.Thread(target=self._run_sync, daemon=True)
        thread.start()

    def _run_sync(self):
        """Voer de sync uit en stream progress updates."""
        headers = {"Accept": "text/event-stream"}
        if BACKEND_BEARER_TOKEN:
            headers["Authorization"] = f"Bearer {BACKEND_BEARER_TOKEN}"

        try:
            with requests.post(
                f"{BACKEND_HTTP}/api/v1/kennisbank/sync/stream",
                headers=headers,
                stream=True,
                timeout=600,  # 10 minuten timeout
            ) as resp:
                resp.raise_for_status()
                for line in resp.iter_lines(decode_unicode=True):
                    if not line or not line.startswith("data: "):
                        continue
                    try:
                        data = json.loads(line[6:])  # Strip "data: " prefix
                    except json.JSONDecodeError:
                        continue

                    if "error" in data:
                        self.sync_error.emit(data["error"])
                        return

                    if data.get("done"):
                        self.sync_finished.emit(data)
                        return

                    progress = data.get("progress", 0)
                    status = data.get("status", "")
                    self.progress_updated.emit(progress, status)

        except requests.RequestException as exc:
            self.sync_error.emit(str(exc))


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
        self._vector_value_labels: list[QLabel] = []
        self._documents_title_label: QLabel | None = None
        self._documents_table: QTableWidget | None = None
        self._relations_table: QTableWidget | None = None
        self._relations_empty_label: QLabel | None = None
        self._relations_doc_label: QLabel | None = None
        self._sync_button: QPushButton | None = None
        self._sync_status_label: QLabel | None = None
        self._sync_details_label: QLabel | None = None

        self._documents_data: list[dict] = []
        self._relations_map: dict[str, list[dict]] = {}
        self._sync_state: dict | None = None

        header = QHBoxLayout()
        header.addStretch(1)
        self._upload_btn = self._pill_button(t("kb_upload_document"), primary=True)
        self._upload_btn.clicked.connect(self._show_upload_instructions)
        header.addWidget(self._upload_btn, 0, Qt.AlignRight)
        self._main_layout.addLayout(header)

        self._main_layout.addWidget(self._sync_status_card())
        self._main_layout.addLayout(self._stats_grid())
        self._main_layout.addWidget(self._vector_status_card())
        self._main_layout.addWidget(self._documents_table_widget())
        self._main_layout.addWidget(self._relations_card())

        self._refresh_sync_state()
        self._refresh_library()
        register_language_change_callback(self._update_translations)

    def _update_translations(self) -> None:
        self._upload_btn.setText(t("kb_upload_document"))
        if self._sync_button:
            self._sync_button.setText(t("kb_sync_button"))
        if self._sync_status_label and self._sync_state:
            self._update_sync_labels(self._sync_state)

        stat_titles = [
            t("kb_stat_documents"),
            t("kb_stat_chunks"),
            t("kb_stat_vectors"),
        ]
        for idx, label in enumerate(self._stat_title_labels):
            if idx < len(stat_titles):
                label.setText(stat_titles[idx].upper())

        if self._vector_title_label:
            self._vector_title_label.setText(t("kb_vector_db_title"))
        vector_labels = [
            t("kb_total_vectors"),
            t("kb_embedding_model"),
            t("kb_database_engine"),
            t("kb_index_status"),
        ]
        for idx, label in enumerate(self._vector_entry_labels):
            if idx < len(vector_labels):
                label.setText(vector_labels[idx].upper())

        if len(self._vector_value_labels) >= 4:
            self._vector_value_labels[3].setText(t("kb_optimal"))

        if self._documents_title_label:
            self._documents_title_label.setText(t("kb_documents"))
        if self._documents_table:
            self._documents_table.setHorizontalHeaderLabels(
                [
                    t("kb_table_document"),
                    t("kb_table_category"),
                    t("kb_table_priority"),
                    t("kb_table_chunks"),
                    t("kb_table_content_date"),
                    t("kb_table_relations"),
                ]
            )

        if self._relations_doc_label:
            self._relations_doc_label.setText(t("kb_relations_title"))
        if self._relations_table:
            self._relations_table.setHorizontalHeaderLabels(
                [
                    t("kb_relations_target"),
                    t("kb_relations_type"),
                ]
            )
        if self._relations_empty_label:
            self._relations_empty_label.setText(t("kb_relations_none"))

    def _pill_button(self, text: str, primary: bool = False) -> QPushButton:
        btn = QPushButton(text)
        btn.setCursor(Qt.PointingHandCursor)
        if primary:
            btn.setStyleSheet(
                "QPushButton {"
                "  background:#facc15;"
                "  color:#050505;"
                "  border-radius:20px;"
                "  padding:10px 28px;"
                "  font-weight:600;"
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
                "}"
                "QPushButton:hover { border-color:rgba(33,33,33,0.45); }"
            )
        btn.setFixedHeight(40)
        return btn

    def _show_upload_instructions(self) -> None:
        dialog = OverlayDialog(self)
        dialog.setWindowTitle(t("kb_upload_popup_title"))

        badge = QLabel(t("kb_upload_popup_badge"))
        badge.setStyleSheet(
            "font-size:11px; font-weight:700; letter-spacing:0.18em; color:#6b7280;"
        )
        dialog.card_layout.addWidget(badge)

        title = QLabel(t("kb_upload_popup_title"))
        title.setWordWrap(True)
        title.setStyleSheet("font-size:24px; font-weight:800; color:#111111;")
        dialog.card_layout.addWidget(title)

        body = QLabel(t("kb_upload_popup_body"))
        body.setWordWrap(True)
        body.setTextInteractionFlags(Qt.TextSelectableByMouse)
        body.setStyleSheet("font-size:15px; font-weight:500; line-height:1.55; color:#374151;")
        dialog.card_layout.addWidget(body)

        url_label = QLabel("kennisbank.aitje.com")
        url_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        url_label.setStyleSheet(
            "background:#f9fafb; border:1px solid #e5e7eb; border-radius:18px; "
            "padding:14px 16px; font-size:16px; font-weight:700; color:#111111;"
        )
        dialog.card_layout.addWidget(url_label)

        dialog.card_layout.addStretch(1)

        actions = QHBoxLayout()
        actions.setSpacing(12)

        close_btn = QPushButton(t("close"))
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet(
            "QPushButton {"
            "  background:#ffffff;"
            "  color:#111111;"
            "  border:1px solid #e5e7eb;"
            "  border-radius:18px;"
            "  padding:8px 18px;"
            "  font-weight:600;"
            "  min-height:36px;"
            "}"
            "QPushButton:hover { background:#f9fafb; border-color:#d1d5db; }"
        )
        close_btn.clicked.connect(dialog.reject)

        actions.addStretch(1)
        actions.addWidget(close_btn)
        dialog.card_layout.addLayout(actions)
        dialog.exec()

    def _sync_status_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("Card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 16, 16, 16)

        header = QHBoxLayout()
        title = QLabel(t("kb_sync_last").upper())
        title.setStyleSheet("color:#6b7280; letter-spacing:0.35em; font-size:11px;")
        header.addWidget(title, 1)
        self._sync_button = self._pill_button(t("kb_sync_button"), primary=True)
        self._sync_button.clicked.connect(self._trigger_sync)
        header.addWidget(self._sync_button, 0, Qt.AlignRight)
        layout.addLayout(header)

        self._sync_status_label = QLabel(t("kb_sync_never"))
        self._sync_status_label.setStyleSheet("font-size:22px; font-weight:700; color:#111111;")
        layout.addWidget(self._sync_status_label)

        self._sync_details_label = QLabel("")
        self._sync_details_label.setStyleSheet("color:#4b5563;")
        layout.addWidget(self._sync_details_label)
        return card

    def _stats_grid(self) -> QGridLayout:
        grid = QGridLayout()
        grid.setSpacing(12)
        placeholders = [
            (t("kb_stat_documents"), "0", t("kb_stat_documents_detail", count="0")),
            (t("kb_stat_chunks"), "0", t("kb_stat_chunks_detail", count="0")),
            (t("kb_stat_vectors"), "0", t("kb_stat_vectors_detail", count="0")),
        ]
        for idx, (title, value, detail) in enumerate(placeholders):
            card = QFrame()
            card.setObjectName("Card")
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(16, 16, 16, 16)

            title_label = QLabel(title.upper())
            title_label.setStyleSheet("color:#6b7280; letter-spacing:0.35em; font-size:11px;")
            self._stat_title_labels.append(title_label)
            card_layout.addWidget(title_label)

            value_label = QLabel(value)
            value_label.setStyleSheet("font-size:28px; font-weight:700; color:#111111;")
            self._stat_value_labels.append(value_label)
            card_layout.addWidget(value_label)

            detail_label = QLabel(detail)
            detail_label.setStyleSheet("color:#4b5563;")
            self._stat_detail_labels.append(detail_label)
            card_layout.addWidget(detail_label)
            grid.addWidget(card, 0, idx)
        return grid

    def _vector_status_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("Card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 16, 16, 16)
        self._vector_title_label = QLabel(t("kb_vector_db_title"))
        self._vector_title_label.setStyleSheet("font-size:20px; font-weight:700; letter-spacing:0.02em;")
        layout.addWidget(self._vector_title_label)

        meta_grid = QGridLayout()
        meta_grid.setSpacing(12)
        entries = [
            (t("kb_total_vectors"), "0"),
            (t("kb_embedding_model"), "-"),
            (t("kb_database_engine"), "Qdrant"),
            (t("kb_index_status"), t("kb_optimal")),
        ]
        for idx, (label_text, value) in enumerate(entries):
            lbl = QLabel(label_text.upper())
            lbl.setStyleSheet("color:#6b7280; letter-spacing:0.3em; font-size:11px;")
            self._vector_entry_labels.append(lbl)
            val = QLabel(value)
            val.setStyleSheet("font-weight:600; color:#111111;")
            self._vector_value_labels.append(val)
            meta_grid.addWidget(lbl, 0, idx)
            meta_grid.addWidget(val, 1, idx)
        layout.addLayout(meta_grid)
        return card

    def _documents_table_widget(self) -> QFrame:
        card = QFrame()
        card.setObjectName("Card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(0, 0, 0, 0)

        self._documents_title_label = QLabel(t("kb_documents"))
        self._documents_title_label.setStyleSheet(
            "font-size:20px; font-weight:700; padding:16px; letter-spacing:0.02em;"
        )
        card_layout.addWidget(self._documents_title_label)

        self._documents_table = QTableWidget()
        self._documents_table.setColumnCount(6)
        self._documents_table.setHorizontalHeaderLabels(
            [
                t("kb_table_document"),
                t("kb_table_category"),
                t("kb_table_priority"),
                t("kb_table_chunks"),
                t("kb_table_content_date"),
                t("kb_table_relations"),
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

        header = self._documents_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        header.setStyleSheet(
            "QHeaderView::section { background:#ffffff; color:#111111; border:0; font-weight:600; }"
        )
        self._documents_table.setStyleSheet(
            "QTableWidget { background:#ffffff; border:0; }"
            "QTableWidget::item { border-bottom:1px solid #f4f4f5; }"
        )
        card_layout.addWidget(self._documents_table)
        return card

    def _relations_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("Card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 16, 16, 16)

        self._relations_doc_label = QLabel(t("kb_relations_title"))
        self._relations_doc_label.setStyleSheet("font-size:20px; font-weight:700; letter-spacing:0.02em;")
        layout.addWidget(self._relations_doc_label)

        self._relations_table = QTableWidget()
        self._relations_table.setColumnCount(2)
        self._relations_table.setHorizontalHeaderLabels(
            [
                t("kb_relations_target"),
                t("kb_relations_type"),
            ]
        )
        self._relations_table.verticalHeader().setVisible(False)
        self._relations_table.setShowGrid(False)
        self._relations_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._relations_table.setSelectionMode(QTableWidget.NoSelection)
        header = self._relations_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        header.setStyleSheet(
            "QHeaderView::section { background:#ffffff; color:#111111; border:0; font-weight:600; }"
        )
        self._relations_table.setStyleSheet(
            "QTableWidget { background:#ffffff; border:0; }"
            "QTableWidget::item { border-bottom:1px solid #f4f4f5; }"
        )
        layout.addWidget(self._relations_table)

        self._relations_empty_label = QLabel(t("kb_relations_none"))
        self._relations_empty_label.setAlignment(Qt.AlignCenter)
        self._relations_empty_label.setStyleSheet("color:#6b7280; padding:16px;")
        layout.addWidget(self._relations_empty_label)
        self._relations_table.hide()
        return card

    def _api_headers(self) -> dict:
        headers = {"Accept": "application/json"}
        if BACKEND_BEARER_TOKEN:
            headers["Authorization"] = f"Bearer {BACKEND_BEARER_TOKEN}"
        return headers

    def _refresh_sync_state(self) -> None:
        if not BACKEND_BEARER_TOKEN:
            if self._sync_status_label:
                self._sync_status_label.setText(t("kb_sync_need_token"))
            if self._sync_button:
                self._sync_button.setEnabled(False)
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
            self._update_stats_view(stats, data.get("qdrant"))
            self._update_vector_view(stats, data.get("qdrant"))
        except requests.RequestException as exc:
            if self._sync_status_label:
                self._sync_status_label.setText(t("kb_sync_error"))
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
        self._relations_map = data.get("relations", {}) or {}
        self._populate_documents_table()

    def _populate_documents_table(self) -> None:
        if not self._documents_table:
            return
        self._documents_table.setRowCount(len(self._documents_data))
        for row_idx, doc in enumerate(self._documents_data):
            relations = len(self._relations_map.get(doc.get("doc_id", ""), []))
            values = [
                doc.get("title") or doc.get("doc_id") or "-",
                doc.get("category") or "-",
                str(doc.get("priority")) if doc.get("priority") is not None else "-",
                str(doc.get("chunk_count") or 0),
                doc.get("content_date") or "-",
                str(relations),
            ]
            for col_idx, value in enumerate(values):
                item = QTableWidgetItem(value)
                if col_idx != 0:
                    item.setTextAlignment(Qt.AlignCenter)
                item.setData(Qt.UserRole, doc.get("doc_id"))
                self._documents_table.setItem(row_idx, col_idx, item)
        if self._documents_data:
            self._documents_table.selectRow(0)
            self._handle_document_selected(0, 0)
        else:
            self._update_relations_view(None)

    def _handle_document_selected(self, row: int, _column: int) -> None:
        if not (0 <= row < len(self._documents_data)):
            self._update_relations_view(None)
            return
        doc = self._documents_data[row]
        self._update_relations_view(doc.get("doc_id"), doc.get("title"))

    def _update_relations_view(self, doc_id: str | None, title: str | None = None) -> None:
        if not self._relations_table or not self._relations_doc_label:
            return

        if not doc_id:
            self._relations_doc_label.setText(t("kb_relations_title"))
            self._relations_table.hide()
            if self._relations_empty_label:
                self._relations_empty_label.setText(t("kb_relations_none"))
                self._relations_empty_label.show()
            return

        relations = self._relations_map.get(doc_id, [])
        display_title = title or doc_id
        self._relations_doc_label.setText(
            t("kb_relations_for", document=display_title)
        )

        if not relations:
            self._relations_table.hide()
            if self._relations_empty_label:
                self._relations_empty_label.setText(t("kb_relations_none"))
                self._relations_empty_label.show()
            return

        self._relations_table.setRowCount(len(relations))
        for idx, relation in enumerate(relations):
            target = relation.get("target") or "-"
            rel_type = relation.get("relationship") or "-"
            target_item = QTableWidgetItem(target)
            rel_item = QTableWidgetItem(rel_type)
            self._relations_table.setItem(idx, 0, target_item)
            rel_item.setTextAlignment(Qt.AlignCenter)
            self._relations_table.setItem(idx, 1, rel_item)
        self._relations_table.show()
        if self._relations_empty_label:
            self._relations_empty_label.hide()

    def _update_stats_view(self, stats: dict | None, qdrant: dict | None) -> None:
        doc_count = stats.get("document_count", 0) if stats else 0
        chunk_count = stats.get("chunk_count", 0) if stats else 0
        vector_count = (qdrant or {}).get("points", 0) or 0

        values = [
            (doc_count, t("kb_stat_documents_detail", count=str(doc_count))),
            (chunk_count, t("kb_stat_chunks_detail", count=str(chunk_count))),
            (vector_count, t("kb_stat_vectors_detail", count=str(vector_count))),
        ]

        for idx, (value, detail) in enumerate(values):
            if idx < len(self._stat_value_labels):
                self._stat_value_labels[idx].setText(f"{value:,}".replace(",", "."))
            if idx < len(self._stat_detail_labels):
                self._stat_detail_labels[idx].setText(detail)

    def _update_vector_view(self, stats: dict | None, qdrant: dict | None) -> None:
        if len(self._vector_value_labels) < 4:
            return
        self._vector_value_labels[0].setText(
            str((qdrant or {}).get("points") or 0)
        )
        model = (stats or {}).get("model", {}).get("model") if stats else None
        self._vector_value_labels[1].setText(model or "-")
        storage = "Qdrant (embedded)" if not os.getenv("QDRANT_HOST") else "Qdrant (remote)"
        self._vector_value_labels[2].setText(storage)
        self._vector_value_labels[3].setText(
            t("kb_optimal") if (qdrant or {}).get("points") else t("kb_sync_pending")
        )

    def _update_sync_labels(self, data: dict) -> None:
        if not self._sync_status_label or not self._sync_details_label:
            return

        if not data.get("synced"):
            self._sync_status_label.setText(t("kb_sync_never"))
            self._sync_details_label.setText("")
            return

        synced_at = data.get("synced_at")
        git_action = (data.get("git") or {}).get("action")
        qdrant_points = (data.get("qdrant") or {}).get("points")
        detail = []
        if synced_at:
            detail.append(self._format_timestamp(synced_at))
        if git_action:
            detail.append(f"git: {git_action}")
        if qdrant_points is not None:
            detail.append(f"vectors: {qdrant_points}")

        self._sync_status_label.setText(t("kb_sync_success"))
        self._sync_details_label.setText(" • ".join(detail))

    def _format_timestamp(self, value: str) -> str:
        try:
            normalized = value.replace("Z", "+00:00")
            dt = datetime.fromisoformat(normalized)
        except ValueError:
            return value
        local_dt = dt.astimezone()
        return local_dt.strftime("%d %b %Y %H:%M")

    def _trigger_sync(self) -> None:
        if not BACKEND_BEARER_TOKEN:
            show_error_dialog(self, t("kb_sync_error"), t("kb_sync_need_token"))
            return
        if not self._sync_button:
            return

        # Open progress dialog
        dialog = SyncProgressDialog(self)
        dialog.start_sync()
        result = dialog.exec()

        if result == QDialog.Accepted and dialog._result:
            data = dialog._result
            self._sync_state = data
            self._update_sync_labels(data)
            stats = data.get("stats") or {}
            self._update_stats_view(stats, data.get("qdrant"))
            self._update_vector_view(stats, data.get("qdrant"))
            self._refresh_library()
        elif dialog._error:
            show_error_dialog(self, t("kb_sync_error"), dialog._error)
