from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
    QFrame,
)
import requests

API_BASE = "http://127.0.0.1:8000"


class ApiDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Nieuwe API Route")
        form = QFormLayout(self)
        self.name = QLineEdit()
        self.method = QComboBox()
        self.method.addItems(["GET", "POST", "PUT", "DELETE"])
        self.path = QLineEdit("/api/example")
        self.port = QSpinBox()
        self.port.setRange(1, 65535)
        self.port.setValue(8080)
        self.kb = QLineEdit("Algemene Kennisbank")
        self.api_key = QLineEdit("loci_sk_xxx")

        form.addRow("Naam", self.name)
        form.addRow("Methode", self.method)
        form.addRow("Pad", self.path)
        form.addRow("Port", self.port)
        form.addRow("Kennisbank", self.kb)
        form.addRow("API Key", self.api_key)

        buttons = QHBoxLayout()
        save = QPushButton("Opslaan")
        cancel = QPushButton("Annuleren")
        save.clicked.connect(self.accept)
        cancel.clicked.connect(self.reject)
        buttons.addWidget(save)
        buttons.addWidget(cancel)
        form.addRow(buttons)

    def payload(self) -> dict:
        return {
            "name": self.name.text(),
            "method": self.method.currentText(),
            "path": self.path.text(),
            "port": int(self.port.value()),
            "knowledge_base": self.kb.text() or None,
            "api_key": self.api_key.text() or None,
            "active": True,
        }


class ApiPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        header = QHBoxLayout()
        description = QLabel("Beheer API endpoints, poorten en toegangssleutels")
        description.setStyleSheet("color:#9ca3af;")
        add_btn = QPushButton("+ Nieuwe API Route")
        add_btn.setStyleSheet(
            "color:white; background:#2563eb; padding:6px 10px; border-radius:6px;"
        )
        add_btn.clicked.connect(self._add_route)
        header.addWidget(description)
        header.addStretch(1)
        header.addWidget(add_btn)
        layout.addLayout(header)

        self.grid = QGridLayout()
        self.grid.setSpacing(12)
        layout.addLayout(self.grid)

        self.metrics_row = self._build_metrics()
        layout.addLayout(self.metrics_row)

        self._reload()

    def _build_metrics(self):
        row = QGridLayout()
        row.setSpacing(12)
        for idx, (label, value) in enumerate(
            [
                ("Totaal Routes", "2"),
                ("Actieve Routes", "2"),
                ("API Calls (24u)", "1,247"),
            ]
        ):
            card = self._card()
            box = QVBoxLayout(card)
            box.setContentsMargins(12, 12, 12, 12)
            title = QLabel(label)
            title.setStyleSheet("color:#9ca3af;")
            metric = QLabel(value)
            metric.setStyleSheet("font-size:20px;")
            box.addWidget(title)
            box.addWidget(metric)
            row.addWidget(card, 0, idx)
        return row

    @staticmethod
    def _card():
        card = QFrame()
        card.setObjectName("Card")
        return card

    def _reload(self):
        while self.grid.count():
            widget = self.grid.takeAt(0).widget()
            if widget:
                widget.deleteLater()
        try:
            data = requests.get(f"{API_BASE}/routes", timeout=3).json()
        except Exception as exc:  # pragma: no cover - UI feedback only
            err = QLabel(f"Kan routes niet laden: {exc}")
            self.grid.addWidget(err, 0, 0)
            return

        for idx, route in enumerate(data):
            card = self._card()
            grid = QGridLayout(card)
            grid.setContentsMargins(12, 12, 12, 12)
            grid.setHorizontalSpacing(16)
            grid.setVerticalSpacing(8)

            name = QLabel(route["name"])
            status = QLabel("Actief" if route["active"] else "Inactief")
            status.setStyleSheet(
                "color: " + ("#10b981" if route["active"] else "#f59e0b") + ";"
            )
            grid.addWidget(name, 0, 0)
            grid.addWidget(status, 0, 1)

            grid.addWidget(QLabel("Route:"), 1, 0)
            grid.addWidget(QLabel(f"<code>{route['path']}</code>"), 1, 1)
            grid.addWidget(QLabel("Port:"), 2, 0)
            grid.addWidget(QLabel(str(route["port"])), 2, 1)
            grid.addWidget(QLabel("Kennisbank:"), 3, 0)
            grid.addWidget(QLabel(route.get("knowledge_base") or "-"), 3, 1)
            grid.addWidget(QLabel("API Key:"), 4, 0)
            grid.addWidget(QLabel(f"<code>{route.get('api_key') or '-'}"), 4, 1)

            actions = QHBoxLayout()
            edit = QPushButton("Bewerken")
            delete = QPushButton("Verwijderen")
            edit.clicked.connect(lambda _=False, rid=route["id"]: self._edit_route(rid))
            delete.clicked.connect(lambda _=False, rid=route["id"]: self._delete_route(rid))
            actions.addWidget(edit)
            actions.addWidget(delete)
            grid.addLayout(actions, 5, 0, 1, 2)

            self.grid.addWidget(card, idx, 0)

    def _add_route(self):
        dialog = ApiDialog(self)
        if dialog.exec():
            try:
                requests.post(f"{API_BASE}/routes", json=dialog.payload(), timeout=3)
                self._reload()
            except Exception as exc:
                QMessageBox.critical(self, "Fout", str(exc))

    def _edit_route(self, rid: str):
        try:
            requests.patch(f"{API_BASE}/routes/{rid}", json={"active": True}, timeout=3)
            self._reload()
        except Exception as exc:
            QMessageBox.critical(self, "Fout", str(exc))

    def _delete_route(self, rid: str):
        try:
            requests.delete(f"{API_BASE}/routes/{rid}", timeout=3)
            self._reload()
        except Exception as exc:
            QMessageBox.critical(self, "Fout", str(exc))
