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

from ..config import API_ROUTES_DEFAULT_PORT, BACKEND_HTTP

API_BASE = BACKEND_HTTP


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
        self.port.setValue(API_ROUTES_DEFAULT_PORT)
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
        description = QLabel("BEHEER API ENDPOINTS, POORTEN EN TOEGANGSSLEUTELS")
        description.setStyleSheet(
            "color:#6b7280; letter-spacing:0.35em; font-size:11px;"
        )
        add_btn = QPushButton("+ Nieuwe API Route")
        add_btn.setStyleSheet(
            "QPushButton {"
            "  background:#facc15;"
            "  color:#050505;"
            "  padding:10px 28px;"
            "  border-radius:999px;"
            "  font-weight:600;"
            "}"
            "QPushButton:hover { background:#050505; color:#facc15; }"
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
            title = QLabel(label.upper())
            title.setStyleSheet(
                "color:#6b7280; letter-spacing:0.35em; font-size:11px;"
            )
            metric = QLabel(value)
            metric.setStyleSheet("font-size:26px; font-weight:700; color:#111111;")
            box.addWidget(title)
            box.addWidget(metric)
            row.addWidget(card, 0, idx)
        return row

    @staticmethod
    def _card():
        card = QFrame()
        card.setObjectName("Card")
        return card

    def _show_error(self, message: str):
        err = QLabel(message)
        err.setWordWrap(True)
        err.setStyleSheet("color:#f87171; font-weight:600;")
        self.grid.addWidget(err, 0, 0)

    def _reload(self):
        while self.grid.count():
            widget = self.grid.takeAt(0).widget()
            if widget:
                widget.deleteLater()
        try:
            resp = requests.get(f"{API_BASE}/routes", timeout=3)
            resp.raise_for_status()
        except requests.RequestException as exc:  # pragma: no cover - UI feedback only
            self._show_error(f"Kan routes niet laden: {exc}")
            return

        if not resp.content.strip():
            data = []
        else:
            try:
                data = resp.json()
            except ValueError:  # pragma: no cover - UI feedback only
                snippet = resp.text.strip().splitlines()
                body = snippet[0] if snippet else ""
                if len(body) > 120:
                    body = body[:117] + "..."
                self._show_error(
                    "Kan routes niet laden: ongeldige JSON van backend "
                    f"(status {resp.status_code}): {body or '<leeg antwoord>'}"
                )
                return

        if not isinstance(data, list):  # pragma: no cover - UI feedback only
            self._show_error(
                "Kan routes niet laden: onverwacht antwoordtype ontvangen."
            )
            return

        for idx, route in enumerate(data):
            card = self._card()
            grid = QGridLayout(card)
            grid.setContentsMargins(12, 12, 12, 12)
            grid.setHorizontalSpacing(16)
            grid.setVerticalSpacing(8)

            name = QLabel(route["name"])
            status = QLabel(("Actief" if route["active"] else "Inactief").upper())
            tone = "#facc15" if route["active"] else "#6b7280"
            status.setStyleSheet(
                f"color:{tone}; font-weight:600; letter-spacing:0.12em; font-size:11px;"
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
            edit.setStyleSheet(
                "QPushButton {"
                "  border:1px solid rgba(33,33,33,0.2);"
                "  border-radius:999px;"
                "  padding:8px 22px;"
                "  color:#111111;"
                "  background:transparent;"
                "}"
                "QPushButton:hover { border-color:rgba(33,33,33,0.45); }"
            )
            delete = QPushButton("Verwijderen")
            delete.setStyleSheet(
                "QPushButton {"
                "  background:#facc15;"
                "  color:#050505;"
                "  border-radius:999px;"
                "  padding:8px 22px;"
                "}"
                "QPushButton:hover { background:#050505; color:#facc15; }"
            )
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
