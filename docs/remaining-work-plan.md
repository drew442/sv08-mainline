# Route to the first supported configured-printer release

Current delivery contract, owner decisions of 2026-11-17. This replaces the historical execution order, not its evidence. Current implementation/handoff: [.codex/current-goals.md](../.codex/current-goals.md). Existing feature records hold source acceptance; the [single human queue](hardware/coordinated-human-tasks.md) owns physical dispatch. No new scheduler/backlog is introduced.

## Release promise

Target the actual test printer with its real fitted bed, hotend, sensors and electronics selected through definitions. Do not infer its present hardware/configuration from old captures, import another printer's measurements or require restoration to factory bed/hotend. Record the exact tested configuration; generic factory thermal support and other electronics variants are separate claims. Definition contracts use representative configurations and boundary cases, not exhaustive physical combinations.

An owner can install, establish private access, select supported fitted hardware, commission/calibrate, print with usable controls, update without losing data/identity/customisations, and recover independently. Initial distribution is LAN-delivered signed bundles. Internet discovery is outside this initial promise; existing update policy is retained. Public corresponding source and notices still accompany distributed artifacts. Reproducible means rebuildable from recorded pinned inputs with differences explained; selected-package byte reproducibility is already measured, while complete-image reproducibility remains unproven.

## Mandatory and deferred scope

| Capability | First-release obligation | Outside initial release critical path |
| --- | --- | --- |
| Board/install | Verified board support, correct boot boundaries, independent recovery, complete factory 7,818,182,656-byte capacity including update/state-copy/inode reserves, repeatable clean installation | Other board families/OS distributions; larger storage cannot hide failure |
| Owner access | Clean-owner setup without project-private credentials; unique persistent CA/SSH/account identity; usable Cockpit/Mainsail | Extra onboarding styles/cloud integrations |
| Printing | Actual fitted definitions, verified MCU identities, inputs/stop/fans/motion/homing/heat, measured calibration/SAVE_CONFIG, representative prints and pause/resume/cancel | Every parameter combination, pressure-based automatic offset, performance tuning, fine sensor-curve fitting |
| Updates | Signed automatic provenance, explicit manual exceptions, integrity/physical/idle guards, preservation and A/B fallback; LAN delivery | Internet infrastructure and new policy features |
| MCU maintenance | Per-release recommended firmware assigned using immutable definitions; observed discrepancy/unknown shown; documented USB maintenance and compatibility refusal | Automatic MCU flashing or atomic host/two-MCU orchestration. A rollback never automatically reflashes MCUs |
| Modes/software | Existing immutable and writable modes, guarded package operations and retained customisations | Arbitrary automatic custom-image reconstruction; safely block unreconciled activation |
| Recovery | Independent HDMI/touch/keyboard UI, identified media/targets, signed restore, export/data restore, preserved identity, return to normal | RAM maintenance and automatic recovery return remain withdrawn/deferred per owner decision |
| Peripherals | Wi-Fi, HDMI/touch, essential USB and bounded combined workload; camera deferral must retain a usable path for existing camera | Broad accessory matrices, tuning/optional integrations |
| Rebuild/publication | Pinned rebuildable artifacts, selected-package proof, shipped notices and concrete corresponding-source/distribution obligations, exact artifact/source hashes, installation/recovery guide | Cross-toolchain/compiler-bootstrap/all-distro-source rebuilding and new whole-disk byte-identity promises |

Definitions distinguish **recommended** from measured installed MCU firmware. New release generations receive that release's recommendation. Older generations retain their binding. Never overwrite hardware selections or calibration to assign firmware recommendations. A mismatch is an owner-visible condition, not permission to flash or bypass existing admission/compatibility checks. Legacy/unavailable observations remain unknown. Releases that change host/MCU compatibility require a supported explicit maintenance route before printing; rollback of OS alone does not roll back flash.

## Ordered delivery and stop conditions

