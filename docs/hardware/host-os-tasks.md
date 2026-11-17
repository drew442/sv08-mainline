# Host OS release acceptance

Current acceptance checklist for [the release route](../remaining-work-plan.md). Old implementation TODOs are retained in [historical evidence](../history/host-os-tasks-through-20261116.md), not another active queue. Physical actions are coordinated through [the single H queue](coordinated-human-tasks.md); a checkbox is not operation authority.

## Mandatory remaining release gates

- [ ] Supported board boot/kernel/driver and MCU compatibility binding for the actual test printer; reliable cold/warm behaviour with no unexplained known boot failures.
- [ ] Supported release/commissioning composition path, preserving diagnostic mode and actual service/health/admission guards; no generic unmask/start shortcut.
- [ ] Clean-owner install/state initialisation, unique identity and usable ordinary/admin access without project-private seeds or cloned credentials.
- [ ] Complete 7,818,182,656-byte layout and 512 MiB recovery fit, inodes, state copy/update staging and reserve measured on the real candidate; larger spare storage is not proof.
- [ ] Actual fitted hardware, input association, stop/fans/motion/homing/heat, native calibration persistence, representative prints and controls via [the staged session](test-sv08-01-commissioning-session.md).
- [ ] Required Wi-Fi reconnect/HDMI/touch/USB and bounded concurrent workload; camera deferral explicitly preserves a usable path for existing hardware.
- [ ] Final-artifact install/update/fallback and independent recovery boundaries, including selected credible interrupted-operation/power-loss cases, preserve state and a usable recovery route.
- [ ] Release-recommended MCU definition assignment and observed match/mismatch/unknown presentation, USB maintenance and mismatch refusal where required; never auto-flash on rollback.
- [ ] Rebuild from pinned inputs; distribute exact artifacts, public corresponding source/shipped notices and tested install/recovery/support instructions after release authority.

## Already accepted software/mechanisms

Reuse [native complete-stack restore/reboot/rollback](../features/recovery-printer-stack/native-evidence.md), [physical healthy update/fallback](../features/physical-automatic-update-validation/completion.md), [attended SD reimage](../features/h12-attended-sd-reimage/physical-completion.md), [configuration and native calibration](../features/stock-printer-readiness/evidence.md), [selected package rebuilds](../features/package-reproducibility-qualification/evidence.md) and [notice closure](../features/release-qualification-closure/evidence.md). Preserve scope: native KVM is not SD/printing proof; repaired physical diagnostic slots are not an untouched final-release image. New candidate differences receive applicable checks, not blanket repetition.

Immutable/writable modes and administration/identity/network capabilities remain required and implemented; validate changed integration. Arbitrary custom-image reconstruction may remain blocked under ADR 0004. Fully automatic MCU orchestration, new hardware families, Internet delivery and broad optimisation are not prerequisites for this release. RAM maintenance is abandoned and automatic recovery return remains deferred; do not recreate old gates.

## Human and powered-printer tasks

This anchor is retained for existing feature requirements. Use the
[single coordinated queue](coordinated-human-tasks.md) and
[configured-printer session](test-sv08-01-commissioning-session.md).
The gates above are the current remaining scope; archived checkboxes do not
request new physical operations.
