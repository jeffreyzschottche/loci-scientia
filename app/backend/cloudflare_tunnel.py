from __future__ import annotations

import logging
import os
import subprocess
import threading
import urllib.error
import urllib.request
from pathlib import Path


logger = logging.getLogger(__name__)
_status_lock = threading.Lock()
_last_logged_signature: str | None = None


def _service_is_active() -> bool:
    if not shutil_which("systemctl"):
        return False
    try:
        result = subprocess.run(
            ["systemctl", "is-active", "--quiet", "cloudflared.service"],
            capture_output=True,
            check=False,
            timeout=3,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return result.returncode == 0


def shutil_which(binary: str) -> str | None:
    for path in os.environ.get("PATH", "").split(os.pathsep):
        candidate = Path(path) / binary
        if candidate.exists() and os.access(candidate, os.X_OK):
            return str(candidate)
    return None


def _metrics_ready(url: str) -> tuple[bool, str | None]:
    try:
        with urllib.request.urlopen(url, timeout=2) as response:
            return response.status == 200, None
    except urllib.error.URLError as exc:
        return False, str(exc.reason)
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)


def _support_ssh_enabled(state_file: Path) -> bool:
    try:
        return state_file.read_text(encoding="utf-8").strip() == "1"
    except OSError:
        return os.environ.get("CF_TUNNEL_ENABLED", "false").lower() == "true"


def _resolve_device_id() -> str:
    return (
        os.environ.get("CF_DEVICE_ID")
        or os.environ.get("AITJE_DEVICE_ID")
        or os.environ.get("DEVICE_HOSTNAME")
        or "aitje-device"
    )


def _resolve_configured() -> bool:
    if os.environ.get("CF_TUNNEL_ENABLED", "true").lower() != "true":
        return False
    if os.environ.get("CF_TUNNEL_TOKEN") or os.environ.get("AITJE_TUNNEL_TOKEN"):
        return True
    config_path = Path(
        os.environ.get("CF_CLOUDFLARED_CONFIG_PATH")
        or os.environ.get("AITJE_CLOUDFLARED_CONFIG_PATH", "/etc/cloudflared/config.yml")
    )
    credentials_path = Path(
        os.environ.get("CF_CLOUDFLARED_CREDENTIALS_PATH")
        or os.environ.get("AITJE_CLOUDFLARED_CREDENTIALS_PATH", "/etc/cloudflared/credentials.json")
    )
    return config_path.exists() or credentials_path.exists()


def get_cloudflare_tunnel_status() -> dict:
    config_path = Path(
        os.environ.get("CF_CLOUDFLARED_CONFIG_PATH")
        or os.environ.get("AITJE_CLOUDFLARED_CONFIG_PATH", "/etc/cloudflared/config.yml")
    )
    state_file = Path(
        os.environ.get("CF_CLOUDFLARED_SUPPORT_STATE_FILE")
        or os.environ.get(
            "AITJE_CLOUDFLARED_SUPPORT_STATE_FILE",
            "/var/lib/aitje/cloudflared/support_ssh_enabled",
        )
    )
    metrics_host = os.environ.get("CF_CLOUDFLARED_METRICS_HOST") or os.environ.get("AITJE_CLOUDFLARED_METRICS_HOST", "127.0.0.1")
    metrics_port = os.environ.get("CF_CLOUDFLARED_METRICS_PORT") or os.environ.get("AITJE_CLOUDFLARED_METRICS_PORT", "45231")
    metrics_url = f"http://{metrics_host}:{metrics_port}/ready"
    service_active = _service_is_active()
    ready, error = _metrics_ready(metrics_url) if service_active else (False, None)
    configured = _resolve_configured()
    tunnel_id = None

    if config_path.exists():
        try:
            for line in config_path.read_text(encoding="utf-8").splitlines():
                if line.startswith("tunnel:"):
                    tunnel_id = line.split(":", 1)[1].strip()
                    break
        except OSError:
            pass

    status = "disabled"
    if configured:
        if service_active and ready:
            status = "connected"
        elif service_active:
            status = "degraded"
        else:
            status = "stopped"

    payload = {
        "configured": configured,
        "status": status,
        "service_active": service_active,
        "ready": ready,
        "ssh_enabled": _support_ssh_enabled(state_file),
        "device_id": _resolve_device_id(),
        "domain": os.environ.get("CF_DOMAIN") or os.environ.get("AITJE_DOMAIN", "aitje.nl"),
        "config_path": str(config_path),
        "tunnel_id": tunnel_id,
        "metrics_url": metrics_url,
        "error": error,
    }
    _log_status_transition(payload)
    return payload


def _log_status_transition(payload: dict) -> None:
    global _last_logged_signature

    signature = f"{payload['status']}:{payload['service_active']}:{payload['ready']}:{payload['ssh_enabled']}"
    with _status_lock:
        if signature == _last_logged_signature:
            return
        _last_logged_signature = signature

    level = logging.INFO
    if payload["configured"] and payload["status"] != "connected":
        level = logging.WARNING

    logger.log(
        level,
        "cloudflared status=%s service_active=%s ready=%s ssh_enabled=%s metrics=%s error=%s",
        payload["status"],
        payload["service_active"],
        payload["ready"],
        payload["ssh_enabled"],
        payload["metrics_url"],
        payload["error"] or "-",
    )
