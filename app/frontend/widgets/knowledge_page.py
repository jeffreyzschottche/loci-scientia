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
)


class KnowledgePage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        header = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel("Kennisbank")
        title.setStyleSheet("font-size:18px; font-weight:600;")
        subtitle = QLabel("Beheer kennisbank documenten en SD kaart opslag")
        subtitle.setStyleSheet("color:#9ca3af;")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        header.addLayout(title_box, 1)

        refresh = self._pill_button("⟳ Sync Google Drive")
        upload = self._pill_button("⬆ Upload Document", primary=True)
        header.addWidget(refresh, 0, Qt.AlignRight)
        header.addWidget(upload, 0, Qt.AlignRight)
        layout.addLayout(header)

        layout.addLayout(self._stats_grid())
        layout.addWidget(self._vector_status_card())
        layout.addWidget(self._documents_table())

    @staticmethod
    def _pill_button(text: str, primary: bool = False) -> QPushButton:
        btn = QPushButton(text)
        btn.setCursor(Qt.PointingHandCursor)
        if primary:
            btn.setStyleSheet(
                "background:#2563eb; color:white; border-radius:8px; padding:8px 16px;"
            )
        else:
            btn.setStyleSheet(
                "background:transparent; border:1px solid #374151; "
                "color:white; border-radius:8px; padding:8px 16px;"
            )
        return btn

    def _stats_grid(self) -> QGridLayout:
        stats = [
            {
                "title": "SD Kaart Capaciteit",
                "value": "256 GB",
                "detail": "48.2 GB gebruikt (18.8%)",
                "progress": 19,
            },
            {
                "title": "Kennisbank Grootte",
                "value": "12.4 GB",
                "detail": "Beschikbaar: 207.8 GB",
                "progress": 6,
            },
            {
                "title": "Totaal Documenten",
                "value": "3",
                "detail": "2 geïndexeerd",
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
            label = QLabel(stat["title"])
            label.setStyleSheet("color:#9ca3af;")
            value = QLabel(stat["value"])
            value.setStyleSheet("font-size:24px; font-weight:600;")
            card_layout.addWidget(label)
            card_layout.addWidget(value)
            if stat["progress"] is not None:
                bar = QProgressBar()
                bar.setRange(0, 100)
                bar.setValue(stat["progress"])
                card_layout.addWidget(bar)
            detail = QLabel(stat["detail"])
            detail.setStyleSheet("color:#9ca3af;")
            card_layout.addWidget(detail)
            grid.addWidget(card, 0, idx)
        return grid

    def _vector_status_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("Card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 16, 16, 16)
        title = QLabel("Vector Database Status")
        title.setStyleSheet("font-size:16px; font-weight:600;")
        layout.addWidget(title)

        meta_grid = QGridLayout()
        meta_grid.setSpacing(12)
        entries = [
            ("Totaal Vectors", "2.130"),
            ("Embedding Model", "all-MiniLM-L6-v2"),
            ("Database Engine", "ChromaDB"),
            ("Index Status", "Optimaal"),
        ]
        for idx, (label, value) in enumerate(entries):
            lbl = QLabel(label)
            lbl.setStyleSheet("color:#9ca3af;")
            val = QLabel(value)
            val.setStyleSheet("font-weight:600;")
            meta_grid.addWidget(lbl, 0, idx)
            meta_grid.addWidget(val, 1, idx)
        layout.addLayout(meta_grid)
        return card

    def _documents_table(self) -> QFrame:
        card = QFrame()
        card.setObjectName("Card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(0, 0, 0, 0)

        title = QLabel("Kennisbank Documenten")
        title.setStyleSheet("font-size:16px; font-weight:600; padding:16px;")
        card_layout.addWidget(title)

        table = QTableWidget()
        table.setColumnCount(6)
        table.setHorizontalHeaderLabels(
            ["Document", "Type", "Grootte", "Status", "Vectors", "Upload Datum"]
        )
        table.verticalHeader().setVisible(False)
        table.setShowGrid(False)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setSelectionMode(QTableWidget.NoSelection)
        table.setAlternatingRowColors(True)
        rows = [
            (
                "Technische Handleiding.pdf",
                "PDF",
                "2.4 MB",
                "Geïndexeerd",
                "1.240",
                "2025-10-28",
            ),
            (
                "Product Specificaties.pdf",
                "PDF",
                "1.8 MB",
                "Geïndexeerd",
                "890",
                "2025-10-27",
            ),
            (
                "FAQ Document.docx",
                "DOCX",
                "456 KB",
                "Verwerken…",
                "-",
                "2025-11-01",
            ),
        ]
        table.setRowCount(len(rows))
        for row_idx, row in enumerate(rows):
            for col_idx, value in enumerate(row):
                item = QTableWidgetItem(value)
                table.setItem(row_idx, col_idx, item)
        table.resizeColumnsToContents()
        card_layout.addWidget(table)
        return card
