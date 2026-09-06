# Test printer 01: spare-eMMC host image

This private candidate is the first host bring-up step for the owner's blank
32 GB eMMC. It combines fresh Debian 13 arm64 with captured vendor boot support.
It is **not yet a printing image**: Klipper source is staged, but Klipper,
Moonraker and touchscreen services are not installed or activated. No MCU
firmware is included. The [decision](../decisions/0002-first-emmc-image.md)
explains the scope and the path to retiring the vendor boot support.

The factory eMMC remains the owner's host rollback baseline. An additional full
factory image file is optional; it is not required to write and test this image.
Do not flash either MCU during this host test.

## Reported spare-module boot

On 2026-09-06 the owner reported successful boot of the new image on the new
eMMC. This is [owner-reported evidence](../../profiles/test-sv08-01/observations/2026-09-06-spare-boot.json);
no new boot logs, exact module capacity or installed-image hash were inspected.
Detailed host validation and restoration testing remain outstanding. To preserve
the installed system, follow [Make an image file from an eMMC](imaging-emmc.md).

## Artifact and first boot

Follow the [Windows, Linux and macOS flashing instructions](flashing-emmc.md)
to write the blank spare with checksum and readback validation.

Local output is `artifacts/test-sv08-01-host-v1.img`, accompanied by SHA-256,
package inventory and build manifest files. A compressed `.img.xz` copy is
also provided (291,106,052 bytes, about 278 MiB); decompress it first if the
writer accepts only raw `.img` files. Its SHA-256 is
`0fbcf1fe7b8418609ddf5d6c9b3946106762624ccebe154c57923e17cd479211`.
The compressed stream passed integrity checking and decompresses to the exact
validated raw-image hash. The raw whole-device image is
8,589,934,592 bytes (8 GiB). Its partitions deliberately use less than the
spare's nominal 32 GB; there is no first-boot resize operation.

1. Verify the artifact against its `.sha256` file on the writer computer.
   The checksum files use the artifact basename, so run the check from their
   containing directory (for example `sha256sum -c test-sv08-01-host-v1.sha256`).
2. Identify the **blank spare** in the USB reader by model/topology and capacity.
   Use a raw whole-device image writer and enable its readback verification.
   The destination must have at least 8,589,934,592 bytes. Do not format any
   partitions if the computer prompts after writing.
3. Cleanly shut down the idle factory host and disconnect power before swapping
   modules. Label and retain the original unchanged. Verify connector orientation
   and spare electrical/mechanical compatibility before insertion.
4. Connect Ethernet and boot. Look for DHCP hostname `sv08-mainline` in the
   router's lease list. Use `ssh sovol@NEW_ADDRESS` with the same authorized key
   used for factory inspection. The IP may change. New SSH host keys are generated
   on first boot; verify the new host identity before replacing an old known-hosts
   entry. Password login is disabled; `sovol` has passwordless sudo.
5. Record boot output and run the read-only checks below. There is no web printer
   UI in this host-only image. An HDMI boot console is configured, but display
   operation on the spare has not been demonstrated.

No Wi-Fi credentials, factory passwords, calibration or factory SSH host keys
are copied. The public keys already authorized on the test printer are included;
private login keys are not. Keep this artifact private because it contains
machine-specific boot inputs and authorized access configuration.

```sh
sudo -n true
cat /etc/os-release
uname -a
findmnt /
findmnt /boot
lsblk -b -o NAME,TYPE,SIZE,FSTYPE,MOUNTPOINTS
systemctl --failed
networkctl status
sudo journalctl -b -p warning --no-pager
ls -l /dev/serial/by-id/
cat /opt/sv08-mainline/SOURCE_COMMIT
```

Save raw results privately. Reboot and repeat the checks before claiming reliable
storage/network operation. For rollback, shut down, disconnect power and reinstall
the retained original eMMC. This assumes neither MCU has been changed. Record an
actual successful swap-back separately from possession of the original module.

## Build from captured inputs

The [build profile](../../configs/images/test-sv08-01-host.json) pins the snapshot,
layout, boot-support archive hash and prefix hash. Input paths below are private
and specific to this machine. The boot-support archive was captured read-only
from the running factory host; it is not a factory disk image. Board revision
remains unknown. The fixed snapshot applies to build package downloads, including
Debian security packages; no unattended update service is installed.

