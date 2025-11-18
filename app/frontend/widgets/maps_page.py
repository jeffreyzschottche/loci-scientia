from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class MapsPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        layout.addWidget(self._build_sidebar(), 0)
        layout.addWidget(self._build_map_view(), 1)

    def _build_sidebar(self) -> QFrame:
        side = QFrame()
        side.setObjectName("Card")
        side_layout = QVBoxLayout(side)
        side_layout.setContentsMargins(16, 16, 16, 16)
        side_layout.setSpacing(16)

        search = QLineEdit()
        search.setPlaceholderText("Zoek locatie…")
        side_layout.addWidget(search)

        combo_layout = QHBoxLayout()
        combo_layout.setContentsMargins(0, 0, 0, 0)
        combo_layout.setSpacing(8)
        layer_label = QLabel("Kaartlaag")
        layer_label.setStyleSheet("color:#9ca3af;")
        combo = QComboBox()
        combo.addItems(["Standaard", "Satelliet", "Hoogte"])
        combo_layout.addWidget(layer_label)
        combo_layout.addStretch(1)
        combo_layout.addWidget(combo)
        side_layout.addLayout(combo_layout)

        current_btn = QPushButton("Huidige Locatie")
        current_btn.setStyleSheet(
            "background:#2563eb; color:white; border-radius:8px; padding:8px;"
        )
        side_layout.addWidget(current_btn)

        side_layout.addWidget(QLabel("Gedownloade Regio's"))
        region_list = QListWidget()
        for name, size, status in [
            ("Nederland", "1.2 GB", "Offline"),
            ("België", "890 MB", "Offline"),
            ("Duitsland", "3.4 GB", "Download beschikbaar"),
        ]:
            item = QListWidgetItem(f"{name} • {size} • {status}")
            region_list.addItem(item)
        side_layout.addWidget(region_list, 1)

        download_btn = QPushButton("Nieuwe Regio Downloaden")
        download_btn.setStyleSheet(
            "border:1px solid #374151; color:white; border-radius:8px; padding:8px;"
        )
        side_layout.addWidget(download_btn)

        storage = QFrame()
        storage_layout = QVBoxLayout(storage)
        storage_layout.setContentsMargins(0, 0, 0, 0)
        storage_label = QLabel("Kaartdata Opslag: 2.1 / 256 GB")
        storage_label.setStyleSheet("color:#9ca3af;")
        storage_bar = QLabel("████░░░░░░░░░░░░")
        storage_bar.setStyleSheet("font-family: monospace; color:#2563eb;")
        storage_layout.addWidget(storage_label)
        storage_layout.addWidget(storage_bar)
        side_layout.addWidget(storage)
        return side

    def _build_map_view(self) -> QFrame:
        area = QFrame()
        area.setObjectName("Card")
        layout = QGridLayout(area)
        layout.setContentsMargins(16, 16, 16, 16)

        center = QLabel("Offline kaart placeholder")
        center.setAlignment(Qt.AlignCenter)
        center.setStyleSheet("font-size:18px; color:#9ca3af;")
        layout.addWidget(center, 0, 0, 1, 2)

        meta = QLabel("Amsterdam, Nederland\n52.3676° N, 4.9041° E")
        meta.setStyleSheet("background:#111827; padding:8px; border-radius:8px;")
        layout.addWidget(meta, 0, 0, Qt.AlignTop | Qt.AlignLeft)

        zoom_controls = QVBoxLayout()
        plus = QPushButton("+")
        minus = QPushButton("-")
        for btn in (plus, minus):
            btn.setFixedSize(32, 32)
            btn.setStyleSheet(
                "background:#111827; border-radius:8px; border:1px solid #1f2937;"
            )
            zoom_controls.addWidget(btn)
        zoom_controls.addStretch(1)
        layout.addLayout(zoom_controls, 0, 1, Qt.AlignTop | Qt.AlignRight)
        return area
