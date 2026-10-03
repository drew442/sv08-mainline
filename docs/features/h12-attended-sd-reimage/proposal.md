# H12 attended SD reimage

Kind: feature. Author: root/coordinator, with project_planner input. Date: 2026-10-03.
This is the implementation record for the owner-selected H12 scope, not a new
owner product decision or a second backlog.

## Problem and intended outcome

At baseline dd6b7f6 the independent SD host boots recovery/SSH, but its recovery
provider offers export only. The prior writer requires the now-abandoned RAM,
signed-claim, entropy and expiry path. Turning on the existing Restore button
would not implement a complete eMMC image transfer. The October 2 physical SD
boot is historical evidence, not today's readiness.

Deliver the accepted journey: independent SD -> integrated target/image checks ->
explicit Yes/No -> full image write, flush and readback -> manual restart ->
observed installed-system normal boot. The newer ten-point H12 decision governs
this path. Use a reviewed image size/checksum; do not add permission or image-signing
work to this delivery. Unrelated host A/B update signing remains unchanged.

## Bounded implementation and alternatives

Reuse the existing SD composer, pinned kernel/DT/root loader and installed GTK
closure. Add a small SD-only Python backend and dedicated native screen using
existing recovery UI patterns and an SD-only display-service drop-in. This keeps
the existing no-Linux-command recovery requirement while avoiding changes to host
A/B administration or the global recovery/export flow. No new dependencies,
servers, browser UI, updater framework, RAM initramfs/writer, signing/claims,
randomness, expiry or RTC correction. Automatic launch/return and loop detection
are excluded. No separate preflight/rehearsal feature or milestone.

Coordinator prepares an independently backed read-only image file and expected
size/SHA-256, plus the measured intended eMMC identity. Reuse the existing NFS
source if its installed mount closure is available; independently backed SD/USB
file is a bounded alternative. Image-source setup is separate from the write and
does not mount target partitions. No generic upload/storage discovery framework.
The UI displays/selects the configured image and identified target, with explicit
whole-disk replacement wording: this operation overwrites the image range,
including image-contained data/environment; it cannot promise file preservation.

Python stdlib and supported Linux interfaces provide bounded transfer/hash loops,
fsync and cache-flushed readback. Standard tools may replace byte-loop glue if
that reduces code without reopening a different target after confirmation. Custom
glue is only for missing SD-specific admission, confirmation and result handling;
retire it when supported recovery supplies the same attended whole-disk path.

One implementer owns: runtime/sv08_sd_reimage.py, runtime/sv08_sd_reimage_ui.py,
scripts/build_sd_recovery_host.py, tests/test_sd_reimage.py,
tests/sd_reimage_gtk.py, tests/sd_reimage_vm.py, tests/test_sd_recovery_host.py,
tests/sd_recovery_host_vm.py,
configs/host-os/sd-recovery-host/sv08-recovery-display.service.d/reimage.conf,
and docs/hardware/host-sd-recovery-host.md. Coordinator owns goals, proposal/record,
shared documentation, commits/pushes and physical operations. The worker is not
alone in the repository and must preserve others' changes. Do not edit upstream,
legacy evidence, shared feature records, host A/B controllers or GPIO/MCU code.

## Acceptance and tasks

`implement` owns offline code/composition and focused evidence. A fresh independent
verifier reviews the complete delivery; planner/author/integration producer cannot
verify it. `prepare-session` is coordinator hardware preparation, followed by
`physical-reimage` for the actual attended outcome. Hardware tasks reference H12
in the existing human queue and depend only on this replacement delivery.

- `sd-scope`: installed SD-only composition includes exact backend/UI/drop-in
  bytes; changes invalidate compressed usr caching. Root/loader pins, capacity and
  printer-service masks remain intact. No legacy permission/RAM dependency or
  automatic write/reboot. Preserve other recovery and host-update behavior.
- `admission`: identify whole user-area eMMC by controller/CID and opened dev_t;
  reject boot partitions, ambiguity, source on target, mounted/in-use/held/swap
  target, insufficient capacity, missing/empty/wrong-size/hash source. Hold source
  and verified target descriptors; serialize and recheck after confirmation before
  mutation. Production never admits regular files as targets; explicit fixtures do.
- `confirmation`: display image/target and destructive effect. Default No, No,
  close and absent answer cause no target write. Each invocation requires Yes;
  restart does not start flashing. Prevent duplicate starts within one invocation;
  leave repeated prompt handling to the operator.
- `transfer`: actual bounded write/short-write handling, flush, then cache-flushed
  full image-range readback. Byte count/hash match is required for success; source
  loss, truncation, write/flush/readback failures report failure without automatic
  retry/rearm/reboot. No new power-failure transaction framework or resumable writer.
- `installed`: exercise actual installed ARM64 backend/GTK from independent virtual
  SD with disposable separate target and supported source. Focused refusal/No,
  Yes/write/readback and relaunch cases establish installed wiring and mount-tool
  closure; record artifact hashes/limits. No broad failure matrix or physical
  compatibility claim from QEMU. Standard prescribed runs can be coordinator-run;
  use integration agent only when diagnosis is needed.
- `session`: actual current SD access, accepted tool/image hash/size, identified
  spare unused by running system, independent source and attended Yes/No interface;
  existing authorization reconciled and exact hardware review completed before
  operation. No separate rehearsal, entropy/clock/claim or factory fallback gate.
- `physical`: attended affirmative confirmation, actual complete image write/flush/
  full readback match, clear result, operator manual restart and observed normal
  installed-system root/access. H12 completes only here. Record remaining limitations.

## Human dependencies and scope boundary

Use H12 in docs/hardware/coordinated-human-tasks.md. Prepare everything reviewable
before requesting current physical facts/attendance. Owner selects affirmative Yes
for the identified destructive write, preserves power through completion and
performs the manual restart/SD removal or boot selection as actually needed.
Stored factory module remains untouched; SD recovery is the sufficient fallback.
No new backup capture, factory restore trial, adapter purchase, soldering, heater,
motion, MCU, release or complete cold-capture work. Missing target identity and
hardware conditions require observation, not guessed constants. Existing hardware
reviews and scoped authority remain; feature approval grants neither hardware
access nor an immediate full-image write.
