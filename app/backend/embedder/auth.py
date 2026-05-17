"""Login + bearer-guard voor de embedder.

Single-tenant: één gebruiker wordt geconfigureerd via env-variabelen
(``EMBEDDER_USER_EMAIL`` / ``EMBEDDER_USER_PASSWORD`` / ``EMBEDDER_USER_NAME``).
Tokens worden uitgegeven door een aparte ``BearerTokenStore`` (eigen bestand,
zodat embedder-tokens niet per ongeluk geldig zijn voor de device-API).
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import Depends, Header, HTTPException

from app.backend.auth_tokens import BearerTokenStore, TokenRecord
from app.backend.settings import settings


_EMBEDDER_DEVICE_ID = "embedder-admin"
_TOKENS_FILE = (
    Path(__file__).resolve().parents[3] / "devices_db" / "embedder_tokens.json"
)


token_store = BearerTokenStore(tokens_path=_TOKENS_FILE, ttl_days=90)


def admin_user_payload() -> dict:
    """Frontend verwacht ``{ id, name, email, email_verified_at, ... }``.

    Email-verificatie is gedropt; we doen alsof de gebruiker geverifieerd is
    sinds boot, zodat oude SPA-code die op het veld checkt blijft werken.
    """

    now_iso = datetime.now(timezone.utc).isoformat()
    return {
        "id": 1,
        "name": settings.embedder_admin_name,
        "email": settings.embedder_admin_email or "",
        "email_verified_at": now_iso,
        "premium": False,
        "created_at": now_iso,
        "updated_at": now_iso,
    }


def verify_credentials(email: str, password: str) -> bool:
    expected_email = (settings.embedder_admin_email or "").strip().lower()
    expected_password = settings.embedder_admin_password or ""
    if not expected_email or not expected_password:
        return False
    return email.strip().lower() == expected_email and password == expected_password


def issue_token() -> TokenRecord:
    return token_store.issue_token(_EMBEDDER_DEVICE_ID, settings.embedder_admin_name)


def revoke_token(token: str) -> None:
    record = token_store.validate(token)
    if record is None:
        return
    token_store.revoke_for_device(record.device_id)


def _extract_bearer(authorization: Optional[str]) -> str:
    if not authorization:
        raise HTTPException(status_code=401, detail="Niet ingelogd")
    scheme, _, value = authorization.partition(" ")
    if scheme.lower() != "bearer" or not value.strip():
        raise HTTPException(status_code=401, detail="Ongeldig Authorization-header")
    return value.strip()


def require_embedder_user(
    authorization: Optional[str] = Header(default=None),
) -> TokenRecord:
    token_value = _extract_bearer(authorization)
    record = token_store.validate(token_value)
    if record is None or record.device_id != _EMBEDDER_DEVICE_ID:
        raise HTTPException(status_code=401, detail="Sessie verlopen, log opnieuw in")
    return record
