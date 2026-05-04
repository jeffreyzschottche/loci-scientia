from __future__ import annotations

import logging
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Optional

logger = logging.getLogger(__name__)

KioskMode = Literal["enabled", "disabled"]


@dataclass
class KioskModeState:
    mode: KioskMode = "disabled"
    reboot_scheduled: bool = False
    log: Optional[str] = None
    error: Optional[str] = None

    def to_response(self) -> dict:
        return {
            "mode": self.mode,
            "reboot_scheduled": self.reboot_scheduled,
            "log": self.log,
            "error": self.error,
        }


class KioskModeError(RuntimeError):
    def __init__(self, message: str, *, status_code: int = 400) -> None:
        super().__init__(message)
        self.status_code = status_code


class KioskModeManager:
    """Read and toggle the kiosk-mode state file via aitje-kiosk-toggle."""

    def __init__(
        self,
        *,
        state_path: Optional[Path] = None,
        toggle_binary: Optional[Path] = None,
        timeout_seconds: int = 30,
    ) -> None:
        self.state_path = (state_path or Path("/etc/aitje/kiosk-mode")).expanduser()
        self.toggle_binary = (
            toggle_binary or Path("/usr/local/bin/aitje-kiosk-toggle")
        ).expanduser()
        self.timeout_seconds = timeout_seconds

    def _read_mode(self) -> KioskMode:
        try:
            raw = self.state_path.read_text(encoding="utf-8").strip().lower()
        except FileNotFoundError:
            return "disabled"
        except OSError:
            return "disabled"
        if raw == "enabled":
            return "enabled"
        return "disabled"

    def status(self) -> KioskModeState:
        return KioskModeState(mode=self._read_mode())

    def _sudo_prefix(self) -> list[str]:
        if os.geteuid() == 0:
            return []
        if shutil.which("sudo") is None:
            raise KioskModeError(
                "sudo ontbreekt. Installeer sudoers/aitje-kiosk-toggle of draai de backend als root.",
                status_code=500,
            )
        return ["sudo", "-n"]

    def _ensure_toggle_available(self) -> None:
        if not self.toggle_binary.exists():
            raise KioskModeError(
                f"aitje-kiosk-toggle ontbreekt op {self.toggle_binary}. "
                "Draai eerst scripts/kiosk/install.sh.",
                status_code=500,
            )

    def set_mode(self, mode: KioskMode, *, reboot: bool = False) -> KioskModeState:
        if mode not in ("enabled", "disabled"):
            raise KioskModeError(f"Onbekende kiosk mode: {mode}")
        self._ensure_toggle_available()
        action = "enable" if mode == "enabled" else "disable"
        command: list[str] = [*self._sudo_prefix(), str(self.toggle_binary), action]
        if reboot:
            command.append("--reboot")

        try:
            result = subprocess.run(
                command,
                check=False,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
            )
        except FileNotFoundError as exc:
            raise KioskModeError(
                f"Commando niet gevonden: {command[0]}", status_code=500
            ) from exc
        except subprocess.TimeoutExpired as exc:
            raise KioskModeError(
                "aitje-kiosk-toggle reageerde niet binnen de tijdslimiet.",
                status_code=504,
            ) from exc

        combined_output = ((result.stdout or "") + (result.stderr or "")).strip() or None
        if result.returncode != 0:
            detail = combined_output or f"aitje-kiosk-toggle exitcode {result.returncode}"
            detail_lower = detail.lower()
            if "password is required" in detail_lower or "sudoers" in detail_lower:
                raise KioskModeError(
                    "aitje mag aitje-kiosk-toggle nog niet zonder wachtwoord beheren. "
                    "Installeer eerst sudoers/aitje-kiosk-toggle.",
                    status_code=500,
                )
            raise KioskModeError(detail, status_code=502)

        new_mode = self._read_mode()
        # The toggle script writes the state file before invoking reboot, so
        # reading it after the call always reflects the requested mode.
        if new_mode != mode:
            logger.warning(
                "Kiosk state file laat %r zien terwijl we %r vroegen (%s).",
                new_mode,
                mode,
                self.state_path,
            )
        return KioskModeState(
            mode=new_mode,
            reboot_scheduled=reboot,
            log=combined_output,
        )
