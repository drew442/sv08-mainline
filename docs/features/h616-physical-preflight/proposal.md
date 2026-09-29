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
