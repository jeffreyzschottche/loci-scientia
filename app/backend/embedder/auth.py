"""Login + bearer-guard voor de embedder."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import Header, HTTPException

from app.backend.auth_tokens import BearerTokenStore, TokenRecord
from app.backend.devices_repo import DevicesRepository
from app.backend.settings import settings
from app.backend.user_roles import ROLE_KNOWLEDGE_MANAGEMENT, has_role


_EMBEDDER_DEVICE_ID = "embedder-admin"
_TOKENS_FILE = (
    Path(__file__).resolve().parents[3] / "devices_db" / "embedder_tokens.json"
)


token_store = BearerTokenStore(tokens_path=_TOKENS_FILE, ttl_days=90)
devices_repo = DevicesRepository()


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


def device_user_payload(device) -> dict:
    now_iso = datetime.now(timezone.utc).isoformat()
    return {
        "id": device.id,
        "name": device.user_name,
        "email": device.email or "",
        "email_verified_at": now_iso,
        "premium": False,
        "created_at": now_iso,
        "updated_at": now_iso,
        "roles": device.roles,
    }


def verify_credentials(email: str, password: str) -> bool:
    expected_email = (settings.embedder_admin_email or "").strip().lower()
    expected_password = settings.embedder_admin_password or ""
    if not expected_email or not expected_password:
        return False
    return email.strip().lower() == expected_email and password == expected_password


def issue_token(email: str, password: str) -> tuple[TokenRecord, dict]:
    if verify_credentials(email, password):
        record = token_store.issue_token(
            _EMBEDDER_DEVICE_ID,
            settings.embedder_admin_name,
            roles=[ROLE_KNOWLEDGE_MANAGEMENT],
        )
        return record, admin_user_payload()

    normalized_email = email.strip().lower()
    for device in devices_repo.list_devices():
        if (device.email or "").strip().lower() != normalized_email:
            continue
        if device.password != password:
            break
        if not has_role(device.roles, ROLE_KNOWLEDGE_MANAGEMENT):
            break
        record = token_store.issue_token(
            device.id,
            device.user_name,
            roles=device.roles,
        )
        return record, device_user_payload(device)

    raise ValueError("Deze inloggegevens kloppen niet.")


def revoke_token(token: str) -> None:
    record = token_store.validate(token)
    if record is None:
        return
    token_store.revoke_for_device(record.device_id)


def user_payload_for_record(record: TokenRecord) -> dict:
    if record.device_id == _EMBEDDER_DEVICE_ID:
        return admin_user_payload()
    device = devices_repo.get_device(record.device_id)
    if device is not None:
        return device_user_payload(device)
    now_iso = datetime.now(timezone.utc).isoformat()
    return {
        "id": record.device_id,
        "name": record.user_name,
        "email": "",
        "email_verified_at": now_iso,
        "premium": False,
        "created_at": now_iso,
        "updated_at": now_iso,
        "roles": record.roles,
    }


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
    if record is None or not has_role(record.roles, ROLE_KNOWLEDGE_MANAGEMENT):
        raise HTTPException(status_code=401, detail="Sessie verlopen, log opnieuw in")
    return record
