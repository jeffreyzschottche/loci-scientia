"""Shared front-end state for contacts and map locations."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional
import uuid


@dataclass
class ContactRecord:
    id: str
    name: str
    company: str
    email: str
    phone: str
    notes: str = ""
    location_ids: List[str] = field(default_factory=list)


@dataclass
class LocationRecord:
    id: str
    label: str
    country: str
    coordinates: str
    linked_contact_id: Optional[str] = None
    notes: str = ""

    @property
    def contact_label(self) -> str:
        return "Gekoppeld aan contact" if self.linked_contact_id else "Los adres"


class MapContactStore:
    """Simple in-memory store so pages share the same data."""

    def __init__(self, supported_countries: Optional[list[str]] = None):
        self.SUPPORTED_COUNTRIES = supported_countries or ["Nederland", "Duitsland"]
        self.contacts: Dict[str, ContactRecord] = {}
        self.locations: Dict[str, LocationRecord] = {}
        self._seed()

    def _seed(self) -> None:
        jan = self.add_contact(
            name="Jan de Vries",
            company="Tech Solutions BV",
            email="jan@techsolutions.nl",
            phone="+31 6 1234 5678",
            notes="Voorkeur voor fysieke afspraken."
        )
        maria = self.add_contact(
            name="Maria Janssen",
            company="Data Insights",
            email="maria@data-insights.io",
            phone="+31 6 8765 4321",
            notes="Werkzaam in Ruhrgebied."
        )
        self.add_contact(
            name="Pieter Bakker",
            company="Innovation Labs",
            email="pieter@innovationlabs.nl",
            phone="+31 6 9999 2222",
            notes="Loves on-site workshops."
        )

        if "Nederland" in self.SUPPORTED_COUNTRIES:
            self.add_location(
                label="HQ Amsterdam",
                country="Nederland",
                coordinates="52.3676° N, 4.9041° E",
                contact_id=jan.id,
                notes="Hoofdkantoor Jan",
            )
            self.add_location(
                label="Opslag Rotterdam",
                country="Nederland",
                coordinates="51.9244° N, 4.4777° E",
                contact_id=None,
                notes="Algemene voorraad",
            )
        if "Duitsland" in self.SUPPORTED_COUNTRIES:
            self.add_location(
                label="Ruhr Demo Center",
                country="Duitsland",
                coordinates="51.4556° N, 7.0116° E",
                contact_id=maria.id,
                notes="Test omgeving",
            )

    def add_contact(self, name: str, company: str, email: str, phone: str, notes: str = "") -> ContactRecord:
        cid = str(uuid.uuid4())
        record = ContactRecord(id=cid, name=name, company=company, email=email, phone=phone, notes=notes)
        self.contacts[cid] = record
        return record

    def list_contacts(self) -> List[ContactRecord]:
        return list(self.contacts.values())

    def add_location(
        self,
        label: str,
        country: str,
        coordinates: str,
        contact_id: Optional[str] = None,
        notes: str = "",
    ) -> LocationRecord:
        if country not in self.SUPPORTED_COUNTRIES:
            raise ValueError("Onbekende kaartregio")
        lid = str(uuid.uuid4())
        record = LocationRecord(
            id=lid,
            label=label,
            country=country,
            coordinates=coordinates,
            linked_contact_id=contact_id,
            notes=notes,
        )
        self.locations[lid] = record
        if contact_id:
            self.link_contact_to_location(contact_id, lid)
        return record

    def link_contact_to_location(self, contact_id: str, location_id: str) -> None:
        contact = self.contacts[contact_id]
        if location_id not in contact.location_ids:
            contact.location_ids.append(location_id)
        location = self.locations[location_id]
        location.linked_contact_id = contact_id

    def list_locations(self, country: Optional[str] = None) -> List[LocationRecord]:
        data = self.locations.values()
        if country:
            data = [loc for loc in data if loc.country == country]
        return list(data)

    def get_contact_locations(self, contact_id: str) -> List[LocationRecord]:
        contact = self.contacts.get(contact_id)
        if not contact:
            return []
        return [self.locations[lid] for lid in contact.location_ids if lid in self.locations]

    def get_contact(self, contact_id: str) -> Optional[ContactRecord]:
        return self.contacts.get(contact_id)

    def get_location(self, location_id: str) -> Optional[LocationRecord]:
        return self.locations.get(location_id)

    def update_location(self, location_id: str, **changes: str) -> None:
        location = self.locations[location_id]
        for key, value in changes.items():
            setattr(location, key, value)

    def iter_countries(self) -> Iterable[str]:
        return list(self.SUPPORTED_COUNTRIES)
