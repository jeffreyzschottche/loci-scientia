from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_LOCK_PATH = PROJECT_ROOT / "devices_db" / "kiosk_lock.json"
PBKDF2_ALGORITHM = "sha256"
PBKDF2_ITERATIONS = 260_000
SALT_BYTES = 16


class KioskLockStore:
    def __init__(self, path: Path = DEFAULT_LOCK_PATH):
        self.path = Path(path)
        self._lock = Lock()

    def snapshot(self) -> dict:
        payload = self._read()
        configured = self._is_configured(payload)
        return {
            "configured": configured,
            "password": str(payload.get("password") or "") if configured else "",
            "reminder_question": str(payload.get("reminder_question") or "") if configured else "",
            "reminder_hint": str(payload.get("reminder_hint") or "") if configured else "",
            "notes": str(payload.get("notes") or "") if configured else "",
            "updated_at": payload.get("updated_at") if configured else None,
        }

    def configure(
        self,
        *,
        password: str,
        reminder_question: str = "",
        reminder_hint: str = "",
        notes: str = "",
    ) -> dict:
        password = password or ""
        if len(password) < 4:
            raise ValueError("Het wachtwoord moet minimaal 4 tekens lang zijn.")

        now = datetime.now(timezone.utc).isoformat()
        existing = self._read()
        salt = secrets.token_bytes(SALT_BYTES)
        password_hash = self._hash_password(password, salt)
        payload = {
            "version": 1,
            "password_hash": base64.b64encode(password_hash).decode("ascii"),
            "password_salt": base64.b64encode(salt).decode("ascii"),
            "password": password,
            "iterations": PBKDF2_ITERATIONS,
            "algorithm": PBKDF2_ALGORITHM,
            "reminder_question": reminder_question.strip(),
            "reminder_hint": reminder_hint.strip(),
            "notes": notes.strip(),
            "created_at": existing.get("created_at") or now,
            "updated_at": now,
        }
        self._write(payload)
        return self.snapshot()

    def verify_password(self, password: str) -> bool:
        payload = self._read()
        if not self._is_configured(payload):
            return False
        provided = password or ""
        verified = self._verify_payload_password(payload, provided)
        if verified and provided and not payload.get("password"):
            payload["password"] = provided
            self._write(payload)
        return verified

    @staticmethod
    def verify_override_password(password: str, configured_override: str | None) -> bool:
        expected = configured_override or ""
        provided = password or ""
        if not expected or not provided:
            return False
        return hmac.compare_digest(provided, expected)

    def _read(self) -> dict:
        try:
            raw = self.path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return {}
        except OSError:
            return {}
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            return {}
        return payload if isinstance(payload, dict) else {}

    def _write(self, payload: dict) -> None:
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix(".tmp")
            tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            tmp.replace(self.path)

    @staticmethod
    def _is_configured(payload: dict) -> bool:
        return bool(payload.get("password_hash") and payload.get("password_salt"))

    @staticmethod
    def _hash_password(password: str, salt: bytes, *, iterations: int = PBKDF2_ITERATIONS) -> bytes:
        return hashlib.pbkdf2_hmac(
            PBKDF2_ALGORITHM,
            password.encode("utf-8"),
            salt,
            iterations,
        )

    def _verify_payload_password(self, payload: dict, password: str) -> bool:
        try:
            salt = base64.b64decode(str(payload.get("password_salt") or ""), validate=True)
            expected = base64.b64decode(str(payload.get("password_hash") or ""), validate=True)
            iterations = int(payload.get("iterations") or PBKDF2_ITERATIONS)
        except (ValueError, TypeError):
            return False
        actual = self._hash_password(password, salt, iterations=iterations)
        return hmac.compare_digest(actual, expected)
