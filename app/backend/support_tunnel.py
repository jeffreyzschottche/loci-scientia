from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _coerce_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


@dataclass
class TunnelConfig:
    jump_server_ip: str
    tunnel_port: int
    tunnel_user: str
    tunnel_key_path: str


@dataclass
class SupportTunnelState:
    active: bool = False
    expires_at: Optional[datetime] = None
    port: Optional[int] = None
    error: Optional[str] = None

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
    def from_json(cls, payload: dict) -> "SupportTunnelState":
        return cls(
            active=bool(payload.get("active", False)),
            expires_at=cls._parse_dt(payload.get("expires_at")),
            port=payload.get("port"),
            error=payload.get("error"),
        )

    def to_json(self) -> dict:
        return {
            "active": self.active,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "port": self.port,
            "error": self.error,
        }

    def to_response(self) -> dict:
        return {
            "active": self.active,
            "expires_at": self.expires_at,
            "port": self.port,
            "error": self.error,
        }


class SupportTunnelError(RuntimeError):
    def __init__(self, message: str, *, status_code: int = 400) -> None:
        super().__init__(message)
        self.status_code = status_code


class SupportTunnelManager:
    def __init__(
        self,
        *,
        env_path: Path,
        state_path: Optional[Path] = None,
        service_name: str = "aitje-tunnel",
        timer_unit: str = "aitje-tunnel-stop",
    ) -> None:
        self.env_path = env_path.expanduser().resolve()
        self.state_path = state_path or Path("/tmp/aitje-tunnel-state.json")
        self.service_name = service_name
        self.timer_unit = timer_unit
        self.allowed_durations = {30, 60, 120}

    def _load_state(self) -> SupportTunnelState:
        try:
            raw = self.state_path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return SupportTunnelState()
        except OSError:
            return SupportTunnelState()
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            return SupportTunnelState()
        if not isinstance(payload, dict):
            return SupportTunnelState()
        return SupportTunnelState.from_json(payload)

    def _persist_state(self, state: SupportTunnelState) -> None:
        payload = state.to_json()
        payload["error"] = None
        tmp_path = self.state_path.with_suffix(".tmp")
        tmp_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        tmp_path.replace(self.state_path)

    def _load_env_file(self) -> dict[str, str]:
        values: dict[str, str] = {}
        try:
            content = self.env_path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return values
        except OSError:
            return values
        for raw_line in content.splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            if not key:
                continue
            value = value.strip()
            if value and value[0] in {"'", '"'} and value[-1:] == value[0]:
                value = value[1:-1]
            else:
                value = value.split(" #", 1)[0].strip()
            values[key] = value
        return values

    def _env_value(self, key: str) -> str:
        live_value = os.environ.get(key)
        if live_value:
            return live_value.strip()
        return self._load_env_file().get(key, "").strip()

    def _configuration_error(self) -> Optional[str]:
        missing = [
            key
            for key in ("JUMP_SERVER_IP", "TUNNEL_PORT", "TUNNEL_USER", "TUNNEL_KEY_PATH")
            if not self._env_value(key)
        ]
        if missing:
            return (
                f"Remote support is niet volledig geconfigureerd. "
                f"Ontbreekt: {', '.join(missing)} in {self.env_path}."
            )
        port_raw = self._env_value("TUNNEL_PORT")
        try:
            port = int(port_raw)
        except ValueError:
            return "TUNNEL_PORT moet een geldig poortnummer zijn."
        if port <= 0 or port > 65535:
            return "TUNNEL_PORT moet tussen 1 en 65535 liggen."
        return None

    def _read_config(self, *, require_complete: bool) -> Optional[TunnelConfig]:
        error = self._configuration_error()
        if error:
            if require_complete:
                raise SupportTunnelError(error)
            return None
        port = int(self._env_value("TUNNEL_PORT"))
        return TunnelConfig(
            jump_server_ip=self._env_value("JUMP_SERVER_IP"),
            tunnel_port=port,
            tunnel_user=self._env_value("TUNNEL_USER"),
            tunnel_key_path=self._env_value("TUNNEL_KEY_PATH"),
        )

    def _require_runtime_tools(self, *, need_timer: bool) -> None:
        if not Path("/usr/bin/systemctl").exists():
            raise SupportTunnelError("systemctl is niet beschikbaar op dit apparaat.", status_code=500)
        if need_timer and not Path("/usr/bin/systemd-run").exists():
            raise SupportTunnelError("systemd-run is niet beschikbaar op dit apparaat.", status_code=500)
        if shutil.which("autossh") is None:
            raise SupportTunnelError(
                "autossh is niet geïnstalleerd. Installeer autossh en openssh-client eerst.",
                status_code=500,
            )

    def _sudo_prefix(self) -> list[str]:
        if os.geteuid() == 0:
            return []
        if shutil.which("sudo") is None:
            raise SupportTunnelError(
                "sudo ontbreekt. Installeer sudoers/aitje-tunnel of draai de backend als root.",
                status_code=500,
            )
        return ["sudo", "-n"]

    def _run_root_command(
        self,
        *args: str,
        allowed_returncodes: tuple[int, ...] = (0,),
        timeout: int = 20,
    ) -> subprocess.CompletedProcess[str]:
        command = [*self._sudo_prefix(), *args]
        try:
            result = subprocess.run(
                command,
                check=False,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except FileNotFoundError as exc:
            raise SupportTunnelError(f"Commando niet gevonden: {args[0]}", status_code=500) from exc
        except subprocess.TimeoutExpired as exc:
            raise SupportTunnelError("Systeemcommando duurde te lang.", status_code=504) from exc
        if result.returncode in allowed_returncodes:
            return result
        detail = (result.stderr or result.stdout or "Onbekende systeemfout").strip()
        detail_lower = detail.lower()
        if "password is required" in detail_lower or "sudoers" in detail_lower:
            raise SupportTunnelError(
                "aitje mag aitje-tunnel nog niet zonder wachtwoord beheren. "
                "Installeer eerst sudoers/aitje-tunnel.",
                status_code=500,
            )
        raise SupportTunnelError(detail or f"Commando faalde: {' '.join(args)}", status_code=502)

    def _service_is_active(self) -> bool:
        result = self._run_root_command(
            "/usr/bin/systemctl",
            "is-active",
            self.service_name,
            allowed_returncodes=(0, 3, 4),
        )
        return result.returncode == 0 and result.stdout.strip() == "active"

    def _schedule_stop(self, duration_minutes: int) -> None:
        self._run_root_command(
            "/usr/bin/systemd-run",
            f"--unit={self.timer_unit}",
            "--replace",
            f"--on-active={duration_minutes}m",
            "/usr/bin/systemctl",
            "stop",
            self.service_name,
        )

    def _cancel_pending_stop(self) -> None:
        self._run_root_command(
            "/usr/bin/systemd-run",
            f"--unit={self.timer_unit}",
            "--replace",
            "--on-active=1s",
            "/usr/bin/true",
        )

    def status(self) -> SupportTunnelState:
        state = self._load_state()
        config = self._read_config(require_complete=False)
        if config:
            state.port = config.tunnel_port
        state.active = self._service_is_active()
        state.error = self._configuration_error()
        return state

    def open(self, *, duration_minutes: int) -> SupportTunnelState:
        if duration_minutes not in self.allowed_durations:
            allowed = ", ".join(str(value) for value in sorted(self.allowed_durations))
            raise SupportTunnelError(f"Duur moet een van deze waarden zijn: {allowed}.")
        self._require_runtime_tools(need_timer=True)
        config = self._read_config(require_complete=True)
        if config is None:
            raise SupportTunnelError("Remote support configuratie ontbreekt.")
        key_path = Path(config.tunnel_key_path).expanduser()
        if not key_path.exists():
            raise SupportTunnelError(
                f"Tunnel key niet gevonden op {key_path}. Draai eerst scripts/setup-tunnel-key.sh.",
            )
        self._run_root_command("/usr/bin/systemctl", "start", self.service_name)
        try:
            self._schedule_stop(duration_minutes)
        except SupportTunnelError:
            self._run_root_command(
                "/usr/bin/systemctl",
                "stop",
                self.service_name,
                allowed_returncodes=(0, 5),
            )
            raise
        state = SupportTunnelState(
            active=True,
            expires_at=_utcnow() + timedelta(minutes=duration_minutes),
            port=config.tunnel_port,
            error=None,
        )
        self._persist_state(state)
        return state

    def close(self) -> SupportTunnelState:
        config = self._read_config(require_complete=False)
        if self._service_is_active():
            self._run_root_command("/usr/bin/systemctl", "stop", self.service_name)
        if Path("/usr/bin/systemd-run").exists():
            self._cancel_pending_stop()
        state = SupportTunnelState(
            active=False,
            expires_at=None,
            port=config.tunnel_port if config else None,
            error=self._configuration_error(),
        )
        self._persist_state(state)
        return state
