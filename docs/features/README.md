# Feature checklist

Current goals are in the [goal record](../../.codex/current-goals.md). Minimal H12
SD reimaging, commissioning-host readiness, default-curve ambient checks and the
installed Cockpit component page are complete within their documented limits.
Physical input checks and fine calibration are owner-deferred. Historical boot
observations do not establish current counters or assignments; abandoned RAM,
permission/replay and cold-capture work must not be resumed.

This is the short project overview. A checked item has the evidence described in
its linked record; it is not automatically a supported-release claim. Detailed
host and hardware acceptance work remains in the
[host checklist](../hardware/host-os-tasks.md) and the
[roadmap](../roadmap.md).

## Foundation and recovery material

- [x] Stock-first project scope, hardware profiles, pinned upstream inputs and
  evidence rules.
- [x] Factory host recovery material retained: the original eMMC is preserved,
  its user-area image is privately retained, and a spare eMMC is available.
- [x] Mainboard and toolhead MCU SWD backups, option-byte records and USB update
  recovery paths.
- [x] Reproducible Katapult and matching Klipper MCU builds; both MCUs have been
  updated and reached a no-output ready state.
- [ ] Record installed host PCB revision and complete host power-isolation evidence.

## Host boot and operating system

- [x] Debian ARM64 host baseline with immutable default and supported writable
  mode, persistent state and factory-8-GB layout checks.
- [x] A/B boot policy, redundant raw environments, RAUC installation/cancellation
  and rollback tested offline.
- [x] Source-built diagnostic host image, recovery root and A/B disk composition.
- [x] Physical diagnostic-host boot with full SPL, U-Boot, Linux, serial-login,
  SSH and Cockpit evidence; read-only root and persistent data verified.
- [x] [Installed commissioning-host repairs](commissioning-host-readiness/installed-completion.md)
  passed normal restart, relay restart and persistent authenticated access.
  Production boot-health/RAUC remains masked on this diagnostic host.
- [x] Disposable SD launcher and read-only NFS-root diagnostic boot passed on
  `test-sv08-01`; see the [physical result](../hardware/host-sd-network-first-boot-20260926.md).
- [x] The named SD host test reached Linux, authenticated SSH and GUI; see its
  [physical result](../hardware/host-sd-recovery-host-first-boot-20260929.md).
  Later minimal H12 SD recovery and reimaging also passed.
- [ ] Complete-host NFS and production signed network recovery remain unvalidated;
  see the [development assessment](../hardware/host-network-boot-investigation.md).
- [x] DRAM diagnostic loader with bounded failures and a captured successful
  final-validation path.
- [x] [Minimal attended SD reimage](h12-attended-sd-reimage/physical-completion.md)
  and normal eMMC return passed. Superseded RAM/permission preflights are abandoned.
- [ ] Complete reproducible production boot-chain pins, physical power-loss tests,
  health confirmation and release-image assembly.

## Printer software and commissioning

- [x] Pinned Klipper, Moonraker, Mainsail and KlipperScreen packages assembled
  and tested offline.
- [x] Physical MCU USB update path verified for mainboard and toolhead.
- [x] [Default-curve ambient sensor baseline](sensor-default-commissioning/intake.md#corrected-ambient-baseline-completed)
  passed with a chamber BLE reference; physical transitions/calibration remain deferred.
- [ ] Activate the printer stack with the selected configuration.
- [ ] Validate sensors, fans, endstops, probe, motion, homing, gantry leveling,
  heaters, mesh and representative prints.

## Browser administration and updates

- [x] Cockpit host administration UI and local GTK recovery UI implemented and
  tested offline.
- [x] Physical Cockpit endpoint and owner-key SSH access to the diagnostic host.
- [x] [Installed printer hardware page](printer-component-configuration/installed-evidence.md):
  board/component presets, private drafts and reviewed inactive candidates.
- [x] Signed bundle admission, staging, RAUC backend, idle admission and automatic
  staging policy tested offline.
- [x] Browser upload, reconnect-safe image jobs and recovery archive export tested
  offline.
- [x] Interrupted image-job resolution independently verified offline; see the
  [delivery record](host-image-job-resolution/record.json).
- [x] [Bounded image-job history rollover](host-image-history-rollover/record.json)
  passed independent offline verification.
- [ ] Add production onboarding, TLS, network/access forms, software catalog and
  complete assembled-system update testing.

## Recovery and user interfaces

- [x] Independent 512 MiB recovery image boots in ARM64 testing and supplies
  keyboard, mouse and touch diagnostic workflows.
- [x] Physical recovery selection was captured with the earlier diagnostic loader.
- [x] Read-only recovery diagnostics and verified archive export are implemented
  and tested offline.
- [x] Trusted independent boot-to-export composition is independently accepted
  offline; see the [record](host-recovery-export-composition/record.json).
- [x] Recovery intake completion receipt binds parsed lock content and refuses
  changed/unreadable input; [independent offline verification](recovery-intake-receipt-binding/record.json) passed.
- [ ] Complete signed restore, first-boot state initialization and preserved-slot
  recovery operations, with physical export/media acceptance still required.
- [ ] Test recovery UI visually with HDMI touch, keyboard, and keyboard plus mouse.

## Hardware integration and peripherals

- [x] Wired networking, serial console, HDMI/touch enumeration and passive MGS1
  camera capture verified on the new kernel.
- [x] Short passive camera capture and bounded memory-pattern check completed on
  the diagnostic host.
- [ ] Validate Wi-Fi association and sustained camera streaming/presentation.
- [ ] Test HDMI/touch interaction, cold-power behavior and recovery under an
  identified power-isolation arrangement.

## Project delivery

- [x] Feature suggestion, delegated approval, implementation and verification
  workflow established with durable records.
- [x] Host/recovery software evidence and physical diagnostic-host evidence are
  committed and pushed.
- [ ] Complete the stock-hardware conversion guide and supported-release criteria.
- [ ] Add and validate modified-electronics profiles after the stock profile.
