#!/usr/bin/env python3
"""Real ARM64 recovery export composition using disposable regular-file media.

Inspection is the default.  ``prepare`` creates sparse GPT fixtures and the
reviewed immutable media profile.  ``run`` boots the installed candidate with
QMP on a private Unix socket, no network and no host share.  The script never
accepts a block device path.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import stat
import subprocess
import tarfile
import tempfile
import threading
import time

REPO = Path(__file__).resolve().parents[1]
RECOVERY_BYTES = 512 * 1024**2
RECOVERY_UUID = "964ed891-6ec4-4a95-8762-e32c91260394"
SOURCE_BYTES = DESTINATION_BYTES = 128 * 1024**2
PROTECTED_BYTES = 192 * 1024**2
SOURCE_UUID = "7e25af9a-f646-4bc8-bd63-2884902365fa"
DESTINATION_UUID = "C0DE-0808"
PROTECTED_UUIDS = (
    "16c420b9-f4d7-4faf-b2ce-442e33d169a1",
    "525b0030-d63f-47a3-b21d-32f44d7dd5e0",
    "c1ec37b3-493f-4914-a83f-a41c0c7aa9dd",
)
SOURCE_PARTUUID = "a223ce55-fc0e-4933-a522-f19c769cd870"
DESTINATION_PARTUUID = "3497e8bd-a16f-48b3-a96f-7a36abdc1935"
PROTECTED_PARTUUIDS = (
    "a6bc58ac-9abe-4cbb-bda7-f3214829041d",
    "464a8449-aa72-44d4-bc64-40a390d918fb",
    "dbd8bea1-5975-4411-a29d-8d54705a6061",
)
LINUX_GUID = "0fc63daf-8483-4772-8e79-3d69d8477de4"
FAT_GUID = "c12a7328-f81f-11d2-ba4b-00a0c93ec93b"
SOURCE_START, SOURCE_SECTORS = 2048, 196608
DESTINATION_START, DESTINATION_SECTORS = 2048, 196608
PROTECTED_LAYOUT = ((2048, 120000), (122048, 120000), (242048, 120000))


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value)


def run(command, *, data=None, capture=False, timeout=180):
    return subprocess.run([str(x) for x in command], input=data, text=True,
                          capture_output=capture, check=True, timeout=timeout)


def safe_regular(path, *, fresh=False):
    path = Path(path).resolve()
    if not path.is_relative_to(REPO / "build"):
        raise ValueError("Use only build/recovery-composition-* disposable paths")
    if any(item.is_symlink() for item in (path, *path.parents)):
        raise ValueError("Symlink paths are refused")
    if fresh and path.exists():
        raise ValueError("Fresh output required")
    if path.exists() and not (path.is_dir() or stat.S_ISREG(path.stat().st_mode)):
        raise ValueError("Only directories and regular files are accepted")
    return path


def partition_image(path, size, filesystem, uuid, tree=None):
    with path.open("xb") as stream:
        stream.truncate(size)
    if filesystem == "ext4":
        command = ["mkfs.ext4", "-q", "-F", "-U", uuid, "-L", "SV08_SOURCE"]
        if tree is not None:
            command += ["-d", tree]
        run(command + [path])
    else:
        run(["mkfs.vfat", "-F", "32", "-i", uuid.replace("-", ""), "-n", "SV08_EXPORT", path])


def gpt(path, size, rows):
    with path.open("xb") as stream:
        stream.truncate(size)
    script = ["label: gpt", "unit: sectors", ""]
    for start, sectors, guid, partuuid in rows:
        script.append(f"start={start}, size={sectors}, type={guid}, uuid={partuuid}")
    run(["sfdisk", "--no-reread", "--no-tell-kernel", path], data="\n".join(script) + "\n")


def embed(disk, part, start):
    run(["dd", f"if={part}", f"of={disk}", "bs=512", f"seek={start}",
         "conv=notrunc,sparse", "status=none"])


def stable_key(value):
    return json.dumps(value["stable"], sort_keys=True, separators=(",", ":"))


def media(stable, sectors, removable, transport, partitions, filesystem="", uuid=""):
    return dict(stable=stable, sectors=sectors, removable=removable,
                transport=transport, filesystem_uuid=uuid,
                filesystem=filesystem, partitions=partitions)


def part(number, start, sectors, uuid, filesystem, partuuid):
    return dict(partition=number, start=start, sectors=sectors,
                filesystem_uuid=uuid, filesystem=filesystem, partuuid=partuuid)


def identity(stable, number, start, sectors, uuid):
    return dict(stable=stable, partition=number, start=start, sectors=sectors,
                filesystem_uuid=uuid)


def reviewed_profile():
    recovery = {"serial": "SV08-RECOVERY"}
    source = {"device/wwid": "naa.5000000000000001"}
    protected = {"device/wwid": "naa.5000000000000002"}
    destination = {"device/wwid": "naa.5000000000000003"}
    disks = [
        media(recovery, RECOVERY_BYTES // 512, False, "virtio", [], "ext4", RECOVERY_UUID),
        media(source, SOURCE_BYTES // 512, False, "scsi",
              [part(1, SOURCE_START, SOURCE_SECTORS, SOURCE_UUID, "ext4", SOURCE_PARTUUID)]),
        media(protected, PROTECTED_BYTES // 512, False, "scsi",
              [part(i + 1, start, sectors, PROTECTED_UUIDS[i], "ext4", PROTECTED_PARTUUIDS[i])
               for i, (start, sectors) in enumerate(PROTECTED_LAYOUT)]),
        media(destination, DESTINATION_BYTES // 512, True, "usb-scsi",
              [part(1, DESTINATION_START, DESTINATION_SECTORS, DESTINATION_UUID, "vfat",
                    DESTINATION_PARTUUID)]),
    ]
    source_identity = identity(source, 1, SOURCE_START, SOURCE_SECTORS, SOURCE_UUID)
    return dict(
        recovery=identity(recovery, 0, 0, RECOVERY_BYTES // 512, RECOVERY_UUID),
        source=source_identity,
        source_path="/run/sv08-recovery/source",
        media=sorted(disks, key=stable_key),
        protected=[dict(role=role, identity=identity(protected, i + 1, start, sectors,
                                                     PROTECTED_UUIDS[i]))
                   for i, (role, (start, sectors)) in enumerate(zip(
                       ("slot-a", "slot-b", "additional-protected"), PROTECTED_LAYOUT))],
        destinations={"export-usb": dict(
            identity=identity(destination, 1, DESTINATION_START, DESTINATION_SECTORS,
                              DESTINATION_UUID),
            path="/run/sv08-recovery/destinations/export-usb", label="Reviewed export USB")},
    )


def prepare(work):
    work = safe_regular(work, fresh=True)
    work.mkdir(parents=True, mode=0o700)
    tree = work / "source-tree"
    (tree / "sv08").mkdir(parents=True)
    (tree / "config" / "macros").mkdir(parents=True)
    (tree / "databases").mkdir()
    (tree / "sv08" / "state.json").write_text("{damaged registry; do not initialize\n")
    (tree / "config" / "printer.cfg").write_text("[printer]\nkinematics: corexy\n# preserved configuration\n")
    (tree / "config" / "macros" / "温度-Δ.cfg").write_text("[gcode_macro CAFÉ]\ngcode:\n  M117 café ∆\n")
    (tree / "databases" / "moonraker.db").write_bytes(b"SQLite format 3\0" + bytes(range(256)) * 32)
    (tree / "databases" / "moonraker.db-wal").write_bytes(b"SQLite-WAL\0" + b"\xa5" * 8192)
    source_part = work / "source-partition.ext4"
    partition_image(source_part, SOURCE_SECTORS * 512, "ext4", SOURCE_UUID, tree)
    gpt(work / "source.raw", SOURCE_BYTES,
        [(SOURCE_START, SOURCE_SECTORS, LINUX_GUID, SOURCE_PARTUUID)])
    embed(work / "source.raw", source_part, SOURCE_START)

    protected_rows = [(start, sectors, LINUX_GUID, PROTECTED_PARTUUIDS[i])
                      for i, (start, sectors) in enumerate(PROTECTED_LAYOUT)]
    gpt(work / "protected.raw", PROTECTED_BYTES, protected_rows)
    for i, (start, sectors) in enumerate(PROTECTED_LAYOUT):
        item = work / f"protected-{i + 1}.ext4"
        partition_image(item, sectors * 512, "ext4", PROTECTED_UUIDS[i])
        embed(work / "protected.raw", item, start)

    destination_part = work / "destination-partition.fat"
    partition_image(destination_part, DESTINATION_SECTORS * 512, "vfat", DESTINATION_UUID)
    older = work / "older-export.txt"
    older.write_text("existing destination file must survive\n")
    run(["mcopy", "-i", destination_part, older, "::older-export.txt"])
    gpt(work / "destination.raw", DESTINATION_BYTES,
        [(DESTINATION_START, DESTINATION_SECTORS, FAT_GUID, DESTINATION_PARTUUID)])
    embed(work / "destination.raw", destination_part, DESTINATION_START)
    profile = reviewed_profile()
    write(work / "media-profile.json", json.dumps(profile, sort_keys=True, indent=2) + "\n")
    hashes = {name: sha(work / name) for name in ("source.raw", "protected.raw", "destination.raw")}
    write(work / "fixture.json", json.dumps(dict(format_version=1, dirty_source=False,
          source_payload={str(p.relative_to(tree)): sha(p) for p in tree.rglob("*") if p.is_file()},
          hashes=hashes, profile_sha256=sha(work / "media-profile.json")), indent=2) + "\n")
    shutil.rmtree(tree)
    for item in work.glob("*.ext4"):
        item.unlink()
    destination_part.unlink()
    older.unlink()
    return json.loads((work / "fixture.json").read_text())


def _unpack_initrd(image, destination):
    gzip_process = subprocess.Popen(["gzip", "-dc", image], stdout=subprocess.PIPE)
    subprocess.run(["cpio", "-idmu", "--quiet"], cwd=destination,
                   stdin=gzip_process.stdout, check=True, timeout=30)
    gzip_process.stdout.close()
    if gzip_process.wait(timeout=10):
        raise subprocess.CalledProcessError(gzip_process.returncode, ["gzip", "-dc", image])


def dirty_source(candidate, fixture, selected_initrd, output, seconds=60, module_initrd=None):
    """Create a real pending ext4 journal by cutting power to a mounted guest."""
    candidate, fixture, selected_initrd = (safe_regular(candidate), safe_regular(fixture),
                                            Path(selected_initrd).resolve())
    output = safe_regular(output, fresh=True)
    if not stat.S_ISREG(selected_initrd.stat().st_mode):
        raise ValueError("Selected-guest initramfs must be a regular file")
    output.mkdir(parents=True, mode=0o700)
    unpack = output / "initramfs"
    unpack.mkdir()
    _unpack_initrd(selected_initrd, unpack)
    if module_initrd:
        module_root = output / "module-initramfs"
        module_root.mkdir()
        _unpack_initrd(Path(module_initrd).resolve(), module_root)
        for source in (module_root / "usr/lib/modules").rglob("*.ko*"):
            destination = unpack / source.relative_to(module_root)
            if not destination.exists():
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, destination)
        shutil.rmtree(module_root)
    init = """#!/bin/busybox sh
