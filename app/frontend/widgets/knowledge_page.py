import webbrowser

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
        title.setStyleSheet("font-size:28px; font-weight:800; letter-spacing:0.02em;")
        subtitle = QLabel("BEHEER KENNISBANK DOCUMENTEN EN SD KAART OPSLAG")
        subtitle.setStyleSheet(
            "color:#6b7280; letter-spacing:0.35em; font-size:11px;"
        )
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        header.addLayout(title_box, 1)

        upload = self._pill_button("⬆ Upload Document", primary=True)
        upload.clicked.connect(self._open_upload_portal)
        header.addWidget(upload, 0, Qt.AlignRight)
        layout.addLayout(header)

        layout.addLayout(self._stats_grid())
        layout.addWidget(self._vector_status_card())
        layout.addWidget(self._documents_table())

    def _pill_button(self, text: str, primary: bool = False) -> QPushButton:
        btn = QPushButton(text)
        btn.setCursor(Qt.PointingHandCursor)
        if primary:
            btn.setStyleSheet(
                "QPushButton {"
                "  background:#facc15;"
                "  color:#050505;"
                "  border-radius:999px;"
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
                "  border-radius:999px;"
                "  padding:10px 28px;"
                "  font-weight:600;"
                "}"
                "QPushButton:hover { border-color:rgba(33,33,33,0.45); }"
            )
        return btn

    @staticmethod
    def _open_upload_portal() -> None:
        webbrowser.open("https://www.aitje.jeffrai.nl")

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
            label = QLabel(stat["title"].upper())
            label.setStyleSheet(
                "color:#6b7280; letter-spacing:0.35em; font-size:11px;"
            )
            value = QLabel(stat["value"])
            value.setStyleSheet("font-size:28px; font-weight:700; color:#111111;")
            card_layout.addWidget(label)
            card_layout.addWidget(value)
            if stat["progress"] is not None:
                bar = QProgressBar()
                bar.setRange(0, 100)
                bar.setValue(stat["progress"])
                card_layout.addWidget(bar)
            detail = QLabel(stat["detail"])
            detail.setStyleSheet("color:#4b5563;")
            card_layout.addWidget(detail)
            grid.addWidget(card, 0, idx)
        return grid

    def _vector_status_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("Card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 16, 16, 16)
        title = QLabel("Vector Database Status")
        title.setStyleSheet("font-size:20px; font-weight:700; letter-spacing:0.02em;")
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
            lbl = QLabel(label.upper())
            lbl.setStyleSheet(
                "color:#6b7280; letter-spacing:0.3em; font-size:11px;"
            )
            val = QLabel(value)
            val.setStyleSheet("font-weight:600; color:#111111;")
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
        title.setStyleSheet(
            "font-size:20px; font-weight:700; padding:16px; letter-spacing:0.02em;"
        )
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
        table.setAlternatingRowColors(False)
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
        table.horizontalHeader().setStyleSheet(
            "QHeaderView::section { background:#ffffff; color:#111111; border:0; font-weight:600; }"
        )
        table.setStyleSheet("QTableWidget { background:#ffffff; }")
        table.resizeColumnsToContents()
        card_layout.addWidget(table)
        return card
