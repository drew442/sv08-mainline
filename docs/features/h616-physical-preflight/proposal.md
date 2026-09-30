# Physical handoff preflight without a whole-device write

2026-09-29. This closes an identified gap in the existing writerless-eMMC goal;
optional product features remain paused. urh-04 requires physical marker/FIT
entry, target admission and return before urh-05 whole-image commissioning.
Current physical claim-only is intentionally prohibited, and only full PASS
reboots. A new separately compiled nonwriting preflight is needed; do not use
synthetic-only flags or fault injection against the printer.

Reconcile the existing acceptance wording explicitly: the source proposal says
without opening eMMC for whole-device WRITE, while the record shorthand says
without whole-device target open. This bounded proposal admits a whole-device
O_RDONLY descriptor solely for capacity and both raw environment checks. It
continues to prohibit O_RDWR and all image/environment transfer writes from the
preflight executable. Marker consumption changes p5 metadata as already required;
ordinary stager boot-policy arming remains separately reviewed hardware work.
This clarification does not waive physical urh-04 or any owner persistence rule.

Add preflight_only to candidate preparation/build and FIT composition. Permit it
only in commissioning+trusted-initramfs+recovery-handoff mode; reject combinations
with synthetic claim-only/fault modes. Use a distinct signed descriptor format
sv08-h616-signed-preflight-v1 with otherwise unchanged fields. Existing signed
reimage-v1 remains default. A preflight build requires the preflight format; a
write build rejects it. Carry the mode in receipts/manifests/FIT evidence and
validate it at service arming and composition. Claims remain descriptor-bound,
signed and one-shot. Each physical preflight uses its own job ID, expiry, fresh
ephemeral job/receipt key pairs and isolated claim state, never a real write job.
Only that reviewed nonwriting artifact uses those lab verification keys. No
unsigned label may weaken job/receipt signature checks or physical source hashing
in preparation. Existing physical preparation still waits for fresh RTC evidence.

The actual writer under a distinct compile-time preflight flag retains trusted
entry/cmdline/source mount, exact CID/controller/dev_t, durable marker consumption,
signed bundle/job freshness and one authenticated claim. Recheck identity, open
the target O_RDONLY, verify exact block capacity/dev_t and both exhausted,
job-token-bound environment records, close descriptor, and emit PREFLIGHT_PASS.
Compile out the subsequent image-transfer/O_RDWR/environment-writing branch.
Preflight does not certify source bulk hash/readback or full transfer: those
remain urh-05. Production write behavior and guards remain unchanged.

For preflight only, after confirmed marker consumption AND successful recovery
unmount, pass/refusal uses the existing finalizer to request reboot so missing
marker selects the retained original recovery script/UI. Before confirmed
consumption retain power-off stop behavior to prevent relaunch loops. Never
retry consumption, claims, writes or reboot. Record distinct preflight status;
it cannot authorize a write or satisfy full-write PASS. Return to original
recovery is not proof of normal A health or automatic SSH availability.

One implementer owns tests/fixtures/sd-network-root/emmc_image_writer.c,
scripts/build_h616_reimage_candidate.py, scripts/build_h616_recovery_handoff.py,
scripts/prepare_h616_reimage_job.py, tests/test_h616_reimage_candidate.py,
tests/test_h616_recovery_handoff.py, tests/test_prepare_h616_reimage_job.py and
docs/hardware/host-h616-physical-preflight.md. Do not modify existing accepted
hardware records/requirements or claim they passed; coordinator documents the
clarification and pending hardware gate. No new dependencies/source downloads,
MCU/kernel/loader, services on hardware, real job preparation or media writes.

Focused actual C harnesses must prove target opens O_RDONLY, closes on pass and
refusal, excludes O_RDWR/transfer paths, validates both environment records, and
selects reboot only after confirmed consumption/unmount; uncertain/before-marker
stops retain poweroff. Signed-format/mode tests reject cross-purpose jobs and
invalid flag combinations; preserve current write builds. Reuse unchanged claim,
bulk-write/QEMU and U-Boot absent-marker fallback evidence. Small finalizer
fixtures may run if needed; no repeated full-image/QEMU transfer. Keep scratch
under512MiB and aggregate retained artifacts under64MiB, no full image copies.
Independent delivery verification is required. Any actual p5 staging, boot-policy
change or preflight boot needs exact target/artifact/recovery checks and an
immediate separate Sol review. urh-04 stays pending until measured hardware entry,
marker behavior, readonly admission and recovery return; urh-05 stays separate.
Retire this commissioning helper when supported recovery/update testing supplies
the same admission evidence.

## Delivery repair amendment — 2026-09-30

Independent delivery review of candidate `fafb87a` failed ppf-02: the shared
`verify_signed_stage_bundle` in `scripts/stage_h616_recovery_handoff.py` invokes
job verification with the default write purpose, rejecting a correctly signed
preflight job before staging. Preserve that failed candidate and verdict; do not
bypass staging verification. The eight original files remain assigned. Extend
the same bounded offline delivery to `scripts/stage_h616_recovery_handoff.py`,
`tests/test_recovery_handoff_stage.py`, and `tests/test_h616_live_stage_cli.py`
solely for purpose binding and its stage/journal/arm/activation regression tests.
The live adapter is an unchanged consumer of the shared verification function.
If repairing it requires production changes outside this ownership, return the
concrete gap for review before editing.

Validate the signed purpose against both the actual bundle's compiled mode and
artifact composition mode before staging and at the existing later revalidation
boundaries. An unsigned preflight label alone must never admit a write executable
or a write job as preflight. Keep default signed-reimage behavior and all existing
signature, source, target, journal, freshness, preservation and one-shot guards.
Tests must demonstrate positive preflight admission through the actual shared
staging verifier and consumers, cross-purpose and unsigned relabel refusal,
and unchanged write admission before any simulated media mutation. Use only
disposable offline fixtures; no live media, service launch or real jobs.

The same review found the tiny FIT insufficient for constraint 7 artifact size
and boot-memory evidence. Complete a representative offline composition using
retained pinned kernel/DTB/base initramfs and an inert, explicitly nondeployable
lab bundle with fixture signatures, never a physical job or claim. Record actual
compiled writer, appended initramfs and FIT sizes/hashes, load intervals and
bounded working memory against the existing H616 handoff constraints. Keep
scratch below 512 MiB and aggregate retained output below 64 MiB; avoid full
images, bulk transfer and repeated QEMU. If actual composition cannot fit these
limits, report the measured minimum and request a separate bounded allocation
before proceeding. Static interval/resource accounting does not prove physical
relocation, memory reliability or boot; those remain urh-04. This amendment does
not waive the resource check or change a hardware/release requirement.

A new separate approval must bind this amendment before repair. After repair,
submit fresh clean-commit evidence and obtain a fresh independent delivery
verifier; preserve the failed review and all earlier identities and hashes.
Physical urh-04/05 and immediate exact-operation review remain pending.
