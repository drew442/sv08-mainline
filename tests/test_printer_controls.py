"""Offline contract and pinned Klippy file-output checks for inactive controls.

Run with ``python3 -m unittest tests/test_printer_controls.py``. The file-output
test uses the pinned source in the primary checkout and needs these existing
offline inputs, or explicit replacements:

* SV08_KLIPPER_PYTHON: Python with the pinned Klippy dependencies installed.
* SV08_KLIPPER_DICT: a file-output dictionary built from the pinned MCU source.

No hardware, live service, or private machine configuration is used.
"""

import configparser
import json
import os
from pathlib import Path
import socket
import subprocess
import tempfile
import time
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONTROLS = ROOT / "configs/commissioning/test-sv08-01-print-controls.cfg"
PINNED_KLIPPER = "f0892d82b0f1c1228454f09eb508eddde2250f4b"
GCODE_PATH = "/run/sv08/printer_data/gcodes"
SECTIONS = ("virtual_sdcard", "pause_resume", "display_status", "respond")


def primary_checkout():
    git_dir = subprocess.check_output(
        ["git", "rev-parse", "--git-common-dir"], cwd=ROOT, text=True
    ).strip()
    return Path(git_dir).resolve().parent


def pinned_source():
    gitlink = subprocess.check_output(
        ["git", "rev-parse", "HEAD:upstream/klipper"], cwd=ROOT, text=True
    ).strip()
    if gitlink != PINNED_KLIPPER:
        raise AssertionError(f"worktree Klipper gitlink changed: {gitlink}")
    for checkout in (ROOT, primary_checkout()):
        source = checkout / "upstream/klipper"
        if (source / "klippy/klippy.py").is_file():
            revision = subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=source, text=True
            ).strip()
            if revision == PINNED_KLIPPER:
                return source
    raise AssertionError("pinned Klipper source is not checked out")


def parse_controls():
    parser = configparser.ConfigParser(interpolation=None, strict=True)
    parser.read(CONTROLS)
    return parser


class KlippyRPC:
    def __init__(self, path):
        self.socket = socket.socket(socket.AF_UNIX)
        self.socket.settimeout(5)
        self.path = path
        self.buffer = b""
        self.counter = 0
        self.events = []

    def connect(self, process):
        for _ in range(300):
            try:
                self.socket.connect(str(self.path))
                return
            except (FileNotFoundError, ConnectionRefusedError):
                if process.poll() is not None:
                    raise AssertionError("Klippy exited before API connection")
                time.sleep(0.05)
        raise AssertionError("Klippy API did not appear")

    def call(self, method, params=None):
        self.counter += 1
        request = {"id": self.counter, "method": method, "params": params or {}}
        self.socket.sendall(json.dumps(request).encode() + b"\x03")
        while True:
            while b"\x03" not in self.buffer:
                self.buffer += self.socket.recv(65536)
            raw, self.buffer = self.buffer.split(b"\x03", 1)
            reply = json.loads(raw)
            self.events.append(reply)
            if reply.get("id") == self.counter:
                if "error" in reply:
                    raise AssertionError(reply)
                return reply["result"]

    def script(self, commands):
        return self.call("gcode/script", {"script": commands})

    def status(self):
        objects = {name: None for name in (
            "pause_resume", "virtual_sdcard", "print_stats", "display_status",
            "heater_generic fixture",
        )}
        return self.call("objects/query", {"objects": objects})["status"]

    def wait_state(self, expected):
        for _ in range(160):
            result = self.status()
            if result["print_stats"]["state"] == expected:
                return result
            time.sleep(0.05)
        raise AssertionError(f"wanted {expected}; got {result}")