On an x86_64 Linux build workstation, install debootstrap, debian-archive-keyring,
qemu-user-static with arm64 binfmt registration, binfmt-support, dosfstools,
mtools, u-boot-tools, e2fsprogs, util-linux and Python 3.12+. These are workstation
build dependencies; never run this recipe on the printer. Initialize the selected
Klipper submodule at its indexed pin. Allow at least 25 GB free for build outputs.

The [builder](../../scripts/build_host_image.py) prints a plan unless `--execute`
is supplied. It creates only workspace files and a temporary chroot proc mount;
it does not write block devices. Build stages are separate from writing the spare.
Use a fresh work directory and output name for each build. A failed configuration
stage should be investigated and rebuilt from a fresh bootstrap, not blindly
rerun over partially configured state.

```sh
sudo python3 scripts/build_host_image.py --stage bootstrap \
  --work build/test-sv08-01-image-v1 --execute
sudo python3 scripts/build_host_image.py --stage configure \
  --work build/test-sv08-01-image-v1 \
  --vendor-archive local/test-sv08-01/image-inputs/vendor-boot-support.tar.gz \
  --authorized-keys local/test-sv08-01/image-inputs/authorized_keys --execute
sudo python3 scripts/build_host_image.py --stage assemble \
  --work build/test-sv08-01-image-v1 \
  --prefix backups/test-sv08-01/recovery-20260905/user-area-prefix.bin \
  --output artifacts/test-sv08-01-host-v1.img --execute
```

Optional compression after assembly uses `xz -T2 -3 -k` on the raw image.
Record a separate checksum for the compressed file; compression is packaging,
not a different disk layout.

The result uses a DOS partition table, a 256 MiB FAT16 boot filesystem at sector
8192, and ext4 at sector 532480. Bytes 512 through 4194303 of the captured prefix
are preserved exactly; only the MBR sector is allowed to change. Boot arguments
and fstab use new filesystem UUIDs. The kernel and DTB stay paired with their
captured modules; the initramfs is rebuilt using the fresh userland. Hardware
related BoardEnv entries retain the captured duplicate overlay lines pending a
separate review. No factory `system.cfg` or boot-side installer scripts are copied.

EXT_CSD settings and hardware boot regions are not written by a USB user-area
image. Both original boot regions were zero in repeat reads and the original
reported `PARTITION_CONFIG=0x00`; that evidence supports trying this user-area
image, but does not establish the blank spare's settings or successful boot.

## Validation and remaining work

Built and checked offline on 2026-09-05. The raw image SHA-256 is
`9f87879d553f832916a56b7229868e3eadfaa756aad38fd5e85f007b65b51b32`.
The [sanitized build observation](../../profiles/test-sv08-01/observations/2026-09-05-host-image.json)
records validation scope. FAT/ext4 checks, partition table/content readback,
boot-prefix preservation, boot UUID references and ten unit tests passed.
Public-key SSH login and Python execution succeeded under QEMU user emulation;
SSHD settings and the target systemd 257 units passed inspection. Temporary
host keys and machine identity were cleared before assembly. Sudoers syntax and
setuid file mode were verified; actual sudo elevation needs hardware testing
because this QEMU-user execution does not implement setuid elevation. QEMU user
mode shares the workstation kernel and does not prove the target kernel boots.

The first configure run exposed debootstrap removing its temporary service policy;
the builder now installs the policy after the second stage. That build's completed
rootfs was inspected, time synchronization added from the same pinned snapshot,
and finalization rerun before assembly. Logs remain private. A complete second
build from scratch has not been performed.

The builder checks FAT/ext4 integrity and boot-prefix preservation. Unit tests
cover unsafe inputs, archive traversal, partition overlap and plan-only behavior:

```sh
python3 -m unittest discover -s tests -v
```

The build manifest records hashes, package inventory, tool versions and selected
Klipper commit. This is a repeatable assembly recipe with pinned inputs, not a
claim of byte-identical output or source-reproduced boot firmware. The owner now reports a successful spare-module boot; detailed boot evidence,
Ethernet, eMMC reliability, HDMI and swap-back remain hardware acceptance tasks.
After that, build the matching upstream host/MCU stack, resolve per-board build
settings and vendor configuration gaps, and preserve both MCU images before
firmware replacement. Follow the [hands-on tasks](test-sv08-01-recovery-tasks.md).
