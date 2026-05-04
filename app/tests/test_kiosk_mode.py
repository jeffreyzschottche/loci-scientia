import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pydantic import ValidationError

from app.backend.kiosk_mode import KioskModeError, KioskModeManager
from app.backend.schemas import KioskModeRequest


class KioskModeRequestTests(unittest.TestCase):
    def test_mode_must_be_known(self) -> None:
        with self.assertRaises(ValidationError):
            KioskModeRequest(mode="weird")

    def test_reboot_defaults_to_false(self) -> None:
        req = KioskModeRequest(mode="enabled")
        self.assertFalse(req.reboot)


class KioskModeManagerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.state_path = base / "kiosk-mode"
        self.toggle_path = base / "aitje-kiosk-toggle"
        self.toggle_path.write_text("#!/bin/bash\nexit 0\n", encoding="utf-8")
        self.toggle_path.chmod(0o755)
        self.manager = KioskModeManager(
            state_path=self.state_path,
            toggle_binary=self.toggle_path,
        )

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_status_defaults_to_disabled_when_state_missing(self) -> None:
        self.assertEqual(self.manager.status().mode, "disabled")

    def test_status_reads_enabled_value(self) -> None:
        self.state_path.write_text("enabled\n", encoding="utf-8")
        self.assertEqual(self.manager.status().mode, "enabled")

    def test_status_unknown_value_falls_back_to_disabled(self) -> None:
        self.state_path.write_text("garbage\n", encoding="utf-8")
        self.assertEqual(self.manager.status().mode, "disabled")

    def test_set_mode_invokes_toggle_and_reads_back_state(self) -> None:
        completed = subprocess.CompletedProcess(args=[], returncode=0, stdout="ok", stderr="")

        def fake_run(cmd, **kwargs):
            self.state_path.write_text("enabled\n", encoding="utf-8")
            self.assertIn(str(self.toggle_path), cmd)
            self.assertIn("enable", cmd)
            self.assertNotIn("--reboot", cmd)
            return completed

        with patch("app.backend.kiosk_mode.subprocess.run", side_effect=fake_run):
            with patch("app.backend.kiosk_mode.os.geteuid", return_value=0):
                state = self.manager.set_mode("enabled")

        self.assertEqual(state.mode, "enabled")
        self.assertFalse(state.reboot_scheduled)
        self.assertEqual(state.log, "ok")

    def test_set_mode_passes_reboot_flag(self) -> None:
        captured = {}

        def fake_run(cmd, **kwargs):
            captured["cmd"] = cmd
            self.state_path.write_text("disabled\n", encoding="utf-8")
            return subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")

        with patch("app.backend.kiosk_mode.subprocess.run", side_effect=fake_run):
            with patch("app.backend.kiosk_mode.os.geteuid", return_value=0):
                state = self.manager.set_mode("disabled", reboot=True)

        self.assertIn("--reboot", captured["cmd"])
        self.assertTrue(state.reboot_scheduled)

    def test_set_mode_raises_when_toggle_missing(self) -> None:
        self.toggle_path.unlink()
        with self.assertRaises(KioskModeError) as ctx:
            self.manager.set_mode("enabled")
        self.assertEqual(ctx.exception.status_code, 500)

    def test_set_mode_propagates_failure_with_stderr(self) -> None:
        failed = subprocess.CompletedProcess(
            args=[], returncode=1, stdout="", stderr="boom"
        )
        with patch("app.backend.kiosk_mode.subprocess.run", return_value=failed):
            with patch("app.backend.kiosk_mode.os.geteuid", return_value=0):
                with self.assertRaises(KioskModeError) as ctx:
                    self.manager.set_mode("enabled")
        self.assertEqual(ctx.exception.status_code, 502)
        self.assertIn("boom", str(ctx.exception))

    def test_set_mode_translates_sudo_failure(self) -> None:
        failed = subprocess.CompletedProcess(
            args=[],
            returncode=1,
            stdout="",
            stderr="sudo: a password is required",
        )
        with patch("app.backend.kiosk_mode.subprocess.run", return_value=failed):
            with patch("app.backend.kiosk_mode.os.geteuid", return_value=0):
                with self.assertRaises(KioskModeError) as ctx:
                    self.manager.set_mode("enabled")
        self.assertEqual(ctx.exception.status_code, 500)
        self.assertIn("sudoers", str(ctx.exception).lower())

    def test_set_mode_translates_timeout(self) -> None:
        with patch(
            "app.backend.kiosk_mode.subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd="x", timeout=1),
        ):
            with patch("app.backend.kiosk_mode.os.geteuid", return_value=0):
                with self.assertRaises(KioskModeError) as ctx:
                    self.manager.set_mode("enabled")
        self.assertEqual(ctx.exception.status_code, 504)


if __name__ == "__main__":
    unittest.main()