class PrinterControlsTests(unittest.TestCase):
    def test_pc01_only_four_upstream_sections(self):
        cfg = parse_controls()
        self.assertEqual(tuple(cfg.sections()), SECTIONS)
        self.assertEqual(dict(cfg.items("virtual_sdcard")), {"path": GCODE_PATH})
        for section in SECTIONS[1:]:
            self.assertEqual(dict(cfg.items(section)), {})
            self.assertTrue(
                (pinned_source() / "klippy/extras" / f"{section}.py").is_file()
            )
        self.assertTrue(
            (pinned_source() / "klippy/extras/virtual_sdcard.py").is_file()
        )
        text = CONTROLS.read_text()
        self.assertNotRegex(text, r"(?m)^\s*(?:on_error_gcode|\[gcode_macro|\[display\])")
        self.assertNotIn("REPLACE_", text)

    def test_pc04_upstream_error_default_is_preserved(self):
        self.assertNotIn("on_error_gcode", parse_controls()["virtual_sdcard"])
        source = (pinned_source() / "klippy/extras/virtual_sdcard.py").read_text()
        self.assertIn("DEFAULT_ERROR_GCODE", source)
        self.assertRegex(source, r"(?s)DEFAULT_ERROR_GCODE\s*=.*?TURN_OFF_HEATERS")
        self.assertIn("config, 'on_error_gcode', DEFAULT_ERROR_GCODE", source)

    def test_pc06_host_paths_stay_coherent(self):
        klipper = (ROOT / "configs/host-os/systemd/sv08-klipper.service").read_text()
        moonraker = (ROOT / "configs/host-os/systemd/sv08-moonraker.service").read_text()
        moonraker_cfg = (ROOT / "configs/host-os/moonraker.conf").read_text()
        self.assertIn("/run/sv08/printer_data/config/printer.cfg", klipper)
        self.assertIn("/run/sv08/printer_data/config/moonraker.conf", moonraker)
        self.assertIn(" -d /run/sv08/printer_data", moonraker)
        self.assertIn("/run/sv08/printer_data/comms/klippy.sock", moonraker_cfg)
        mounts = (ROOT / "runtime/sv08_mounts.py").read_text()
        state = (ROOT / "runtime/sv08_state.py").read_text()
        self.assertIn("'run/sv08/printer_data'", mounts)
        self.assertIn("('gcodes', 'timelapse')", mounts)
        self.assertIn("'shared/gcodes'", state)

    def test_pc08_commissioning_dependencies(self):
        for path in (
            ROOT / "docs/hardware/test-sv08-01-commissioning-session.md",
            ROOT / "docs/hardware/coordinated-human-tasks.md",
        ):
            self.assertTrue(path.is_file())
            content = path.read_text()
            for gate in ("H01", "H02", "H05", "H06"):
                self.assertIn(gate, content)
        comments = CONTROLS.read_text()
        for gate in ("H01", "H02", "H05", "H06"):
            self.assertIn(gate, comments)

    def test_pc03_pc04_pc05_pinned_file_output_behavior(self):
        source = pinned_source()
        checkout = primary_checkout()
        default_python = (
            checkout / "build/printer-interface-prep-20260918/venv/bin/python"
        )
        default_dict = (
            checkout / "artifacts/test-sv08-01-mcu-usb-v1/klipper.dict"
        )
        python = Path(os.environ.get("SV08_KLIPPER_PYTHON", default_python))
        dictionary = Path(os.environ.get("SV08_KLIPPER_DICT", default_dict))
        self.assertTrue(python.is_file(), f"Klippy Python missing: {python}")
        self.assertTrue(dictionary.is_file(), f"MCU dictionary missing: {dictionary}")
        self.assertTrue(
            json.loads(dictionary.read_text())["version"].startswith(PINNED_KLIPPER[:7])
        )

        with tempfile.TemporaryDirectory(prefix="sv08-print-controls-") as tmp:
            fixture = Path(tmp)
            gcodes = fixture / "gcodes"
            gcodes.mkdir()
            (gcodes / "pause.gcode").write_text(
                "RESPOND MSG=BEGIN\nPAUSE\nRESPOND MSG=TAIL\n"
            )
            (gcodes / "error.gcode").write_text(
                "RESPOND MSG=ERROR_BEGIN\nM73 P1.2.3\nRESPOND MSG=ERROR_TAIL\n"
            )
            # The tracked path is a host service contract. Substitute only that
            # path for this disposable fixture; all four sections stay identical.
            fixture_include = fixture / "print-controls.cfg"
            fixture_include.write_text(
                CONTROLS.read_text().replace(GCODE_PATH, str(gcodes))
            )
            config = fixture / "printer.cfg"
            config.write_text(
                "[include print-controls.cfg]\n"
                "[mcu]\nserial: /dev/null\n"
                "[printer]\nkinematics: none\nmax_velocity: 100\nmax_accel: 1000\n"
                "[heater_generic fixture]\nheater_pin: PA0\n"
                "sensor_type: EPCOS 100K B57560G104F\n"
                "sensor_pin: PA1\ncontrol: watermark\nmin_temp: 0\nmax_temp: 100\n"
            )
            log_path = fixture / "klippy.log"
            output_path = fixture / "mcu.output"
            command = [
                str(python), str(source / "klippy/klippy.py"), str(config),
                "-I", str(fixture / "tty"), "-a", str(fixture / "api"),
                "-o", str(output_path), "-d", str(dictionary),
                "-l", str(log_path),
            ]
            with (fixture / "stdout.log").open("w") as stdout:
                process = subprocess.Popen(
                    command, cwd=fixture, stdout=stdout, stderr=subprocess.STDOUT
                )
                rpc = KlippyRPC(fixture / "api")
                try:
                    rpc.connect(process)
                    for _ in range(300):
                        info = rpc.call("info")
                        if info["state"] == "ready":
                            break
                        time.sleep(0.05)
                    self.assertEqual(info["state"], "ready", log_path.read_text())
                    rpc.call("gcode/subscribe_output", {
                        "response_template": {"output": True}
                    })
                    rpc.script("SDCARD_PRINT_FILE FILENAME=pause.gcode")
                    paused = rpc.wait_state("paused")
                    self.assertTrue(paused["pause_resume"]["is_paused"])
                    self.assertGreater(paused["virtual_sdcard"]["file_position"], 0)
                    rpc.script("RESUME")
                    resumed = rpc.wait_state("complete")
                    self.assertFalse(resumed["pause_resume"]["is_paused"])
                    rpc.script("M23 pause.gcode\nM24")
                    self.assertTrue(rpc.wait_state("paused")["pause_resume"]["is_paused"])
                    rpc.script("CANCEL_PRINT")
                    cancelled = rpc.wait_state("cancelled")
                    self.assertFalse(cancelled["pause_resume"]["is_paused"])
                    self.assertFalse(cancelled["virtual_sdcard"]["is_active"])

                    rpc.script("SET_HEATER_TEMPERATURE HEATER=fixture TARGET=40")
                    self.assertEqual(
                        rpc.status()["heater_generic fixture"]["target"], 40
                    )
                    rpc.script("SDCARD_PRINT_FILE FILENAME=error.gcode")
                    error = rpc.wait_state("error")
                    self.assertEqual(error["heater_generic fixture"]["target"], 0)
                    self.assertIn("M73", error["print_stats"]["message"])

                    rpc.script(
                        "M73 P42\nM117 probe message\nM118 response one\n"
                        "RESPOND MSG=\"response two\""
                    )
                    message = rpc.status()["display_status"]
                    self.assertEqual(message["progress"], 0.42)
                    self.assertEqual(message["message"], "probe message")
                    rpc.script("SET_DISPLAY_TEXT MSG=\"explicit message\"")
                    self.assertEqual(
                        rpc.status()["display_status"]["message"],
                        "explicit message",
                    )
                    outputs = [
                        item["params"]["response"] for item in rpc.events
                        if item.get("output") is True
                        and "response" in item.get("params", {})
                    ]
                    joined = "\n".join(outputs)
                    self.assertIn("echo: BEGIN", joined)
                    self.assertIn("echo: TAIL", joined)
                    self.assertIn("echo: response one", joined)
                    self.assertIn("echo: response two", joined)
                    self.assertNotIn("ERROR_TAIL", joined)
                except Exception as exc:
                    detail = log_path.read_text()[-1800:] if log_path.exists() else "no Klippy log"
                    raise AssertionError(f"{exc}\nKlippy log tail:\n{detail}") from exc
                finally:
                    rpc.socket.close()
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait(timeout=5)


if __name__ == "__main__":
    unittest.main()
