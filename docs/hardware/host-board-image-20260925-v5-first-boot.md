# Board image v5 first boot

Date: 2026-09-25. Hardware profile: `test-sv08-01`, owner-reported board
marking `H616_JC_6Z_V1.2`. The spare eMMC was written and full direct-I/O
readback verified as recorded in the [v5 image record](host-board-image-20260925-v5.md)
and JSON manifest. The owner reinstalled it, connected the USB serial interface,
and reported that the printer booted with output on both the HDMI panel and the
GL-RM1V2 KVM.

## Observed host state

SSH to `sv08@192.168.1.141` succeeded. The running system reports Debian 13
(`trixie`), kernel `6.18.51-sv08-candidate1`, and command-line slot `A`. Root
is the expected `root-a` PARTUUID `26c68198-9248-47af-bbd3-643f1b604ef5`, mounted
read-only. `/data` is the expected data PARTUUID
`4773f966-0678-4cf5-bb83-8ee6fb11d8eb`, mounted read-write, and the state file
exists. `sv08-prepare.service` exited successfully. NetworkManager reports
`wlan1` connected to the owner's `iotnet` network at the reserved address
`192.168.1.141`; Ethernet is unavailable. Printer output services remain
masked, and no heater, motion, or MCU operation was attempted.

Both redundant U-Boot environments were read from the running eMMC and passed
CRC checks. The flag-1 copy at 4 MiB still shows `BOOT_A_LEFT=3`; the newer
flag-2 copy at 8 MiB shows `BOOT_A_LEFT=2`; both show `BOOT_ORDER=A` and
`BOOT_B_LEFT=0`. One A attempt has therefore been consumed. The boot-health and
RAUC services are masked by the diagnostic command line, so this boot has not
confirmed the slot. Avoid another reboot until a reviewed plan preserves a
bootable attempt or the image is replaced.

The initial receive-only serial capture missed SPL/U-Boot output: its watcher
used a stale Beelink USB path and then expired with zero bytes. A corrected
root-owned receiver is now attached to the observed CH340 path, but it started
after this boot and cannot reconstruct the missing trace. SSH and the KVM
snapshot independently establish that Linux reached the normal host login.
The private screenshot and UART/session files are retained under
`local/test-sv08-01/board-v5-write-20260925/` and Beelink's private capture
directory.

## Items found for the next candidate

Only Cockpit is currently failed. Its certificate helper attempted to generate
a self-signed certificate under `/etc/cockpit/ws-certs.d`; the immutable root
is read-only, so `cockpit.socket` exhausted its start limit and the system is
degraded. The helper also logged that optional `sscg` is unavailable before
falling back to OpenSSL. Preserve a device-specific certificate and key under
the writable persistent data filesystem and point Cockpit's supported
certificate directory there; do not make the OS root writable to hide this
failure.

The KVM snapshot is 1280×720. Linux reports HDMI connected with active mode
1280×720 and lists 1024×576, but not 1024×600. The host's 256-byte EDID hash is
`0c6673505da0ecd208d33670b41f6dc41e76af95332049b2549dd4a62c456e52`; its
preferred detailed timing is 1280×720 and it identifies as MACROSILICON. That
EDID does not match the custom 1024×600 EDID saved by the GL-RM1V2, whose hash is
`932c187a061cf4b042667486f723d3a6663bf2636c274338b79e7531cdb669f9`. The HDMI
picture is visible, but whether the KVM's custom EDID reaches the host and
whether 1280×720 is scaled acceptably by the 1024×600 panel remain unresolved.

This verifies a normal Linux A-slot boot and persistent-data setup, not a
healthy release or a working printer. Physical DRAM stability, repeatable cold
boot, Cockpit, the intended native display mode/touch input, camera, B/recovery,
and all printer outputs, heat, motion and printing remain unverified.
