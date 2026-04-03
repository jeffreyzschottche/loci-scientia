import os
from pathlib import Path

from app.backend import cloudflare_tunnel


def test_cloudflare_tunnel_status_reports_disabled_when_not_configured(tmp_path, monkeypatch):
    config_path = tmp_path / "config.yml"
    state_path = tmp_path / "support_ssh_enabled"

    monkeypatch.delenv("CF_TUNNEL_TOKEN", raising=False)
    monkeypatch.setenv("CF_TUNNEL_ENABLED", "true")
    monkeypatch.setenv("CF_CLOUDFLARED_CONFIG_PATH", str(config_path))
    monkeypatch.setenv("CF_CLOUDFLARED_SUPPORT_STATE_FILE", str(state_path))
    monkeypatch.setattr(cloudflare_tunnel, "_service_is_active", lambda: False)

    status = cloudflare_tunnel.get_cloudflare_tunnel_status()

    assert status["configured"] is False
    assert status["status"] == "disabled"
    assert status["ssh_enabled"] is False


def test_cloudflare_tunnel_status_reports_connected(tmp_path, monkeypatch):
    config_path = tmp_path / "config.yml"
    config_path.write_text("tunnel: tunnel-123\n", encoding="utf-8")
    state_path = tmp_path / "support_ssh_enabled"
    state_path.write_text("1\n", encoding="utf-8")

    monkeypatch.setenv("CF_TUNNEL_ENABLED", "true")
    monkeypatch.setenv("CF_CLOUDFLARED_CONFIG_PATH", str(config_path))
    monkeypatch.setenv("CF_CLOUDFLARED_SUPPORT_STATE_FILE", str(state_path))
    monkeypatch.setattr(cloudflare_tunnel, "_service_is_active", lambda: True)
    monkeypatch.setattr(cloudflare_tunnel, "_metrics_ready", lambda url: (True, None))

    status = cloudflare_tunnel.get_cloudflare_tunnel_status()

    assert status["configured"] is True
    assert status["status"] == "connected"
    assert status["tunnel_id"] == "tunnel-123"
    assert status["ssh_enabled"] is True
