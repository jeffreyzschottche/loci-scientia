from __future__ import annotations

from typing import Iterable


ROLE_CHAT = "chat"
ROLE_KNOWLEDGE_MANAGEMENT = "knowledge_management"

DEFAULT_ROLES = [ROLE_CHAT]
ALL_ROLES = [ROLE_CHAT, ROLE_KNOWLEDGE_MANAGEMENT]

ROLE_LABELS = {
    ROLE_CHAT: {
        "nl": "Chatten",
        "en": "Chat",
    },
    ROLE_KNOWLEDGE_MANAGEMENT: {
        "nl": "Kennisbank management",
        "en": "Knowledge base management",
    },
}


def normalize_roles(raw_roles: Iterable[str] | None) -> list[str]:
    roles = []
    for role in raw_roles or []:
        value = str(role).strip()
        if value in ALL_ROLES and value not in roles:
            roles.append(value)
    return roles or list(DEFAULT_ROLES)


def has_role(raw_roles: Iterable[str] | None, role: str) -> bool:
    return role in normalize_roles(raw_roles)
