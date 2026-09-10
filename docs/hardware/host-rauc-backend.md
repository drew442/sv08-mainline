# RAUC backend connected to state and idle admission

2026-09-10. Offline ARM64 VM and sandbox tests; no physical printer was accessed.

[The backend](../../runtime/sv08_rauc.py) now connects the transaction library to
real RAUC, libubootenv and paired ext4/vfat partitions. It has no activation CLI or
automatic scheduler. The caller must supply reviewed manifests and hold the
state/admission locks. Non-deployable hardware manifests are refused. Its explicit
fixture exception requires QEMU, the test disk serial, a test kernel argument and
`deployable=false`.

Before a write it checks:

- Read-only running root, current release/schema and packaged Klipper source pin.
- Root/data/paired-boot identities, six distinct partitions on one non-removable
  device, partition numbers, sizes and starts, and the complete image footprint.
  The shared read-only GPT parser verifies both headers/arrays and CRCs, compares
  on-disk identities with the running map, and excludes GPT/SPL/environment overlaps.
- Exact RAUC config: U-Boot backend, verity, three attempts, no automatic activation,
  the expected keyring, exactly paired slots, and no custom hooks/handlers.
- Actual running RAUC status, grouping, devices and unmounted inactive targets.
- Two 64 KiB environment regions at 4/8 MiB on that same whole device, plus the
  persistent layout marker, permitted order and bounded counter values.

It authenticates the exact bundle again before installation, hashes the complete
active pair before/after, and verifies both inactive image digests against the
signed proof. Bootloader marking remains a separate transaction operation. These
checks do not substitute for the release builder cross-checking payload contents,
board boot support, key management or hardware validation.

## Integrated guest result

`build/host-qemu-backend-v1/` extends the earlier service-admission fixture. Its
`debugfs.cmd` and `v2-debugfs.cmd` record root/config insertion, including a public
test certificate, explicit PARTUUIDs and `/dev/vda` environment config. Environment
copies were preseeded from the reviewed file-only sandbox fixture. The signed
metadata bundle was copied into the disposable data partition. No private signing
key was copied into the guest.

[The guest test](../../tests/host_qemu_rauc_backend.py) ran real systemd, Moonraker,
RAUC 1.15.2, its U-Boot backend and libubootenv on the distro kernel. Printer/heater
status remained simulated using the previously documented reactor fixture. It
successfully staged both inactive partitions under idle admission, verified all
four image hashes, left A primary/B bad, armed B, then cancelled and restored A
primary/B bad before clearing the pending record. Services were restored between
operations. `boot.log` and the [public result](host-rauc-backend-20260910.json)
record the final run and normal shutdown.

The guest also simulated the counter value consumed before a final B attempt:
with B preferred but its counter zero, RAUC reported A as the next primary.
`mark-good B` restored B's counter and priority; B was then disarmed again. The
transaction confirmation logic now checks resulting priority **after** mark-good,
so a healthy final attempt is not rejected merely because its counter was already
consumed. Unit tests cover that ordering and refusal when priority stays changed.
This simulation did not boot B or evaluate trial health.

A subsequent native U-Boot sandbox read the environment written by the real ARM64
backend and saw order A, A=3, B=0 and the correct layout marker. The whole disk hash
was unchanged by that read. Logs/results are in
`build/rauc-backend-uboot-check/`. This connects the Linux and bootloader formats;
it still does not prove eMMC power-loss atomicity or H616 board booting.

## GPT collision admission

After the integrated install run, the final parser revision passed two additional
ARM64 boots using [the read-only probe](../../tests/host_qemu_gpt_backend.py).
The normal GPT was admitted. Moving the primary array to LBA 16384 (8 MiB) on
the disposable file preserved partition identities and allowed Linux to boot,
but backend admission rejected its overlap with the second environment region.
The probe issued no install or bootloader marking commands. Logs are
`gpt-positive.log` and `gpt-negative.log` in the backend fixture directory.
The table was then restored to LBA 4096 and both environment banks reseeded;
`gpt-restored.json` records the restored collision-free layout. This final parser
revision (apart from removal of a trailing blank line) has read-only guest admission evidence; the preceding full installation
run used the backend revision recorded separately in the public evidence.

## Remaining gates

The low-level backend is connected and tested, but configuration rendering for a
reviewed board, owned staging/upload paths, automatic idle/next-boot policy,
boot-time transaction reconciliation and production health confirmation remain
open. The test uses an offline-only signed bundle with dummy boot content; it must
not be written to a printer. Complete OS recovery, service/onboarding UI and named
hardware commissioning remain on the [task list](host-os-tasks.md).

Primary source used: pinned RAUC `src/bootloaders/uboot.c` and `src/main.c` at
`4fb7c798d6ae412344fb8f8d310d773046af3441`, inspected locally on 2026-09-10;
Linux block sysfs and the actual target service outputs supply measured identities.
The custom backend fills project layout/admission/state checks around upstream
RAUC; retire it if upstream supplies equivalent declarative integration. See
[decision 0006](../decisions/0006-host-state-integration.md).
