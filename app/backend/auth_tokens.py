from __future__ import annotations

import json
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable, Optional


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _coerce_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


@dataclass
class TokenRecord:
    token: str
    device_id: str
    user_name: str
    expires_at: datetime

    def to_json(self) -> dict:
        return {
            "token": self.token,
            "device_id": self.device_id,
            "user_name": self.user_name,
            "expires_at": self.expires_at.isoformat(),
        }


class BearerTokenStore:
    """Simple JSON-file backed token store for issuing and validating bearer tokens."""

    def __init__(self, tokens_path: Optional[Path] = None, ttl_days: int = 90) -> None:
        default_dir = Path(__file__).resolve().parents[2] / "devices_db"
        if tokens_path is None:
            tokens_path = default_dir / "tokens.json"
        self.tokens_path = tokens_path
        self.tokens_path.parent.mkdir(parents=True, exist_ok=True)
        self.ttl = timedelta(days=ttl_days)

    # -- internal helpers -------------------------------------------------
    def _load_tokens(self) -> list[TokenRecord]:
        try:
            raw_text = self.tokens_path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return []
        try:
            payload = json.loads(raw_text)
            if isinstance(payload, dict) and "tokens" in payload:
                items = payload.get("tokens") or []
            elif isinstance(payload, list):
                items = payload
            else:
                items = []
        except json.JSONDecodeError:
            return []

        tokens: list[TokenRecord] = []
        for entry in items:
            if not isinstance(entry, dict):
                continue
            token = entry.get("token")
            device_id = entry.get("device_id")
            user_name = entry.get("user_name")
            expires_at = entry.get("expires_at")
            if not (token and device_id and user_name and expires_at):
                continue
            try:
                parsed_expiry = datetime.fromisoformat(expires_at)
            except ValueError:
                continue
            record = TokenRecord(
                token=token,
                device_id=str(device_id),
                user_name=str(user_name),
                expires_at=_coerce_utc(parsed_expiry),
            )
            tokens.append(record)
        return tokens

    def _persist_tokens(self, records: Iterable[TokenRecord]) -> None:
        data = [record.to_json() for record in records]
        tmp_path = self.tokens_path.with_suffix(".tmp")
        tmp_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        tmp_path.replace(self.tokens_path)

    # -- public API -------------------------------------------------------
    def issue_token(self, device_id: str, user_name: str) -> TokenRecord:
        valid = self._purge_expired()
        # Replace any existing token for this device to avoid duplicates.
        valid = [record for record in valid if record.device_id != device_id]
        token_value = secrets.token_urlsafe(40)
        expires_at = _utcnow() + self.ttl
        record = TokenRecord(
            token=token_value,
            device_id=device_id,
            user_name=user_name,
            expires_at=expires_at,
        )
        valid.append(record)
        self._persist_tokens(valid)
        return record

    def _purge_expired(self) -> list[TokenRecord]:
        now = _utcnow()
        existing = self._load_tokens()
        valid = [record for record in existing if record.expires_at > now]
        if len(valid) != len(existing):
            self._persist_tokens(valid)
        return valid

    def validate(self, token: str) -> Optional[TokenRecord]:
        now = _utcnow()
        valid = self._load_tokens()
        dirty = False
        kept: list[TokenRecord] = []
        match: Optional[TokenRecord] = None
        for record in valid:
            if record.expires_at <= now:
                dirty = True
                continue
            kept.append(record)
            if record.token == token and match is None:
                match = record
        if dirty:
            self._persist_tokens(kept)
        return match

    def revoke_for_device(self, device_id: str) -> int:
        if not device_id:
            return 0
        valid = self._purge_expired()
        remaining = [record for record in valid if record.device_id != device_id]
        removed = len(valid) - len(remaining)
        if removed:
            self._persist_tokens(remaining)
        return removed

    def get_valid_for_device(
        self,
        device_id: str,
        *,
        user_name: Optional[str] = None,
    ) -> Optional[TokenRecord]:
        if not device_id:
            return None
        valid = self._purge_expired()
        for record in valid:
            if record.device_id != device_id:
                continue
            if user_name and record.user_name != user_name:
                continue
            return record
        return None
