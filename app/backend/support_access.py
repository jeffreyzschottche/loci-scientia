from __future__ import annotations

import json
import logging
import os
import secrets
import shlex
import subprocess
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional


logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _coerce_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


@dataclass
class SupportAccessState:
    active: bool = False
    enabled_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    session_id: Optional[str] = None
    requested_by: Optional[str] = None
    public_key: Optional[str] = None
    ticket: Optional[str] = None
    last_error: Optional[str] = None

    @staticmethod
    def _parse_dt(value: Optional[str]) -> Optional[datetime]:
        if not value:
            return None
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError:
            return None
        return _coerce_utc(parsed)

    @classmethod
    def from_json(cls, payload: dict) -> "SupportAccessState":
        return cls(
            active=bool(payload.get("active", False)),
            enabled_at=cls._parse_dt(payload.get("enabled_at")),
            expires_at=cls._parse_dt(payload.get("expires_at")),
            session_id=payload.get("session_id"),
            requested_by=payload.get("requested_by"),
            public_key=payload.get("public_key"),
            ticket=payload.get("ticket"),
            last_error=payload.get("last_error"),
        )

    def to_json(self) -> dict:
        return {
            "active": self.active,
            "enabled_at": self.enabled_at.isoformat() if self.enabled_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "session_id": self.session_id,
            "requested_by": self.requested_by,
            "public_key": self.public_key,
            "ticket": self.ticket,
            "last_error": self.last_error,
        }

    def to_response(self) -> dict:
        return {
            "active": self.active,
            "enabled_at": self.enabled_at,
            "expires_at": self.expires_at,
            "session_id": self.session_id,
            "requested_by": self.requested_by,
            "last_error": self.last_error,
        }


class SupportAccessError(RuntimeError):
    def __init__(self, message: str, *, status_code: int = 400) -> None:
        super().__init__(message)
        self.status_code = status_code


class SupportAccessManager:
    def __init__(
        self,
        *,
        state_path: Optional[Path] = None,
        log_path: Optional[Path] = None,
        hook_cmd: Optional[str] = None,
        min_minutes: int = 15,
        max_minutes: int = 12 * 60,
    ) -> None:
        base_dir = Path(__file__).resolve().parents[2] / "devices_db"
        self.state_path = state_path or (base_dir / "support_access.json")
        self.log_path = log_path or (base_dir / "support_access.log")
        self.min_minutes = min_minutes
        self.max_minutes = max_minutes
        if hook_cmd is None:
            hook_cmd = os.environ.get("SUPPORT_SSH_HOOK", "")
        self.hook_cmd = hook_cmd.strip() or None
        self.state_path.parent.mkdir(parents=True, exist_ok=True)

    def _load_state(self) -> SupportAccessState:
        try:
            raw = self.state_path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return SupportAccessState()
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            return SupportAccessState()
        if not isinstance(payload, dict):
            return SupportAccessState()
        return SupportAccessState.from_json(payload)

    def _persist_state(self, state: SupportAccessState) -> None:
        tmp_path = self.state_path.with_suffix(".tmp")
        tmp_path.write_text(json.dumps(state.to_json(), indent=2), encoding="utf-8")
        tmp_path.replace(self.state_path)

    def _log_event(
        self,
        action: str,
        state: SupportAccessState,
        *,
        requested_by: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> None:
        line = (
            f"{_utcnow().isoformat()} action={action} "
            f"session={state.session_id or '-'} "
            f"requested_by={requested_by or '-'} "
            f"reason={reason or '-'}\n"
        )
        try:
            with self.log_path.open("a", encoding="utf-8") as handle:
                handle.write(line)
        except OSError:
            logger.warning("Kon support access log niet schrijven", exc_info=True)

    def _run_hook(self, action: str, state: SupportAccessState, *, reason: Optional[str]) -> None:
        if not self.hook_cmd:
            raise SupportAccessError(
                "SUPPORT_SSH_HOOK is niet geconfigureerd op dit apparaat.",
                status_code=501,
            )
        payload = {
            "action": action,
            "session_id": state.session_id,
            "requested_by": state.requested_by,
            "enabled_at": state.enabled_at.isoformat() if state.enabled_at else None,
            "expires_at": state.expires_at.isoformat() if state.expires_at else None,
            "public_key": state.public_key,
            "ticket": state.ticket,
            "reason": reason,
        }
        cmd = shlex.split(self.hook_cmd)
        result = subprocess.run(
            cmd,
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            timeout=15,
            check=False,
        )
        if result.returncode != 0:
            detail = (result.stderr or result.stdout or "Onbekende fout").strip()
            raise SupportAccessError(f"Support hook faalde: {detail}", status_code=502)

    def status(self) -> SupportAccessState:
        state = self._load_state()
        if state.active and state.expires_at:
            now = _utcnow()
            if state.expires_at <= now:
                try:
                    state = self.disable(
                        requested_by="system",
                        reason="expired",
                        force=True,
                    )
                except SupportAccessError as exc:
                    state.active = False
                    state.last_error = str(exc)
                    self._persist_state(state)
        return state

    def enable(
        self,
        *,
        duration_minutes: int,
        public_key: Optional[str],
        ticket: Optional[str],
        requested_by: Optional[str],
    ) -> SupportAccessState:
        if duration_minutes < self.min_minutes or duration_minutes > self.max_minutes:
            raise SupportAccessError(
                f"Duur moet tussen {self.min_minutes} en {self.max_minutes} minuten liggen."
            )
        if public_key:
            parts = public_key.split()
            if len(parts) < 2:
                raise SupportAccessError("Support sleutel lijkt geen geldige SSH key.")

        now = _utcnow()
        state = SupportAccessState(
            active=True,
            enabled_at=now,
            expires_at=now + timedelta(minutes=duration_minutes),
            session_id=secrets.token_urlsafe(8),
            requested_by=requested_by,
            public_key=public_key,
            ticket=ticket,
            last_error=None,
        )
        self._run_hook("enable", state, reason="manual")
        self._persist_state(state)
        self._log_event("enable", state, requested_by=requested_by)
        return state

    def disable(
        self,
        *,
        requested_by: Optional[str],
        reason: Optional[str],
        force: bool = False,
    ) -> SupportAccessState:
        state = self._load_state()
        if not state.active:
            return state
        error: Optional[str] = None
        try:
            self._run_hook("disable", state, reason=reason)
        except SupportAccessError as exc:
            if not force:
                raise
            error = str(exc)
        state.active = False
        state.last_error = error
        self._persist_state(state)
        self._log_event("disable", state, requested_by=requested_by, reason=reason)
        return state
