"""Offline behavior checks; these do not validate a printer."""

import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch


spec = importlib.util.spec_from_file_location(
    "collector", Path(__file__).resolve().parents[1] / "scripts/collect_hardware.py"
)
collector = importlib.util.module_from_spec(spec)
spec.loader.exec_module(collector)


class CollectorTests(unittest.TestCase):
    def test_fixture_identity_missing_fields_and_no_commands(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            dt = root / "proc/device-tree"
            dt.mkdir(parents=True)
            (dt / "compatible").write_bytes(b"sovol,example\0allwinner,sun50i-h616\0")
            serial = root / "dev/serial/by-id"
            serial.mkdir(parents=True)
            (serial / "test-mcu").symlink_to("../../ttyACM1")
            with patch.object(collector, "run_inspection") as runner:
                report = collector.collect(root, runner=runner)
            runner.assert_not_called()
            self.assertTrue(report["offline_fixture"])
            self.assertEqual(report["files"]["/etc/os-release"]["status"], "unavailable")
            self.assertEqual(report["files"]["/proc/device-tree/compatible"]["text"],
                             "sovol,example\nallwinner,sun50i-h616")
            self.assertEqual(report["serial_links"]["/dev/serial/by-id"]["links"],
                             [{"name": "test-mcu", "target": "../../ttyACM1"}])
            json.dumps(report)

    def test_boot_selection_preserves_duplicate_keys_and_omits_credentials(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "boot").mkdir()
            env = root / "boot/BoardEnv.txt"
            original = b"# example\nfdtfile=board.dtb\noverlays=uart3\noverlays=spi\npassword=secret\n"
            env.write_bytes(original)
            report = collector.collect(root)
            settings = report["boot_environment"]["/boot/BoardEnv.txt"]["selected_settings"]
            self.assertEqual(settings, [{"key": "fdtfile", "value": "board.dtb"},
                                        {"key": "overlays", "value": "uart3"},
                                        {"key": "overlays", "value": "spi"}])
            self.assertNotIn("secret", json.dumps(report))
            self.assertEqual(env.read_bytes(), original)

    def test_usb_identity_without_device_access(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            usb = root / "sys/bus/usb/devices/1-1"
            usb.mkdir(parents=True)
            (usb / "idVendor").write_text("1d50\n")
            (usb / "idProduct").write_text("614e\n")
            report = collector.collect(root)
            attrs = report["usb_devices"]["devices"][0]["attributes"]
            self.assertEqual(attrs["idVendor"]["text"], "1d50")
            self.assertEqual(attrs["serial"]["status"], "unavailable")

    def test_oversized_file_is_explicitly_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory) / "large"
            file.write_bytes(b"x" * (collector.MAX_READ + 1))
            result = collector.read_evidence(file)
            self.assertEqual(result["status"], "too-large")
            self.assertNotIn("sha256", result)

    def test_command_failures_are_reported(self):
        cases = [(FileNotFoundError(), "unavailable"),
                 (PermissionError(), "unavailable"),
                 (subprocess.TimeoutExpired(["lsusb"], 10), "timeout")]
        for error, expected in cases:
            with self.subTest(expected=expected), patch.object(
                collector.subprocess, "run", side_effect=error
            ):
                self.assertEqual(collector.run_inspection(["lsusb"])["status"], expected)
        result = subprocess.CompletedProcess(["lsusb"], 1, "", "permission denied")
        with patch.object(collector.subprocess, "run", return_value=result):
            self.assertEqual(collector.run_inspection(["lsusb"])["status"], "failed")


if __name__ == "__main__":
    unittest.main()
