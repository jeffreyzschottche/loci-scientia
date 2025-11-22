from dataclasses import dataclass
from typing import Literal, Optional, Union

from .contacts_repo import ContactsRepository
from .devices_repo import DevicesRepository
from .schemas import ChatRequest, Contact, Device


@dataclass(frozen=True)
class SearchCandidate:
    kind: Literal["contact", "device"]
    score: float
    payload: Union[Contact, Device]


contacts_repo = ContactsRepository()
devices_repo = DevicesRepository()


def _describe_contact(contact: Contact) -> str:
    company = f" ({contact.company})" if contact.company else ""
    lines = [
        f"{contact.name}{company}",
        f"  ✉ {contact.email}" if contact.email else "",
        f"  ☎ {contact.phone}" if contact.phone else "",
        f"  ❝ {contact.notes}" if contact.notes else "",
    ]
    return "\n".join(line for line in lines if line)


def _describe_device(device: Device) -> str:
    lines = [
        f"{device.user_name} ({device.device_name})",
        f"  ✉ {device.email}" if device.email else "",
        f"  ☎ {device.phone}" if device.phone else "",
    ]
    return "\n".join(line for line in lines if line)


def _pick_best_candidate(
    contact_hits: list[tuple[Contact, float]],
    device_hits: list[tuple[Device, float]],
) -> Optional[SearchCandidate]:
    best: Optional[SearchCandidate] = None
    for kind, hits in (
        ("contact", contact_hits),
        ("device", device_hits),
    ):
        for entity, score in hits:
            candidate = SearchCandidate(kind=kind, score=score, payload=entity)
            if best is None or candidate.score > best.score:
                best = candidate
    return best


def handle_ask(req: ChatRequest) -> dict:
    """Returneer de beste match op basis van contacten en devices."""

    contact_hits = contacts_repo.search_contacts(req.prompt, limit=3)
    if not contact_hits:
        contact_hits = contacts_repo.keyword_search_contacts(req.prompt, limit=3)
    device_hits = devices_repo.search_devices(req.prompt, limit=3)
    best = _pick_best_candidate(contact_hits, device_hits)
    if not best:
        return {"message": "Geen relevante matches gevonden.", "matches": []}

    if best.kind == "contact":
        description = _describe_contact(best.payload)
        kind_label = "contact"
    else:
        description = _describe_device(best.payload)
        kind_label = "apparaat"

    return {
        "message": f"Ik vond dit {kind_label}:\n{description}",
        "kind": best.kind,
        "score": best.score,
        "matches": [best.payload.model_dump()],
    }