B=/bin/busybox
$B mount -t proc proc /proc
$B mount -t sysfs sysfs /sys
$B mount -t devtmpfs devtmpfs /dev
$B modprobe virtio_pci
$B modprobe virtio_scsi
$B modprobe sd_mod
$B modprobe ext4
$B mkdir -p /mnt
for n in 1 2 3 4 5 6 7 8 9 10; do [ -b /dev/sda1 ] && break; $B sleep 1; done
$B mount -t ext4 -o rw /dev/sda1 /mnt || { echo SV08_DIRTY_FAILED; $B poweroff -f; }
echo qemu-crash-created-journal > /mnt/journal-crash-marker
$B sync
echo SV08_DIRTY_READY
while true; do $B sleep 60; done
"""
    write(unpack / "init", init)
    (unpack / "init").chmod(0o755)
    packed = output / "dirty-initrd.gz"
    find = subprocess.Popen(["find", ".", "-print0"], cwd=unpack, stdout=subprocess.PIPE)
    cpio = subprocess.Popen(["cpio", "--null", "-o", "--format=newc", "--quiet"], cwd=unpack,
                            stdin=find.stdout, stdout=subprocess.PIPE)
    find.stdout.close()
    with packed.open("wb") as stream:
        gzip = subprocess.run(["gzip", "-9"], stdin=cpio.stdout, stdout=stream,
                              check=True, timeout=60)
    cpio.stdout.close()
    if find.wait(timeout=10) or cpio.wait(timeout=10):
        raise RuntimeError("Could not repack selected-guest dirty-journal initramfs")
    shutil.rmtree(unpack)
    endpoint = Path(tempfile.mkdtemp(prefix="sv08-dirty-qmp-"))
    qmp = endpoint / "qmp.sock"
    command = ["qemu-system-aarch64", "-machine", "virt", "-cpu", "cortex-a53",
               "-accel", "tcg,thread=multi", "-smp", "2", "-m", "256",
               "-kernel", candidate / "vmlinuz", "-initrd", packed, "-append", "console=ttyAMA0",
               "-device", "virtio-scsi-pci,id=scsi0",
               "-drive", f"if=none,id=source,format=raw,file={fixture / 'source.raw'},readonly=off",
               "-device", "scsi-hd,drive=source,serial=SV08-SOURCE,bus=scsi0.0,wwn=0x5000000000000001",
               "-nic", "none", "-display", "none", "-serial", "stdio",
               "-qmp", f"unix:{qmp},server=on,wait=off", "-no-reboot"]
    write(output / "command.json", json.dumps([str(x) for x in command], indent=2) + "\n")
    serial = (output / "serial.log").open("wb")
    process = subprocess.Popen([str(x) for x in command], stdin=subprocess.DEVNULL,
                               stdout=serial, stderr=subprocess.STDOUT)
    client = None
    started = time.monotonic()
    ready = False
    try:
        while process.poll() is None and time.monotonic() - started < seconds:
            if client is None and qmp.exists():
                client = QMP(qmp)
            if "SV08_DIRTY_READY" in (output / "serial.log").read_text(errors="replace"):
                ready = True
                client.call("quit")
                break
            time.sleep(.25)
        process.wait(timeout=10)
    finally:
        if process.poll() is None:
            process.kill(); process.wait(timeout=10)
        serial.close()
        shutil.rmtree(endpoint)
    if not ready:
        raise AssertionError("Dirty-journal guest never mounted and flushed the source")
    partition = output / "source-after-crash.ext4"
    with (fixture / "source.raw").open("rb") as source, partition.open("wb") as target:
        source.seek(SOURCE_START * 512)
        remaining = SOURCE_SECTORS * 512
        while remaining:
            block = source.read(min(1024 * 1024, remaining))
            if not block:
                raise ValueError("Short source partition after dirty guest")
            target.write(block)
            remaining -= len(block)
    check = subprocess.run(["e2fsck", "-fn", partition], text=True, capture_output=True,
                           timeout=60, check=False)
    if "journal" not in (check.stdout + check.stderr).lower():
        raise AssertionError("Crash-created source has no pending-journal diagnostic")
    fixture_data = json.loads((fixture / "fixture.json").read_text())
    marker = b"qemu-crash-created-journal\n"
    fixture_data["dirty_source"] = True
    fixture_data["dirty_source_method"] = "selected-arm64-guest-qmp-power-cut-while-mounted"
    fixture_data["source_payload"]["journal-crash-marker"] = hashlib.sha256(marker).hexdigest()
    fixture_data["hashes"]["source.raw"] = sha(fixture / "source.raw")
    fixture_data["dirty_guest_initrd_sha256"] = sha(packed)
    write(fixture / "fixture.json", json.dumps(fixture_data, indent=2) + "\n")
    write(output / "result.json", json.dumps(dict(ready=True, hard_qmp_quit=True,
          source_sha256=fixture_data["hashes"]["source.raw"], e2fsck_output=check.stdout + check.stderr,
          command=[str(x) for x in command]), indent=2) + "\n")
    return fixture_data


class QMP:
    def __init__(self, path):
        self.socket = socket.socket(socket.AF_UNIX)
        self.socket.settimeout(5)
        self.socket.connect(str(path))
        self.file = self.socket.makefile("rwb")
        self._read()
        self.call("qmp_capabilities")

    def _read(self):
        line = self.file.readline()
        if not line:
            raise EOFError("QMP closed")
        return json.loads(line)

    def call(self, command, arguments=None):
        self.file.write((json.dumps({"execute": command, "arguments": arguments or {}}) + "\n").encode())
        self.file.flush()
        while True:
            answer = self._read()
            if "error" in answer:
                raise RuntimeError(answer)
            if "return" in answer:
                return answer["return"]

    def key(self, *keys):
        events = [dict(type="key", data=dict(down=True, key=dict(type="qcode", data=k))) for k in keys]
        self.call("input-send-event", {"events": events})
        time.sleep(.15)
        events = [dict(type="key", data=dict(down=False, key=dict(type="qcode", data=k)))
                  for k in reversed(keys)]
        self.call("input-send-event", {"events": events})

    def text(self, value):
        """Type a small shell command through the QEMU keyboard device."""
        shifted = {"/": "slash", "-": "minus", "_": ("shift", "minus"), ".": "dot",
                   "[": "bracket_left", "]": "bracket_right", "!": ("shift", "1"),
                   ";": "semicolon", "&": ("shift", "7"), "*": ("shift", "8"),
                   "$": ("shift", "4")}
        plain = {"=": "equal", ",": "comma"}
        for char in value:
            if char == " ":
                self.key("spc")
            elif char == "\n":
                self.key("ret")
            elif char in shifted:
                keys = shifted[char]
                self.key(*keys) if isinstance(keys, tuple) else self.key(keys)
            elif char in plain:
                self.key(plain[char])
            else:
                self.key(char.lower())

    def click(self, x, y):
        mice = self.call("query-mice")
        tablet = next((item for item in mice if item.get("absolute") and
                       "tablet" in item.get("name", "").lower()), None)
        if tablet is None:
            raise RuntimeError("QEMU absolute tablet is unavailable")
        self.call("human-monitor-command", {"command-line": f"mouse_set {tablet['index']}"})
        self.call("input-send-event", {"events": [
            dict(type="abs", data=dict(axis="x", value=int(x * 32767 / 1024))),
            dict(type="abs", data=dict(axis="y", value=int(y * 32767 / 768))),
            dict(type="btn", data=dict(down=True, button="left"))]})
        time.sleep(.15)
        self.call("input-send-event", {"events": [
            dict(type="btn", data=dict(down=False, button="left"))]})

    def touch(self, x, y):
        def event(kind, axis, value, tracking):
            return dict(type="mtt", data={"type": kind, "slot": 0, "tracking-id": tracking,
                                          "axis": axis, "value": value})
        self.call("input-send-event", {"device": "video0", "events": [
            dict(type="btn", data=dict(down=True, button="touch")),
            event("begin", "x", 0, 1), event("data", "x", int(x * 32767 / 1024), 1),
            event("data", "y", int(y * 32767 / 768), 1)]})
        time.sleep(.15)
        self.call("input-send-event", {"device": "video0", "events": [
            event("end", "x", 0, -1), dict(type="btn", data=dict(down=False, button="touch"))]})


def image_policy(image):
    result = run(["debugfs", "-R", "cat /etc/sv08/recovery-media-policy.json", image],
                 capture=True)
    return json.loads(result.stdout)


def qemu_command(candidate, fixture, qmp, binding, provider, *, source_readonly=False,
                 initrd=None, replacement=False):
    return ["qemu-system-aarch64", "-machine", "virt", "-cpu", "cortex-a53",
        "-accel", "tcg,thread=multi", "-smp", "2", "-m", "768",
        "-kernel", candidate / "vmlinuz", "-initrd", initrd or candidate / "initrd.img",
        "-append", f"console=ttyAMA0 root=/dev/vda ro sv08.envelope={binding} sv08.recovery={provider} systemd.debug_shell systemd.log_target=console systemd.show_status=yes",
        "-drive", f"if=none,id=recovery,format=raw,file={candidate / 'recovery.ext4'},readonly=on",
        "-device", "virtio-blk-pci,drive=recovery,serial=SV08-RECOVERY",
        "-device", "virtio-scsi-pci,id=scsi0", "-device", "qemu-xhci,id=usb0",
        "-device", "usb-uas,id=uas0,bus=usb0.0",
        "-drive", f"if=none,id=source,format=raw,file={fixture / 'source.raw'},readonly={'on' if source_readonly else 'off'}",
        "-device", "scsi-hd,drive=source,serial=SV08-SOURCE,bus=scsi0.0,wwn=0x5000000000000001",
        "-drive", f"if=none,id=protected,format=raw,file={fixture / 'protected.raw'},readonly=on",
        "-device", "scsi-hd,drive=protected,serial=SV08-PROTECTED,bus=scsi0.0,wwn=0x5000000000000002",
        "-drive", f"if=none,id=destination,format=raw,file={fixture / 'destination.raw'},readonly=off",
        "-device", "scsi-hd,id=destination-device,drive=destination,serial=SV08-DESTINATION,bus=uas0.0,removable=on,wwn=0x5000000000000003",
        "-device", "virtio-gpu-pci,id=video0,xres=1024,yres=768",
        "-device", "virtio-multitouch-pci,display=video0", "-device", "usb-kbd",
        "-device", "usb-mouse", "-device", "usb-tablet", "-nic", "none",
        "-display", "none", "-serial", "stdio", "-qmp", f"unix:{qmp},server=on,wait=off",
        "-no-reboot"]


def add_replacement_drive(command, fixture):
    """Attach a second removable medium, initially absent from the guest bus.

    QMP replacement journeys use a distinct stable identity while preserving
    the reviewed destination path and filesystem contents.  The ordinary
    candidate is unchanged; this is only a host-side fixture operation.
    """
    replacement = fixture / "destination-replacement.raw"
    shutil.copyfile(fixture / "destination.raw", replacement)
    command.extend(["-drive", f"if=none,id=replacement,format=raw,file={replacement},readonly=off"])
    return replacement


def alter_fat_identity(image):
    """Change the FAT volume serial in a fixture copy without changing its size."""
    with image.open("r+b") as stream:
        stream.seek(DESTINATION_START * 512 + 67)
        value = int.from_bytes(stream.read(4), "little") ^ 0x5A17C0DE
        stream.seek(DESTINATION_START * 512 + 67)
        stream.write(value.to_bytes(4, "little"))
        stream.flush(); os.fsync(stream.fileno())


def corrupt_destination_raw(image, stop):
    """Continuously corrupt a data-sector range while the guest publishes an archive."""
    block = b"\x00" * 4096
    while not stop.wait(.5):
        try:
            with image.open("r+b") as stream:
                stream.seek(DESTINATION_START * 512)
                payload = stream.read(DESTINATION_SECTORS * 512)
                marker = payload.find(b"ustar")
                if marker >= 0:
                    stream.seek(DESTINATION_START * 512 + max(0, marker - 512))
                    stream.write(block); stream.flush(); os.fsync(stream.fileno())
        except OSError:
            return


def namespace_diagnostic(candidate, fixture, output, seconds=120, overrides=False):
    """Instrument /run only to report selected-guest task namespaces.

    This never supplies policy/context and is diagnosis, not acceptance evidence.
    """
    candidate, fixture = safe_regular(candidate), safe_regular(fixture)
    output = safe_regular(output, fresh=True)
    output.mkdir(parents=True, mode=0o700)
    unpack = output / "initramfs"
    unpack.mkdir()
    _unpack_initrd(candidate / "initrd.img", unpack)
    init = unpack / "init"
    original = init.read_text()
    # /run is moved into the real root before switch_root.  Stage diagnostic-only
    # units immediately before that move so PID 1 sees them as /run units.
    marker = "mount --move /run /newroot/run || fail 'move run'"
    if original.count(marker) != 1:
        raise ValueError("Selected initramfs switch_root marker changed")
    override_units = r'''
mkdir -p /run/systemd/system/systemd-udevd.service.d /run/systemd/system/systemd-logind.service.d
cat >/run/systemd/system/systemd-udevd.service.d/sv08-diagnostic-namespace.conf <<'SV08_UDEV_OVERRIDE'
[Service]
PrivateMounts=no
SV08_UDEV_OVERRIDE
cat >/run/systemd/system/systemd-logind.service.d/sv08-diagnostic-namespace.conf <<'SV08_LOGIND_OVERRIDE'
[Service]
PrivateMounts=no
PrivateTmp=no
ProtectSystem=no
ProtectHome=no
ProtectKernelModules=no
ProtectKernelLogs=no
ProtectControlGroups=no
ReadWritePaths=
SV08_LOGIND_OVERRIDE
''' if overrides else ""
    instrumentation = r'''cat >/run/sv08-namespace-report.sh <<'SV08_NS_SCRIPT'
#!/bin/sh
phase=$1
echo SV08_NAMESPACE_${phase}_BEGIN
for process in /proc/[0-9]*; do
  [ -d "$process/task" ] || continue
  pid=${process##*/}
  command=$(tr '\000' ' ' <"$process/cmdline" 2>/dev/null)
  [ -n "$command" ] || continue
  cgroup=$(tr '\n' ';' <"$process/cgroup" 2>/dev/null)
  for task in "$process"/task/[0-9]*; do
    [ -d "$task" ] || continue
    tid=${task##*/}
    mnt=$(readlink "$task/ns/mnt" 2>&1)
    pidns=$(readlink "$task/ns/pid" 2>&1)
    stat=$(cat "$task/stat" 2>/dev/null)
    printf 'SV08_NAMESPACE_TASK pid=%s tid=%s mnt=%s pidns=%s cgroup=%s command=%s stat=%s\n' "$pid" "$tid" "$mnt" "$pidns" "$cgroup" "$command" "$stat"
  done
done
echo SV08_NAMESPACE_${phase}_MOUNTS_BEGIN
cat /proc/self/mountinfo
echo SV08_NAMESPACE_${phase}_MOUNTS_END
echo SV08_NAMESPACE_${phase}_UNITS_BEGIN
systemctl list-units --all --no-legend --no-pager
echo SV08_NAMESPACE_${phase}_UNITS_END
if [ -e /run/sv08-recovery/media.lock ]; then
  lock_identity=$(stat -Lc '%d:%i' /run/sv08-recovery/media.lock)
  for fd in /proc/[0-9]*/fd/[0-9]*; do
    [ -e "$fd" ] || continue
    [ "$(stat -Lc '%d:%i' "$fd" 2>/dev/null)" = "$lock_identity" ] || continue
    pid=${fd#/proc/}; pid=${pid%%/*}
    command=$(tr '\000' ' ' <"/proc/$pid/cmdline" 2>/dev/null)
    cgroup=$(tr '\n' ';' <"/proc/$pid/cgroup" 2>/dev/null)
    printf 'SV08_MEDIA_LOCK_HOLDER phase=%s pid=%s fd=%s cgroup=%s command=%s\n' "$phase" "$pid" "${fd##*/}" "$cgroup" "$command"
  done
fi
echo SV08_NAMESPACE_${phase}_END
SV08_NS_SCRIPT
chmod 0700 /run/sv08-namespace-report.sh
mkdir -p /run/systemd/system/sv08-recovery-prepare.service.d /run/systemd/system/sv08-recovery.target.wants
''' + override_units + r'''
cat >/run/systemd/system/sv08-namespace-report.service <<'SV08_NS_UNIT'
[Unit]
Description=Diagnostic-only recovery namespace report
After=basic.target systemd-udev-settle.service sv08-recovery-private-mounts.service
Before=sv08-recovery-prepare.service sv08-recovery-display.service
[Service]
Type=oneshot
ExecStart=/run/sv08-namespace-report.sh EARLY
StandardOutput=journal+console
StandardError=journal+console
SV08_NS_UNIT
cat >/run/systemd/system/sv08-recovery-prepare.service.d/namespace-report.conf <<'SV08_NS_DROPIN'
[Unit]
Requires=sv08-namespace-report.service
After=sv08-namespace-report.service
SV08_NS_DROPIN
ln -s ../sv08-namespace-report.service /run/systemd/system/sv08-recovery.target.wants/sv08-namespace-report.service
cat >/run/systemd/system/sv08-namespace-late-report.service <<'SV08_NS_LATE_UNIT'
[Unit]
Description=Diagnostic-only late recovery namespace report
After=sv08-recovery-display.service
[Service]
Type=oneshot
ExecStart=/bin/sh -c 'sleep 60; exec /run/sv08-namespace-report.sh LATE'
StandardOutput=journal+console
StandardError=journal+console
SV08_NS_LATE_UNIT
ln -s ../sv08-namespace-late-report.service /run/systemd/system/sv08-recovery.target.wants/sv08-namespace-late-report.service
'''
    init.write_text(original.replace(marker, instrumentation + marker))
    init.chmod(0o755)
    packed = output / "namespace-initrd.gz"
    find = subprocess.Popen(["find", ".", "-print0"], cwd=unpack, stdout=subprocess.PIPE)
    cpio = subprocess.Popen(["cpio", "--null", "-o", "--format=newc", "--quiet"], cwd=unpack,
                            stdin=find.stdout, stdout=subprocess.PIPE)
    find.stdout.close()
    with packed.open("wb") as stream:
        subprocess.run(["gzip", "-9"], stdin=cpio.stdout, stdout=stream, check=True, timeout=60)
    cpio.stdout.close()
    if find.wait(timeout=10) or cpio.wait(timeout=10):
        raise RuntimeError("Could not repack namespace diagnostic initramfs")
    shutil.rmtree(unpack)
    build = json.loads((candidate / "build.json").read_text())
    endpoint = Path(tempfile.mkdtemp(prefix="sv08-ns-qmp-"))
    qmp = endpoint / "qmp.sock"
    command = qemu_command(candidate, fixture, qmp, build["manifest_sha256"],
                           build["provider_manifest_sha256"], initrd=packed)
    write(output / "command.json", json.dumps([str(x) for x in command], indent=2) + "\n")
    serial = (output / "serial.log").open("wb")
    process = subprocess.Popen([str(x) for x in command], stdin=subprocess.DEVNULL,
                               stdout=serial, stderr=subprocess.STDOUT)
    client = None
    started = time.monotonic()
    complete = False
    try:
        while process.poll() is None and time.monotonic() - started < seconds:
            if client is None and qmp.exists():
                client = QMP(qmp)
            text = (output / "serial.log").read_text(errors="replace")
            if "SV08_NAMESPACE_LATE_END" in text:
                complete = True
                time.sleep(3)
                client.call("quit")
                break
            time.sleep(.5)
        if process.poll() is None:
            if client is not None:
                try:
                    client.call("quit")
                except (OSError, EOFError, RuntimeError):
                    pass
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=10)
    finally:
        if process.poll() is None:
            process.kill(); process.wait(timeout=10)
        serial.close()
        shutil.rmtree(endpoint)
    if not complete:
        raise AssertionError("Diagnostic namespace report did not complete")
    result = dict(diagnostic_only=True, acceptance=False, complete=True,
                  diagnostic_namespace_overrides=overrides,
                  candidate_image_sha256=build["image_sha256"],
                  production_initrd_sha256=build["initrd_sha256"],
                  diagnostic_initrd_sha256=sha(packed), command=[str(x) for x in command])
    write(output / "result.json", json.dumps(result, indent=2) + "\n")
    return result


def destination_state(fixture, output, name, raw_name="destination.raw"):
    partition = output / (name + ".fat")
    raw = Path(raw_name)
    if not raw.is_absolute():
        raw = fixture / raw
    with raw.open("rb") as source, partition.open("wb") as target:
        source.seek(DESTINATION_START * 512)
        remaining = DESTINATION_SECTORS * 512
        while remaining:
            block = source.read(min(1024 * 1024, remaining))
            if not block:
                raise ValueError("Short destination partition")
            target.write(block)
            remaining -= len(block)
    extracted = output / (name + "-files")
    extracted.mkdir()
    run(["mcopy", "-i", partition, "-s", "::*", extracted])
    older = extracted / "older-export.txt"
    if not older.is_file() or sha(older) != hashlib.sha256(
            b"existing destination file must survive\n").hexdigest():
        raise AssertionError("Older destination file changed or disappeared")
    archives = {p.name: sha(p) for p in extracted.glob("*.tar") if p.is_file()}
    malformed_archives = sorted(p.name for p in extracted.glob("*.tar") if not p.is_file())
    markers = sorted(p.name for p in extracted.glob("*.marker"))
    return dict(partition=partition, extracted=extracted, archives=archives,
                malformed_archives=malformed_archives,
                older_sha256=sha(older), markers=markers)


def verify_destination(fixture, output, expected_payload, before):
    state = destination_state(fixture, output, "destination-after")
    export_dir = state["extracted"]
    new_names = sorted(set(state["archives"]) - set(before["archives"]))
    changed = {name for name, digest in before["archives"].items()
               if state["archives"].get(name) != digest}
    if changed:
        raise AssertionError("Pre-existing export archives changed: " + ", ".join(sorted(changed)))
    if len(new_names) != 1:
        raise AssertionError("Expected exactly one newly published export archive")
    archives = [export_dir / new_names[0]]
    members = {}
    if archives:
        with tarfile.open(archives[0]) as archive:
            for item in archive:
                if item.isfile():
                    members[item.name] = hashlib.sha256(archive.extractfile(item).read()).hexdigest()
        expected_members = {"data/" + name: digest for name, digest in expected_payload.items()}
        for name, digest in expected_members.items():
            if members.get(name) != digest:
                raise AssertionError("Export member changed or missing: " + name)
        if "export-manifest.json" not in members:
            raise AssertionError("Export manifest is missing")
    return dict(archives=[p.name for p in archives], archive_sha256=state["archives"][new_names[0]],
                members=members, older_preserved=True, older_sha256=state["older_sha256"],
                archives_before=before["archives"])


def fill_destination(fixture, output):
    """Fill the disposable FAT partition so the admitted export cannot fit."""
    partition = output / "destination-no-space.fat"
    with (fixture / "destination.raw").open("rb") as source, partition.open("wb") as target:
        source.seek(DESTINATION_START * 512)
        remaining = DESTINATION_SECTORS * 512
        while remaining:
            block = source.read(min(1024 * 1024, remaining))
            if not block:
                raise ValueError("Short destination partition")
            target.write(block); remaining -= len(block)
    filler = output / "destination-filler.bin"
    with filler.open("wb") as stream:
        stream.truncate(DESTINATION_SECTORS * 512 - 2 * 1024 * 1024)
    run(["mcopy", "-i", partition, str(filler), "::/destination-filler.bin"])
    with partition.open("rb") as source, (fixture / "destination.raw").open("r+b") as target:
        target.seek(DESTINATION_START * 512)
        while True:
            block = source.read(1024 * 1024)
            if not block: break
            target.write(block)


def execute(candidate, fixture, output, seconds, journey, fault, source_readonly,
            diagnostic_initrd=None):
    candidate, fixture = safe_regular(candidate), safe_regular(fixture)
    output = safe_regular(output, fresh=True)
    if diagnostic_initrd is not None:
        diagnostic_initrd = safe_regular(diagnostic_initrd)
        if not diagnostic_initrd.is_file():
            raise ValueError("Diagnostic initrd must be a regular file")
    build = json.loads((candidate / "build.json").read_text())
    expected_fixture = json.loads((fixture / "fixture.json").read_text())
    if expected_fixture.get("dirty_source_method") != "selected-arm64-guest-qmp-power-cut-while-mounted":
        raise ValueError("Acceptance requires the VM-crash-created dirty source")
    if build.get("media_profile_sha256") != expected_fixture["profile_sha256"]:
        raise ValueError("Candidate is not bound to this immutable media profile")
    policy = image_policy(candidate / "recovery.ext4")
    policy_bytes = (json.dumps(policy, sort_keys=True, separators=(",", ":")) + "\n").encode()
    if hashlib.sha256(policy_bytes).hexdigest() != build.get("policy_sha256"):
        raise ValueError("Extracted immutable policy does not match the build binding")
    provider_binding = build.get("provider_manifest_sha256")
    if not isinstance(provider_binding, str) or len(provider_binding) != 64:
        raise ValueError("Candidate lacks the immutable provider manifest binding")
    output.mkdir(parents=True, mode=0o700)
    destination_before = destination_state(fixture, output, "destination-before")
    if fault == "no-space":
        fill_destination(fixture, output)
        destination_before = destination_state(fixture, output, "destination-before-no-space")
    endpoint = Path(tempfile.mkdtemp(prefix="sv08-export-qmp-"))
    qmp = endpoint / "qmp.sock"
    boot_provider = "0" * 64 if fault == "wrong-provider" else provider_binding
    command = qemu_command(candidate, fixture, qmp, build["manifest_sha256"],
                           boot_provider, source_readonly=source_readonly,
                           initrd=diagnostic_initrd)
    replacement_path = None
    replacement_before = None
    if fault in ("stale-context", "replace-destination"):
        replacement_path = add_replacement_drive(command, fixture)
        replacement_before = sha(replacement_path)
        if fault == "stale-context":
            alter_fat_identity(replacement_path)
    corruption_stop = threading.Event()
    corruption_thread = None
    write(output / "command.json", json.dumps([str(x) for x in command], indent=2) + "\n")
    before = {"recovery": sha(candidate / "recovery.ext4"), "source": sha(fixture / "source.raw"),
              "protected": sha(fixture / "protected.raw"), "destination": sha(fixture / "destination.raw")}
    serial = (output / "serial.log").open("wb")
    process = subprocess.Popen([str(x) for x in command], stdin=subprocess.DEVNULL,
                               stdout=serial, stderr=subprocess.STDOUT)
    client = None
    peak = 0
    started = time.monotonic()
    actions = []
    boot_report = None
    cleanup_injected = False
    sample_stop = threading.Event()
    peak_sample = [0]
    def sample_memory():
        while not sample_stop.wait(.1):
            try:
                for line in (Path("/proc") / str(process.pid) / "status").read_text().splitlines():
                    if line.startswith("VmRSS:"):
                        peak_sample[0] = max(peak_sample[0], int(line.split()[1]) * 1024)
            except FileNotFoundError:
                return
    sampler = threading.Thread(target=sample_memory, daemon=True)
    sampler.start()
    try:
        while process.poll() is None and time.monotonic() - started < seconds:
            try:
                for line in (Path("/proc") / str(process.pid) / "status").read_text().splitlines():
                    if line.startswith("VmRSS:"):
                        peak = max(peak, int(line.split()[1]) * 1024)
            except FileNotFoundError:
                pass
            if client is None and qmp.exists():
                client = QMP(qmp)
            serial_text = (output / "serial.log").read_text(errors="replace")
            if (client and fault == "cleanup-prep-failure" and not cleanup_injected and
                    "debug-shell.service" in serial_text):
                # Let the ordinary preparer create its destination mountpoint,
                # then leave an operation-created marker behind and terminate
                # the preparer.  Its normal rollback must report the failed
                # rmdir rather than silently deleting an unrelated file.
                client.key("ctrl", "alt", "f9")
                time.sleep(2)
                client.text(
                    "while [ ! -e /run/sv08-recovery/destinations/export-usb ]; do sleep 1; done;"
                    " touch /run/sv08-recovery/destinations/export-usb/marker;"
                    " pkill -TERM -f sv08_recovery_prepare.py\n")
                time.sleep(2)
                client.key("ctrl", "alt", "f1")
                cleanup_injected = True
                actions.append("vt-debug-shell-cleanup-fault")
            text = (output / "serial.log").read_text(errors="replace")
            if client and "SV08_RECOVERY_BOOT_REPORT " in text:
                for line in text.splitlines():
                    if "SV08_RECOVERY_BOOT_REPORT " in line:
                        boot_report = json.loads(line.split("SV08_RECOVERY_BOOT_REPORT ", 1)[1])
                time.sleep(3)
                client.call("screendump", {"filename": str(output / "ready.ppm")})
                def step(name, operation, delay=2):
                    operation(); time.sleep(delay); actions.append(name)
                    client.call("screendump", {"filename": str(output / (name + ".ppm"))})
                if fault == "wrong-provider":
                    actions.append("diagnostic-only-wrong-provider-binding")
                elif fault == "cleanup-prep-failure":
                    actions.append("cleanup-failure-observed")
                else:
                    # Re-read visible state after the serial report using the
                    # same modality as the journey.  Initial nonblocking lease
                    # contention is valid and must recover through Refresh.
                    if journey == "keyboard":
                        step("keyboard-preflight-refresh",
                             lambda: (client.key("tab"), client.key("tab"),
                                      client.key("tab"), client.key("ret")), 35)
                    elif journey == "keyboard-mouse":
                        # Establish the post-report state with the mouse, then
                        # exercise the mixed keyboard-plus-mouse review path.
                        step("mouse-preflight-refresh", lambda: client.click(760, 308), 35)
                    elif journey == "touch":
                        step("touch-preflight-refresh", lambda: client.touch(760, 308), 35)
                    else:
                        step("mouse-preflight-refresh", lambda: client.click(760, 308), 35)
                if fault in ("wrong-provider", "cleanup-prep-failure"):
                    pass
                elif journey == "smoke":
                    step("keyboard-open", lambda: client.key("alt", "s"))
                    step("keyboard-cancel", lambda: client.key("esc"))
                    step("mouse-open", lambda: client.click(760, 240))
                    step("mouse-review", lambda: client.click(620, 430), 35)
                    if fault == "remove-destination":
                        step("qmp-remove-destination",
                             lambda: client.call("device_del", {"id": "destination-device"}), 35)
                    elif fault in ("stale-context", "replace-destination"):
                        step("qmp-remove-destination",
                             lambda: client.call("device_del", {"id": "destination-device"}), 35)
                        step("qmp-add-replacement",
                             lambda: client.call("device_add", {"driver": "scsi-hd",
                                 "id": "destination-replacement-device", "drive": "replacement",
                                 "serial": ("SV08-DESTINATION" if fault == "stale-context"
                                             else "SV08-DESTINATION-REPLACEMENT"),
                                 "bus": "uas0.0", "removable": "on",
                                 "wwn": "0x5000000000000003"}), 35)
                    elif fault == "archive-corruption":
                        client.key("ctrl", "alt", "f9")
                        time.sleep(2)
                        client.text(
                            "touch /run/sv08-recovery/destinations/export-usb/archive-corruptor-started.marker;"
                            " while true; do for f in /run/sv08-recovery/destinations/export-usb/.*partial;"
                            " do test -f \"$f\" && touch /run/sv08-recovery/destinations/export-usb/archive-corruptor-hit.marker"
                            " && dd if=/dev/zero of=\"$f\" bs=512 count=1 conv=notrunc && sync && break 2; done; sleep .1; done &\n")
                        time.sleep(2)
                        client.key("ctrl", "alt", "f1")
                        time.sleep(5)
                        actions.append("vt-debug-shell-archive-corruptor")
                    elif fault == "lock-contention":
                        # systemd.debug_shell is enabled only on this QEMU
                        # command line.  The lock holder is a real root process
                        # in the ordinary candidate guest, and the UI must
                        # refuse the first apply until the lease is released.
                        client.key("ctrl", "alt", "f9")
                        time.sleep(2)
                        client.text("flock -n /run/sv08-recovery/media.lock sleep 90\n")
                        time.sleep(2)
                        client.key("ctrl", "alt", "f1")
                        time.sleep(5)
                        time.sleep(2)
                        actions.append("vt-debug-shell-lock-holder")
                    if fault == "cleanup-failure":
                        client.key("ctrl", "alt", "f9")
                        time.sleep(2)
                        client.text(
                            "touch /run/sv08-recovery/destinations/export-usb/cleanup-blocker-started.marker;"
                            " while true; do for f in /run/sv08-recovery/destinations/export-usb/.*partial;"
                            " do test -f \"$f\" && touch /run/sv08-recovery/destinations/export-usb/cleanup-blocker-hit.marker"
                            " && dd if=/dev/zero of=\"$f\" bs=512 count=1 conv=notrunc && rm -f \"$f\" && mkdir \"$f\" && break 2; done; sleep .1; done &\n")
                        time.sleep(2)
                        client.key("ctrl", "alt", "f1")
                        actions.append("vt-debug-shell-partial-cleanup-blocker")
                    if fault in ("archive-corruption", "cleanup-failure"):
                        step("mouse-apply", lambda: (client.click(680, 500),
                                                       client.key("tab"), client.key("tab"),
                                                       client.key("ret"), client.key("tab"),
                                                       client.key("ret")), 120)
                    else:
                        step("mouse-apply", lambda: client.click(680, 500), 120)
                    step("touch-refresh", lambda: client.touch(760, 300))
                elif journey == "touch":
                    step("touch-open-cancel", lambda: client.touch(760, 240))
                    step("touch-cancel-selection", lambda: client.touch(500, 430))
                    step("touch-open-review-cancel", lambda: client.touch(760, 240))
                    step("touch-review-cancel", lambda: client.touch(620, 430), 35)
                    step("touch-cancel-review", lambda: client.touch(530, 500))
                    step("touch-open-apply", lambda: client.touch(760, 240))
                    step("touch-review-apply", lambda: client.touch(620, 430), 35)
                    step("touch-apply", lambda: client.touch(680, 500), 120)
                elif journey == "keyboard":
                    step("keyboard-open-cancel", lambda: client.key("alt", "s"))
                    step("keyboard-cancel-selection", lambda: client.key("esc"))
                    step("keyboard-open-review-cancel", lambda: client.key("alt", "s"))
                    step("keyboard-focus-review-cancel", lambda: (client.key("tab"), client.key("tab")))
                    step("keyboard-review-cancel", lambda: client.key("ret"), 35)
                    step("keyboard-cancel-review", lambda: client.key("esc"))
                    step("keyboard-open-apply", lambda: client.key("alt", "s"))
                    step("keyboard-focus-review-apply", lambda: (client.key("tab"), client.key("tab")))
                    step("keyboard-review-apply", lambda: client.key("ret"), 35)
                    step("keyboard-focus-apply", lambda: client.key("tab"))
                    step("keyboard-apply", lambda: client.key("ret"), 120)
                elif journey == "keyboard-mouse":
                    step("mouse-open-keyboard-cancel", lambda: client.click(760, 240))
                    step("keyboard-cancel-selection", lambda: client.key("esc"))
                    step("mouse-open-keyboard-review", lambda: client.click(760, 240))
                    step("mouse-review-keyboard-apply", lambda: client.click(620, 430), 35)
                    step("mouse-apply", lambda: client.click(680, 500), 120)
                else:
                    raise ValueError("Journey is not implemented: " + journey)
                client.call("screendump", {"filename": str(output / "complete.ppm")})
                break
            time.sleep(1)
    finally:
        sample_stop.set()
        sampler.join(timeout=2)
        corruption_stop.set()
        if corruption_thread is not None:
            corruption_thread.join(timeout=2)
        peak = max(peak, peak_sample[0])
        if process.poll() is None:
            if client:
                try:
                    client.call("quit")
                except (OSError, EOFError, RuntimeError):
                    pass
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill(); process.wait(timeout=10)
        serial.close()
        if replacement_path is not None:
            shutil.copyfile(replacement_path, output / "destination-replacement-after.raw")
            replacement_after = sha(replacement_path)
        else:
            replacement_after = None
        if replacement_path is not None:
            replacement_path.unlink(missing_ok=True)
        shutil.rmtree(endpoint)
    after = {"recovery": sha(candidate / "recovery.ext4"), "source": sha(fixture / "source.raw"),
             "protected": sha(fixture / "protected.raw"), "destination": sha(fixture / "destination.raw")}
    preparation = []
    for line in (output / "serial.log").read_text(errors="replace").splitlines():
        if "SV08_RECOVERY_PREPARE " in line:
            preparation.append(json.loads(line.split("SV08_RECOVERY_PREPARE ", 1)[1]))
    order = [item.get("event") for item in preparation]
    required_order = ["source-whole-ro", "source-partition-ro", "source-mount-begin",
                      "source-mount-complete"]
    if fault not in ("wrong-provider", "cleanup-prep-failure"):
        positions = [order.index(event) for event in required_order]
        if positions != sorted(positions) or len(set(positions)) != len(positions):
            raise AssertionError("Production source preservation order was not observed")
        mount_event = preparation[positions[2]]
        if "ro,noload" not in mount_event.get("options", ""):
            raise AssertionError("Production source mount did not suppress journal replay")
        # The read-only boot report and GTK refresh intentionally use the same
        # nonblocking MediaLease, so either may record a transient contention
        # refusal.  The post-report visible Refresh plus the verified archive
        # below is the positive proof that installed export became available.
        if not boot_report or boot_report.get("failed_units"):
            raise AssertionError("Production startup report is missing or has failed units")
    elif fault == "cleanup-prep-failure":
        if not any("cleanup" in line.lower() and "incomplete" in line.lower()
                   for line in (output / "serial.log").read_text(errors="replace").splitlines()):
            raise AssertionError("Production cleanup failure was not reported")
    elif (not boot_report or
          boot_report["status"]["capabilities"]["recovery.export"]["available"] or
          not boot_report["status"]["capabilities"]["recovery.export"]["reason"]):
        raise AssertionError("Untrusted preparation did not leave a useful export diagnostic")
    if fault == "none":
        destination = verify_destination(fixture, output, expected_fixture["source_payload"],
                                         destination_before)
    else:
        destination_after = destination_state(fixture, output, "destination-after")
        new_names = sorted(set(destination_after["archives"]) - set(destination_before["archives"]))
        if new_names:
            raise AssertionError("Failure path published an archive: " + ", ".join(new_names))
        if destination_after["malformed_archives"]:
            raise AssertionError("Failure path published malformed archive path: " +
                                 ", ".join(destination_after["malformed_archives"]))
        destination = dict(archives=[], archives_before=destination_before["archives"],
                           older_preserved=True, older_sha256=destination_after["older_sha256"],
                           expected_failure=fault, markers=destination_after["markers"])
        if fault == "archive-corruption" and "archive-corruptor-hit.marker" not in destination_after["markers"]:
            raise AssertionError("Archive corruption watcher never observed a partial")
        if fault == "cleanup-failure" and "cleanup-blocker-hit.marker" not in destination_after["markers"]:
            raise AssertionError("Cleanup watcher never observed an operation partial")
        if replacement_after is not None:
            replacement_state = destination_state(fixture, output, "replacement-after",
                                                   output / "destination-replacement-after.raw")
            destination["replacement_archives"] = replacement_state["archives"]
            destination["replacement_older_sha256"] = replacement_state["older_sha256"]
    result = dict(format_version=1, acceptance=diagnostic_initrd is None,
                  diagnostic_initrd_sha256=(sha(diagnostic_initrd)
                                            if diagnostic_initrd else None),
                  elapsed_seconds=time.monotonic() - started,
                  exit_code=process.returncode, peak_qemu_rss_bytes=peak, actions=actions,
                  journey=journey, fault=fault, source_backing_readonly=source_readonly,
                  boot_report=boot_report,
                  hashes_before=before, hashes_after=after,
                  recovery_preserved=before["recovery"] == after["recovery"],
                  source_preserved=before["source"] == after["source"],
                  protected_preserved=before["protected"] == after["protected"],
                  preparation_events=preparation,
                  destination=destination, candidate_build=build,
                  provider_binding=provider_binding,
                  replacement_before_sha256=replacement_before,
                  replacement_after_sha256=replacement_after)
    write(output / "result.json", json.dumps(result, indent=2) + "\n")
    if not all((result["recovery_preserved"], result["source_preserved"],
                result["protected_preserved"])):
        raise AssertionError("Protected input changed")
    if fault == "none" and not destination["archives"]:
        raise AssertionError("Installed GTK journey did not publish an archive")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("inspect", "prepare", "dirty", "namespace", "run"), nargs="?", default="inspect")
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--candidate", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--selected-initrd", type=Path)
    parser.add_argument("--module-initrd", type=Path)
    parser.add_argument("--seconds", type=int, default=180)
    parser.add_argument("--journey", choices=("smoke", "touch", "keyboard", "keyboard-mouse"),
                        default="smoke")
    parser.add_argument("--fault", choices=("none", "wrong-provider", "remove-destination", "stale-context",
                                             "replace-destination", "archive-corruption", "lock-contention",
                                             "cleanup-failure", "cleanup-prep-failure", "no-space"),
                        default="none")
    parser.add_argument("--source-readonly", action="store_true")
    parser.add_argument("--namespace-overrides", action="store_true",
                        help="diagnostic-only udevd/logind namespace drop-ins")
    parser.add_argument("--diagnostic-initrd", type=Path,
                        help="diagnostic-only initrd for harness debugging; never acceptance")
    args = parser.parse_args()
    if args.stage == "inspect":
        print(json.dumps(dict(execute=False, fixture=str(safe_regular(args.fixture)),
                              profile=reviewed_profile(), network=False,
                              physical_devices=False), indent=2))
    elif args.stage == "prepare":
        print(json.dumps(prepare(args.fixture), indent=2))
    elif args.stage == "dirty":
        if not args.candidate or not args.output or not args.selected_initrd:
            parser.error("dirty requires --candidate, --selected-initrd and --output")
        print(json.dumps(dirty_source(args.candidate, args.fixture, args.selected_initrd,
                                      args.output, args.seconds, args.module_initrd), indent=2))
    elif args.stage == "namespace":
        if not args.candidate or not args.output:
            parser.error("namespace requires --candidate and --output")
        print(json.dumps(namespace_diagnostic(args.candidate, args.fixture, args.output,
                                              args.seconds, args.namespace_overrides), indent=2))
    else:
        if not args.candidate or not args.output or not 60 <= args.seconds <= 600:
            parser.error("run requires --candidate, --output and --seconds 60..600")
        print(json.dumps(execute(args.candidate, args.fixture, args.output, args.seconds,
                                 args.journey, args.fault, args.source_readonly,
                                 args.diagnostic_initrd), indent=2))


if __name__ == "__main__":
    main()