1. **Release/commissioning candidate path (autonomous source work).** Extend existing composition/finalisation/manifest paths rather than add a distribution or parallel builder. Preserve diagnostic masks/gates. Provide explicit clean-owner state/identity/access initialisation, board compatibility and supported commissioning/service activation. The current diagnostic composer and release-preparation report deliberately do not grant release readiness. Stop this stage when tests exercise the actual intended installation/setup/activation route, without private pilot seeds, invented health markers or generic unmask/start instructions.
2. **Freeze and assemble one candidate.** Reuse verified packages. Run prerequisite checks before assembly, then build the normal A/B, recovery and data artifacts with the actual layout. Measure storage/inodes and realistic staging/state-copy headroom. Bind source, tools, artifacts, firmware definitions and supported target. No unrelated image copies. A source change invalidates only its affected outputs/acceptance.
3. **Commission the configured printer.** Prepare the [existing staged session](hardware/test-sv08-01-commissioning-session.md), exact candidate/configuration, stop/recovery route and consequential-operation review before requesting attendance. Verify current fitted parts and execute inputs, stop/fans/motion, homing, heat, calibration and representative printing. Physical checks need observations; unavailable attendance is a task dependency, not a software failure. Do not test forced fallback/destructive recovery during first-print setup.
4. **Qualify the candidate's remaining boundaries.** Combine required peripherals and concurrent print/UI/network workload with the same campaign. Reuse native PR17 and H12/H13 mechanism evidence where inputs/assumptions match; test final artifact-specific install/recovery/update differences and credible power-loss paths with expendable data. No arbitrary soak/reboot counts or exhaustive fault matrix: name the failure question and exit condition before expensive work.
5. **Publish the supported release.** Repeat documented clean installation, complete current-source/data/notice obligations, and ship artifacts, hashes, source, support scope, concrete limitations and tested recovery instructions. Source-ready, built, bench-tested, print-tested and publicly released are different states. Owner-authorised release publication is separate from a source PR.

Completion is an owner using the documented supported installation/configuration/print/update/recovery journeys, with the tested artifacts published. A green software report alone is insufficient.

## Evidence reuse and failures

Keep inexpensive change regressions; use native installed/parser/browser checks for changed integration boundaries; reserve assembled/hardware acceptance for the candidate. Reuse passes by relevant input/environment/assumption hashes, not by latest commit date alone. Preserve failed/skipped/incomplete evidence. Classify each new failure as product defect, harness defect, environment/prerequisite failure, stale evidence/input or expected refusal before expanding scope/rebuilding. Required checks cannot be waived for cost. One diagnosed repair cycle concerns the same unresolved cause, not the entire delivery.

Each proposal answers: promised outcome/material defect; supporting evidence; smallest sufficient action and resource cost; stop condition. Dependency/tooling work without a concrete release consequence is deferred. Do not reinterpret truthful historical limitations as mandatory new projects.

## Already delivered — reuse, do not reopen by default

- [Complete configuration generation](features/complete-printer-configuration/proposal.md), [readiness/calibration](features/stock-printer-readiness/evidence.md) and the implemented administration/identity/UI workflows.
- [Native complete-stack recovery](features/recovery-printer-stack/native-evidence.md): archive/configuration/services/persistence/rollback/regression pass; physical printer/SD/power-loss/printing not claimed.
- [Actual healthy update and fallback](features/physical-automatic-update-validation/completion.md): mechanism evidence includes reviewed continuation repairs; qualify relevant final-artifact differences, not pretend it was untouched release-image proof.
- [Attended SD reimage](features/h12-attended-sd-reimage/physical-completion.md), [selected package reproducibility](features/package-reproducibility-qualification/evidence.md) and [notice closure](features/release-qualification-closure/evidence.md).
- [Current diagnostic full-image source/software qualification](features/current-release-qualification/evidence.md): not deployable printing-release proof.

Historical narrative: [previous plan](history/remaining-work-through-20261116.md). Preserve old IDs/hashes/evidence; superseded queue disposition is not fabricated completion. Fine calibration, proprietary pressure automation and print power-loss resumption remain deferred.
