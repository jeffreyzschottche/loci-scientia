import webbrowser
from datetime import datetime

import requests
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QProgressBar,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QHeaderView,
)

from ..config import BACKEND_BEARER_TOKEN, BACKEND_HTTP, BACKEND_TIMEOUT
from ..translations import t, register_language_change_callback
from .dialog_style import show_error_dialog


class KnowledgePage(QWidget):
    def __init__(self):
        super().__init__()
        self._main_layout = QVBoxLayout(self)
        self._main_layout.setContentsMargins(16, 16, 16, 16)
        self._main_layout.setSpacing(16)

        # Store references to all translatable widgets
        self._stat_title_labels = []
        self._stat_detail_labels = []
        self._stat_value_labels = []
        self._vector_title_label = None
        self._vector_entry_labels = []
        self._vector_value_labels = []
        self._documents_title_label = None
        self._documents_table = None
        self._sync_status_label = None
        self._sync_details_label = None
        self._sync_button = None
        self._sync_state: dict | None = None

        header = QHBoxLayout()
        header.addStretch(1)

        self._upload_btn = self._pill_button(t("kb_upload_document"), primary=True)
        self._upload_btn.clicked.connect(self._open_upload_portal)
        header.addWidget(self._upload_btn, 0, Qt.AlignRight)
        self._main_layout.addLayout(header)

        self._main_layout.addWidget(self._sync_status_card())
        self._main_layout.addLayout(self._stats_grid())
        self._main_layout.addWidget(self._vector_status_card())
        self._main_layout.addWidget(self._documents_table_widget())

        self._refresh_sync_state()
        register_language_change_callback(self._update_translations)

    def _update_translations(self) -> None:
        """Update UI elements when language changes."""
        self._upload_btn.setText(t("kb_upload_document"))
        if self._sync_button:
            label = (
                t("kb_syncing")
                if self._sync_button.property("syncing")
                else t("kb_sync_button")
            )
            self._sync_button.setText(label)

        # Update stats grid
        stat_titles = [
            t("kb_sd_card_capacity"),
            t("kb_knowledge_bank_size"),
            t("kb_total_documents"),
        ]
        stat_details = [
            t("kb_used", used="48.2", percent="18.8"),
            t("kb_available", available="207.8"),
            t("kb_indexed", count="2"),
        ]
        for i, label in enumerate(self._stat_title_labels):
            if i < len(stat_titles):
                label.setText(stat_titles[i].upper())
        for i, label in enumerate(self._stat_detail_labels):
            if i < len(stat_details):
                label.setText(stat_details[i])

        # Update vector status card
        if self._vector_title_label:
            self._vector_title_label.setText(t("kb_vector_db_title"))

        vector_labels = [
            t("kb_total_vectors"),
            t("kb_embedding_model"),
            t("kb_database_engine"),
            t("kb_index_status"),
        ]
        for i, label in enumerate(self._vector_entry_labels):
            if i < len(vector_labels):
                label.setText(vector_labels[i].upper())

        # Update the "Optimal" value which is also translated
        if len(self._vector_value_labels) >= 4:
            self._vector_value_labels[3].setText(t("kb_optimal"))

        # Update documents table
        if self._documents_title_label:
            self._documents_title_label.setText(t("kb_documents"))

        if self._documents_table:
            self._documents_table.setHorizontalHeaderLabels([
                t("kb_table_document"),
                t("kb_table_type"),
                t("kb_table_size"),
                t("kb_table_status"),
                t("kb_table_vectors"),
                t("kb_table_upload_date"),
            ])
            # Update status column (column 3)
            status_values = [
                t("kb_status_indexed"),
                t("kb_status_indexed"),
                t("kb_status_processing"),
            ]
            for row_idx, status in enumerate(status_values):
                    item = self._documents_table.item(row_idx, 3)
                    if item:
                        item.setText(status)
        if self._sync_status_label and self._sync_state:
            self._update_sync_labels(self._sync_state)

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
        self._sync_button.setProperty("syncing", False)
        header.addWidget(self._sync_button, 0, Qt.AlignRight)
        layout.addLayout(header)

        self._sync_status_label = QLabel(t("kb_sync_never"))
        self._sync_status_label.setStyleSheet("font-size:22px; font-weight:700; color:#111111;")
        layout.addWidget(self._sync_status_label)

        self._sync_details_label = QLabel("")
        self._sync_details_label.setStyleSheet("color:#4b5563;")
        layout.addWidget(self._sync_details_label)

        if not BACKEND_BEARER_TOKEN:
            self._sync_button.setEnabled(False)
            self._sync_details_label.setText(t("kb_sync_error"))

        return card

    @staticmethod
    def _open_upload_portal() -> None:
        webbrowser.open("https://www.aitje.jeffrai.nl")

    def _api_headers(self) -> dict:
        headers = {"Accept": "application/json"}
        if BACKEND_BEARER_TOKEN:
            headers["Authorization"] = f"Bearer {BACKEND_BEARER_TOKEN}"
        return headers

    def _refresh_sync_state(self) -> None:
        if not BACKEND_BEARER_TOKEN or not self._sync_status_label:
            return
        try:
            resp = requests.get(
                f"{BACKEND_HTTP}/api/v1/kennisbank/sync-state",
                headers=self._api_headers(),
                timeout=BACKEND_TIMEOUT,
            )
            resp.raise_for_status()
            state = resp.json()
        except requests.RequestException as exc:
            self._sync_status_label.setText(t("kb_sync_error"))
            if self._sync_details_label:
                self._sync_details_label.setText(str(exc))
            return
        self._sync_state = state
        self._update_sync_labels(state)

    def _update_sync_labels(self, state: dict) -> None:
        if not self._sync_status_label or not self._sync_details_label:
            return
        synced_at = state.get("synced_at")
        stats = state.get("stats") or {}
        if synced_at:
            timestamp = self._format_timestamp(synced_at)
            self._sync_status_label.setText(t("kb_sync_success"))
            detail = f"{t('kb_sync_last')}: {timestamp}"
        else:
            self._sync_status_label.setText(t("kb_sync_never"))
            detail = t("kb_sync_never")
        doc_count = stats.get("document_count")
        chunk_count = stats.get("chunk_count")
        if doc_count is not None and chunk_count is not None:
            detail += f" • {doc_count} docs / {chunk_count} chunks"
        self._sync_details_label.setText(detail)

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
            show_error_dialog(self, t("kb_sync_error"), "Geen admin-token ingesteld.")
            return
        if not self._sync_button:
            return
        self._sync_button.setEnabled(False)
        self._sync_button.setProperty("syncing", True)
        self._sync_button.setText(t("kb_syncing"))
        try:
            resp = requests.post(
                f"{BACKEND_HTTP}/api/v1/kennisbank/sync",
                headers=self._api_headers(),
                timeout=max(BACKEND_TIMEOUT, 60),
            )
            resp.raise_for_status()
            data = resp.json()
            self._sync_state = data
            self._update_sync_labels(data)
        except requests.RequestException as exc:
            if self._sync_status_label:
                self._sync_status_label.setText(t("kb_sync_error"))
            if self._sync_details_label:
                self._sync_details_label.setText(str(exc))
            show_error_dialog(self, t("kb_sync_error"), str(exc))
        finally:
            self._sync_button.setEnabled(True)
            self._sync_button.setProperty("syncing", False)
            self._sync_button.setText(t("kb_sync_button"))

    def _stats_grid(self) -> QGridLayout:
        stats = [
            {
                "title": t("kb_sd_card_capacity"),
                "value": "256 GB",
                "detail": t("kb_used", used="48.2", percent="18.8"),
                "progress": 19,
            },
            {
                "title": t("kb_knowledge_bank_size"),
                "value": "12.4 GB",
                "detail": t("kb_available", available="207.8"),
                "progress": 6,
            },
            {
                "title": t("kb_total_documents"),
                "value": "3",
                "detail": t("kb_indexed", count="2"),
                "progress": None,
            },
        ]
        grid = QGridLayout()
        grid.setSpacing(12)
        for idx, stat in enumerate(stats):
            card = QFrame()
            card.setObjectName("Card")
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(16, 16, 16, 16)
            label = QLabel(stat["title"].upper())
            label.setStyleSheet(
                "color:#6b7280; letter-spacing:0.35em; font-size:11px;"
            )
            self._stat_title_labels.append(label)
            value = QLabel(stat["value"])
            value.setStyleSheet("font-size:28px; font-weight:700; color:#111111;")
            card_layout.addWidget(label)
            card_layout.addWidget(value)
            if stat["progress"] is not None:
                bar = QProgressBar()
                bar.setRange(0, 100)
                bar.setValue(stat["progress"])
                bar.setFixedHeight(16)
                bar.setStyleSheet(
                    "QProgressBar {"
                    "  border:1px solid #facc15;"
                    "  border-radius:8px;"
                    "  background:#fefce8;"
                    "}"
                    "QProgressBar::chunk {"
                    "  background-color:#facc15;"
                    "  border-radius:8px;"
                    "}"
                )
                card_layout.addWidget(bar)
            detail = QLabel(stat["detail"])
            detail.setStyleSheet("color:#4b5563;")
            self._stat_detail_labels.append(detail)
            card_layout.addWidget(detail)
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
            (t("kb_total_vectors"), "2.130"),
            (t("kb_embedding_model"), "all-MiniLM-L6-v2"),
            (t("kb_database_engine"), "ChromaDB"),
            (t("kb_index_status"), t("kb_optimal")),
        ]
        for idx, (label_text, value) in enumerate(entries):
            lbl = QLabel(label_text.upper())
            lbl.setStyleSheet(
                "color:#6b7280; letter-spacing:0.3em; font-size:11px;"
            )
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
        self._documents_table.setHorizontalHeaderLabels([
            t("kb_table_document"),
            t("kb_table_type"),
            t("kb_table_size"),
            t("kb_table_status"),
            t("kb_table_vectors"),
            t("kb_table_upload_date"),
        ])
        self._documents_table.verticalHeader().setVisible(False)
        self._documents_table.setShowGrid(False)
        self._documents_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._documents_table.setSelectionMode(QTableWidget.NoSelection)
        self._documents_table.setAlternatingRowColors(False)
        self._documents_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        rows = [
            (
                "Technische Handleiding.pdf",
                "PDF",
                "2.4 MB",
                t("kb_status_indexed"),
                "1.240",
                "2025-10-28",
            ),
            (
                "Product Specificaties.pdf",
                "PDF",
                "1.8 MB",
                t("kb_status_indexed"),
                "890",
                "2025-10-27",
            ),
            (
                "FAQ Document.docx",
                "DOCX",
                "456 KB",
                t("kb_status_processing"),
                "-",
                "2025-11-01",
            ),
        ]
        self._documents_table.setRowCount(len(rows))
        for row_idx, row in enumerate(rows):
            for col_idx, value in enumerate(row):
                item = QTableWidgetItem(value)
                self._documents_table.setItem(row_idx, col_idx, item)
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
