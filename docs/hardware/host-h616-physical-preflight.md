# H616 physical recovery preflight (offline implementation)

The [approved proposal](../features/h616-physical-preflight/proposal.md) adds a
separate, nonwriting commissioning artifact for the recovery handoff. This is
offline software evidence only. No connected H616 target, p5 marker, boot
policy, raw environment, return to the original recovery UI, or normal A-slot
health has been measured by this work. The stock hardware profile remains an
[inventory](stock-sv08.md), not identity proof for a connected printer.

The earlier urh-04 shorthand said “without whole-device target open.” Its
approved clarification permits a whole-device **O_RDONLY** open solely to
check exact block capacity, `dev_t`, and both 64 KiB exhausted environment
records. It still prohibits O_RDWR and image or environment transfer writes.
Consuming the single-use marker changes recovery p5 metadata; preflight is
not wholly read-only. This does not mark urh-04 passed or authorize urh-05.

`prepare_h616_reimage_job.py --preflight-only` selects the distinct signed
`sv08-h616-signed-preflight-v1` format. The default remains signed
`sv08-h616-signed-reimage-v1`. Other signed job fields, canonical Ed25519
verification, policy digest, one-shot claim, and physical streaming source
hash remain in force. A preflight job requires its own fresh ID, short expiry,
isolated durable claim state, and fresh ephemeral job and receipt key pairs;
it must never consume or rearm a write job. Actual physical preparation also
requires fresh RTC evidence and a separately reviewed operation. Private keys
belong only in coordinator-controlled ignored paths; none are included in the
artifact. No real keys or job were prepared for this implementation.

`build_h616_reimage_candidate.py --preflight-only` requires commissioning,
trusted initramfs, and recovery handoff. It rejects synthetic, claim-only,
fault-injection, and selftest combinations. The compiled preflight retains the
trusted mount and board checks, exact CID/controller/`dev_t`, durable marker
consumption, bundle and job freshness checks, and one authenticated claim.
The FIT identifies the preflight purpose and supplies a separate exact
`sv08.h616_preflight=1` boot token, checked by the compiled preflight.
After a second identity check, it opens the whole eMMC O_RDONLY with O_EXCL,
checks the block descriptor and capacity, reads both job-bound exhausted
environment records, closes the descriptor, and reports `PREFLIGHT_PASS`.
The full source hash, image transfer, and readback remain urh-05 work.

The marker must be unlinked, its directory fsynced, the filesystem synced,
and the recovery mount successfully unmounted and removed before the preflight
finalizer requests `RB_AUTOBOOT`. A refusal after confirmed consumption may
also return through the existing absent-marker selector to the retained
original recovery script. Any earlier or uncertain marker outcome requests
power-off. A returned reboot syscall stops without retry. The existing full
writer still reboots only on exact `PASS`.

The candidate manifest, preparation receipt, service arming check, and FIT
composition record or validate the signed purpose. Composition records actual
writer, initramfs, and FIT SHA-256 values and retains the 64 MiB FIT ceiling and
existing load addresses. Review those values and memory impact against the
existing handoff evidence before any physical stage. Offline tests use tiny
native syscall fixtures and fixture signatures; they make no hardware claim.
Composition also records kernel, DTB, and initramfs byte counts and the FIT
load interval. The FIT starts at `0x48000000`; its 64 MiB ceiling ends at
`0x4c000000`, below the retained marker address `0x4f800000` and original
recovery-script address `0x4fd00000`. Component sizes describe input payloads,
not total boot memory or verified physical relocation behavior. The native
`dtc`/`mkimage` test uses an inert 22-byte kernel, 25-byte initramfs and 111-byte
DTB and produces a 1360-byte FIT; bundle intake and initramfs append are modeled.
That small fixture validates composition and size accounting, not the size or
bootability of a physical artifact. Actual artifact memory review stays pending.
The compiled native preflight has no target-transfer imports, and captured
target syscalls cover read-only opens, close failures, both environment CRCs
and job tokens, plus zero image/environment writes. The service-entry fixture
also refuses an unsigned purpose relabel before launching listeners.
Retire this helper when a supported recovery/update path supplies equivalent
target-admission evidence.

The next physical urh-04 step requires exact target, artifact, recovery, and
preservation evidence plus the standing owner authority and immediate separate
high-consequence review. Its measured checks include FIT entry, marker
consumption, target identity/capacity/raw environments, and return to the
original recovery UI. Even a successful preflight cannot prove that normal A
boots or that SSH is available. Full-write urh-05 remains separate.

Offline continuation checks on 2026-09-30 ran
`python3 -m unittest tests.test_h616_reimage_candidate tests.test_h616_recovery_handoff tests.test_prepare_h616_reimage_job`:
35 tests passed in 26.435 seconds. The measured process tree maximum RSS was
66,680 KiB and final retained continuation logs occupied 24 KiB. The native
FIT fixture's aggregate file content was 6353 bytes. No full-image transfer
or QEMU run was repeated. Marker tests compile the actual main sequence,
marker consumer and finalizer with modeled board, source-mount and identity
boundaries; unlink, fsync, syncfs, unmount and directory-removal faults all
request power-off, while a stale-job refusal after confirmed consumption
requests reboot. These are implementation checks awaiting independent delivery
verification; physical admission and production artifact memory remain pending.
