import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, call

from pydantic import ValidationError

from app.backend.schemas import SupportTunnelRequest
from app.backend.support_tunnel import SupportTunnelError, SupportTunnelManager


class SupportTunnelRequestTests(unittest.TestCase):
    def test_open_requires_allowed_duration(self) -> None:
        with self.assertRaises(ValidationError):
            SupportTunnelRequest(action="open", duration_minutes=45)

    def test_close_clears_duration(self) -> None:
        req = SupportTunnelRequest(action="close", duration_minutes=120)
        self.assertIsNone(req.duration_minutes)


class SupportTunnelManagerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        base = Path(self.temp_dir.name)
        self.env_path = base / ".env"
        self.state_path = base / "tunnel-state.json"
        self.key_path = base / "tunnel_key"
        self.key_path.write_text("dummy-key", encoding="utf-8")
        self.env_path.write_text(
            "\n".join(
                [
                    "JUMP_SERVER_IP=jump.example.com",
                    "TUNNEL_PORT=10001",
                    "TUNNEL_USER=support-tunnel",
                    f"TUNNEL_KEY_PATH={self.key_path}",
                ]
            ),
            encoding="utf-8",
        )
        self.manager = SupportTunnelManager(env_path=self.env_path, state_path=self.state_path)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_status_reads_port_from_env(self) -> None:
        self.manager._service_is_active = Mock(return_value=False)  # type: ignore[method-assign]
        state = self.manager.status()
        self.assertFalse(state.active)
        self.assertEqual(state.port, 10001)
        self.assertIsNone(state.error)

    def test_open_persists_expiry_and_port(self) -> None:
        self.manager._require_runtime_tools = Mock()  # type: ignore[method-assign]
        self.manager._run_root_command = Mock()  # type: ignore[method-assign]
        self.manager._schedule_stop = Mock()  # type: ignore[method-assign]

        state = self.manager.open(duration_minutes=60)

        self.assertTrue(state.active)
        self.assertEqual(state.port, 10001)
        self.manager._run_root_command.assert_called_once_with(  # type: ignore[attr-defined]
            "/usr/bin/systemctl",
            "start",
            "aitje-tunnel",
        )
        self.manager._schedule_stop.assert_called_once_with(60)  # type: ignore[attr-defined]
        payload = json.loads(self.state_path.read_text(encoding="utf-8"))
        self.assertEqual(payload["port"], 10001)
        self.assertTrue(payload["active"])
        self.assertIn("expires_at", payload)

    def test_open_rolls_back_when_timer_setup_fails(self) -> None:
        self.manager._require_runtime_tools = Mock()  # type: ignore[method-assign]
        self.manager._run_root_command = Mock()  # type: ignore[method-assign]
        self.manager._schedule_stop = Mock(  # type: ignore[method-assign]
            side_effect=SupportTunnelError("timer failed", status_code=502)
        )

        with self.assertRaises(SupportTunnelError):
            self.manager.open(duration_minutes=30)

        self.manager._run_root_command.assert_has_calls(  # type: ignore[attr-defined]
            [
                call("/usr/bin/systemctl", "start", "aitje-tunnel"),
                call(
                    "/usr/bin/systemctl",
                    "stop",
                    "aitje-tunnel",
                    allowed_returncodes=(0, 5),
                ),
            ]
        )


if __name__ == "__main__":
    unittest.main()
