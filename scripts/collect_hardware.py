#!/usr/bin/env python3
"""Inspect a Linux printer host using bounded reads and optional read-only tools.

Emit a private JSON report to stdout; do not open MCU ports or change the printer.
Python 3.7+ standard library only. No upstream patch is needed for this project
evidence collector; retire it if equivalent upstream tooling covers these fields.
"""

import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys


MAX_READ = 65536
FILES = (
    "/etc/os-release",
    "/proc/version",
    "/proc/meminfo",
    "/proc/device-tree/model",
    "/proc/device-tree/compatible",
)
BOOT_KEYS = {"fdtfile", "overlay_prefix", "overlays", "console", "rootdev", "rootfstype"}


def read_evidence(path):
    """Include explicit absence/error and truncation, not an inferred value."""
    try:
        with path.open("rb") as handle:
            data = handle.read(MAX_READ + 1)
    except OSError as exc:
        return {"status": "unavailable", "error": type(exc).__name__}
    if len(data) > MAX_READ:
        return {"status": "too-large", "limit_bytes": MAX_READ}
    return {
        "status": "read",
        "sha256": hashlib.sha256(data).hexdigest(),
        "text": data.decode("utf-8", errors="replace").replace("\x00", "\n").strip(),
    }


def run_inspection(argv):
    try:
        result = subprocess.run(
            argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            timeout=10, check=False, encoding="utf-8", errors="replace",
        )
    except FileNotFoundError:
        return {"status": "unavailable", "command": argv}
    except subprocess.TimeoutExpired:
        return {"status": "timeout", "command": argv}
    except OSError as exc:
        return {"status": "unavailable", "command": argv, "error": type(exc).__name__}
    return {
        "status": "ok" if result.returncode == 0 else "failed",
        "command": argv,
        "returncode": result.returncode,
        "stdout": result.stdout[:MAX_READ],
        "stderr": result.stderr[:MAX_READ],
        "truncated": len(result.stdout) > MAX_READ or len(result.stderr) > MAX_READ,
    }


def list_entries(path):
    try:
        return sorted(path.iterdir()), None
    except OSError as exc:
        return [], type(exc).__name__


def collect(root=Path("/"), runner=run_inspection):
    root = root.resolve()
    report = {
        "format_version": 1,
        "collected_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "scope": "host-inspection-only",
        "private": True,
        "offline_fixture": root != Path("/"),
        "files": {},
        "boot_environment": {},
        "serial_links": {},
        "usb_devices": {},
        "commands": {},
        "limitations": [
            "Does not prove PCB revision, MCU chip marking, clock or bootloader offset.",
            "Does not open serial ports, send G-code, stop services or write firmware.",
            "Does not back up host storage, MCU flash or printer configuration.",
            "Report may contain serial numbers and other machine-specific identifiers.",
        ],
    }
    for name in FILES:
        report["files"][name] = read_evidence(root / name.lstrip("/"))
    for name in ("/boot/BoardEnv.txt", "/boot/armbianEnv.txt"):
        evidence = read_evidence(root / name.lstrip("/"))
        if evidence["status"] == "read":
            settings = []
            for line in evidence.pop("text").splitlines():
                key, separator, value = line.strip().partition("=")
                if separator and key in BOOT_KEYS:
                    settings.append({"key": key, "value": value})
            evidence["selected_settings"] = settings
        report["boot_environment"][name] = evidence
    for directory in ("/dev/serial/by-id", "/dev/serial/by-path"):
        entries, error = list_entries(root / directory.lstrip("/"))
        links = []
        for path in entries:
            if path.is_symlink():
                # Read link text only: never open a serial device.
                try:
                    links.append({"name": path.name, "target": os.readlink(str(path))})
                except OSError as exc:
                    links.append({"name": path.name, "error": type(exc).__name__})
        report["serial_links"][directory] = {
            "status": "unavailable" if error else "listed", "error": error, "links": links,
        }
    entries, error = list_entries(root / "sys/bus/usb/devices")
    devices = []
    for path in entries:
        if not (path / "idVendor").exists():
            continue
        devices.append({
            "sysfs_name": path.name,
            "attributes": {key: read_evidence(path / key) for key in (
                "idVendor", "idProduct", "manufacturer", "product", "serial",
            )},
        })
    report["usb_devices"] = {
        "status": "unavailable" if error else "listed", "error": error, "devices": devices,
    }
    # Fixture reads must never accidentally inspect the machine running tests.
    if root == Path("/"):
        for key, argv in (
            ("kernel", ["uname", "-rm"]),
            ("storage", ["lsblk", "--json", "--bytes", "--output",
                         "NAME,TYPE,SIZE,FSTYPE,MOUNTPOINT,MODEL"]),
            ("usb", ["lsusb"]),
        ):
            report["commands"][key] = runner(argv)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    if not sys.platform.startswith("linux"):
        parser.error("run this collector on the Linux printer host")
    json.dump(collect(), sys.stdout, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
