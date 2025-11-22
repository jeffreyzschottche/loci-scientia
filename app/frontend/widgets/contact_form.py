from __future__ import annotations

from typing import Any, Dict, Optional

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QMessageBox,
)


class ContactFormDialog(QDialog):
    """Reusable contact form dialog that can prefill location data."""

    def __init__(
        self,
        parent=None,
        *,
        title: str = "Nieuw contact",
        initial: Optional[Dict[str, Any]] = None,
        location_defaults: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self._payload_cache: Optional[Dict[str, Any]] = None

        form = QFormLayout(self)
        form.setContentsMargins(16, 16, 16, 16)
        form.setSpacing(12)

        self.name_edit = QLineEdit()
        self.company_edit = QLineEdit()
        self.email_edit = QLineEdit()
        self.phone_edit = QLineEdit()
        self.notes_edit = QLineEdit()
        self.location_label_edit = QLineEdit()
        self.location_street_edit = QLineEdit()
        self.location_city_edit = QLineEdit()
        self.location_region_edit = QLineEdit()
        self.location_country_edit = QLineEdit()
        self.location_context_edit = QLineEdit()
        self.lat_edit = QLineEdit()
        self.lon_edit = QLineEdit()

        form.addRow("Naam", self.name_edit)
        form.addRow("Bedrijf", self.company_edit)
        form.addRow("E-mail", self.email_edit)
        form.addRow("Telefoon", self.phone_edit)
        form.addRow("Notities", self.notes_edit)
        form.addRow("Label", self.location_label_edit)
        form.addRow("Straat", self.location_street_edit)
        form.addRow("Plaats", self.location_city_edit)
        form.addRow("Regio", self.location_region_edit)
        form.addRow("Land", self.location_country_edit)
        form.addRow("Context", self.location_context_edit)
        form.addRow("Latitude", self.lat_edit)
        form.addRow("Longitude", self.lon_edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel, parent=self
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

        if initial:
            self._apply_initial(initial)
        if location_defaults:
            self.apply_location(location_defaults)

    def _apply_initial(self, data: Dict[str, Any]) -> None:
        self.name_edit.setText(data.get("name", ""))
        self.company_edit.setText(data.get("company", ""))
        self.email_edit.setText(data.get("email", ""))
        self.phone_edit.setText(data.get("phone", ""))
        self.notes_edit.setText(data.get("notes", ""))
        self.location_label_edit.setText(data.get("location_label", ""))
        self.location_street_edit.setText(data.get("location_street", ""))
        self.location_city_edit.setText(data.get("location_city", ""))
        self.location_region_edit.setText(data.get("location_region", ""))
        self.location_country_edit.setText(data.get("location_country", ""))
        self.location_context_edit.setText(data.get("location_context", ""))
        self.lat_edit.setText(self._format_float(data.get("location_lat")))
        self.lon_edit.setText(self._format_float(data.get("location_lon")))

    def apply_location(self, data: Dict[str, Any]) -> None:
        if not data:
            return
        label = data.get("label") or data.get("street") or ""
        if label:
            self.location_label_edit.setText(label)
        if data.get("street"):
            self.location_street_edit.setText(data["street"])
        if data.get("city"):
            self.location_city_edit.setText(data["city"])
        if data.get("region"):
            self.location_region_edit.setText(data["region"])
        if data.get("country"):
            self.location_country_edit.setText(data["country"])
        context_parts = [part for part in [data.get("region"), data.get("country")] if part]
        if context_parts and not self.location_context_edit.text().strip():
            self.location_context_edit.setText(", ".join(context_parts))
        if data.get("lat") is not None:
            self.lat_edit.setText(self._format_float(data.get("lat")))
        if data.get("lon") is not None:
            self.lon_edit.setText(self._format_float(data.get("lon")))

    def _format_float(self, value: Optional[float]) -> str:
        if value is None:
            return ""
        try:
            return f"{float(value):.6f}"
        except (TypeError, ValueError):
            return ""

    def _float_or_none(self, text: str) -> Optional[float]:
        stripped = text.strip()
        if not stripped:
            return None
        try:
            return float(stripped)
        except ValueError:
            return None

    def accept(self) -> None:  # type: ignore[override]
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "Ongeldig", "Naam is verplicht.")
            return
        self._payload_cache = self.payload()
        super().accept()

    def payload(self) -> Dict[str, Any]:
        return {
            "name": self.name_edit.text().strip(),
            "company": self.company_edit.text().strip(),
            "email": self.email_edit.text().strip(),
            "phone": self.phone_edit.text().strip(),
            "notes": self.notes_edit.text().strip(),
            "location_label": self.location_label_edit.text().strip() or None,
            "location_street": self.location_street_edit.text().strip() or None,
            "location_city": self.location_city_edit.text().strip() or None,
            "location_region": self.location_region_edit.text().strip() or None,
            "location_country": self.location_country_edit.text().strip() or None,
            "location_context": self.location_context_edit.text().strip() or None,
            "location_lat": self._float_or_none(self.lat_edit.text()),
            "location_lon": self._float_or_none(self.lon_edit.text()),
        }

    def payload_cache(self) -> Optional[Dict[str, Any]]:
        return self._payload_cache
