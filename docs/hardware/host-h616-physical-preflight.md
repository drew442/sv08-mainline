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

The separately approved 2026-09-30 repair fixes the shared staging verifier's
default write-purpose selection. It checks the signed job against strict bundle
and composition modes before staging. The actual executable now contains a
compile-time ELF section with purpose, trusted-entry/handoff/fixture modes and
the signed descriptor and policy hashes. A bounded Python ELF64 little-endian
reader inspects that section at build, composition and staging. Replacing a preflight executable
with the actual write executable is refused even when its unsigned manifest
hashes are recomputed. This section is compile evidence, not a signature or
proof that arbitrary newly authored ELF code is safe: the independently reviewed
`expected_build_sha256` remains the artifact trust boundary.
Newly built write candidates carry the same evidence section; historical
executables without it require rebuilding and a new reviewed artifact hash.

The shared verifier also checks the decompressed archive hash and streams the
actual gzip/newc initramfs already checked against its FIT member. Its trusted executable,
job, detached signature, policy, expected image hash and PID 1 ORDER entry must
match the compiled bundle. The unchanged live stage, arm and activation consumers
call that verifier; existing journal build/FIT hashes retain the reviewed purpose
across later operations. Tests capture target opens after positive revalidation
and refuse changed bundle/journal pins before those boundaries. The production
live adapter is unchanged, and these fixtures perform no live media operation.
The streaming reader supports only the actual composer's single gzip/newc
format, with a 64 MiB compressed-input ceiling, 128 MiB uncompressed archive
ceiling, 64 MiB ordinary-member ceiling, 4096-byte names and 100000 entries.
Required members must have their exact reviewed lengths and regular-file type;
duplicates, unsafe paths, truncation, unsupported types and nonzero archive
tails are refused. The ELF reader limits executables to 4 MiB, 1024 sections
and one 1024-byte purpose record. Job/policy inputs are limited to 64 KiB.
This avoids adding `readelf` or `unmkinitramfs` to the recorded SD userspace
tool contract; those tools remain available only for existing workbench builds.

Representative composition uses the retained pinned inputs in
[the SD input record](../../configs/host-os/sv08-sd-network-inputs.json), with
provenance in [the root prototype](host-sd-network-root-prototype.md) and
[the eMMC probe](host-sd-network-emmc-probe-20260926.md). The actual C compiler,
initramfs append and `mkimage` machinery run against an expired lab descriptor
signed with existing test fixtures. The production builder still prohibits
fixture keys for physical candidates; the offline compiler harness does not
relax that guard or prepare a real physical job or claim.

| Representative component | Bytes | SHA-256 |
| --- | ---: | --- |
| Compiled preflight writer | 779072 | `4db3284d9f1e428f12cb13980cc8b63a3a1d197284affa5597ac5dcd52bc7bb1` |
| Appended initramfs | 15444207 | `675d7076fca0813c05fcd8106d43f432b6a17132add8e9e8dc3afd681403d4ba` |
| Uncompressed initramfs archive | 54857728 | `fd3cadc9379169a4a070733982c42ffd184236c94476fdc42115897a100ef15a` |
| FIT | 48899052 | `4c20dc95b234ad11b1e9b2108fd5158ac8c87391f18fad89a4384a0b78c773e2` |

The kernel interval is `[0x40080000, 0x4205ba00)` and the FIT interval is
`[0x48000000, 0x4aea23ec)`, below the marker at `0x4f800000` and original
script address `0x4fd00000`. These fixed intervals do not overlap.
Conservative static accounting totals 565388663 bytes against 1 GiB, leaving
508353161 bytes: it includes a full 64 MiB FIT reserve, the raw kernel,
compressed initramfs, uncompressed archive and expanded files simultaneously,
two DTB copies, a 4 MiB writer allowance, a 64 MiB bootloader reserve and a
256 MiB kernel/runtime reserve. Those reserves are accounting assumptions,
not observed physical allocations or a guarantee of memory reliability.
`bootm` ramdisk/FDT relocation remains a physical observation requirement.

Final composition and actual streaming staging verification took 11.22 seconds
including compilation and used a measured 145092 KiB maximum RSS. Sampled peak
allocated scratch was 307949568 bytes, including the previous experimental FIT;
retained output was 48963584 bytes after removing only assigned disposable
intermediates. The retained final FIT and compact ignored receipt preserve the
exact sizes, source hashes, toolchain and inputs for independent review. This
supplies representative artifact-size/static-resource evidence, while actual
H616 entry, marker admission, raw environments, relocation and recovery return
remain urh-04. Full transfer/readback remains urh-05.

The final repaired offline regression command adds
`tests.test_h616_recovery_handoff_builder tests.test_recovery_handoff_stage tests.test_h616_live_stage_cli`
to the three modules above. All 47 tests passed in 37.608 seconds, with 66488 KiB
maximum RSS. Cases include signed preflight/default-write admission, signed
cross-purpose and invalid-signature refusal, a write executable with recomputed
unsigned labels, a write executable substituted inside a rebuilt initramfs/FIT,
nonboolean modes, expiry, and changed bundle/journal pins before media mutation.
Malformed/duplicate/oversized/truncated ELF and newc fixtures also pass refusal
checks; positive staging uses neither added target-side executable. The earlier
45-test run before the tool-contract adjustment remains preserved at its scope.
Earlier failed independent verification remains preserved; repaired delivery
requires a fresh independent verifier.
