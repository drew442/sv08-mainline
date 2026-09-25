# Feature checklist

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
- [ ] The latest v5 A-slot boot reached SSH and persistent `/data`; Cockpit
  failed on immutable root and A-slot trial confirmation is masked. See its
  [first-boot findings](../hardware/host-board-image-20260925-v5-first-boot.md).
- [ ] Optional SD/network boot is under read-only investigation; it is not a
  supported recovery path. See the [investigation](../hardware/host-network-boot-investigation.md).
- [x] DRAM diagnostic loader with bounded failures and a captured successful
  final-validation path.
- [ ] Reconcile the unconfirmed v5 A-slot trial before a routine reboot. The
  current boot-health and RAUC units are masked; one A attempt has been consumed
  and the read-back environment showed two remaining after boot.
- [ ] Complete reproducible production boot-chain pins, physical power-loss tests,
  health confirmation and release-image assembly.

## Printer software and commissioning

- [x] Pinned Klipper, Moonraker, Mainsail and KlipperScreen packages assembled
  and tested offline.
- [x] Physical MCU USB update path verified for mainboard and toolhead.
- [ ] Activate the printer stack with the selected configuration.
- [ ] Validate sensors, fans, endstops, probe, motion, homing, gantry leveling,
  heaters, mesh and representative prints.

## Browser administration and updates

- [x] Cockpit host administration UI and local GTK recovery UI implemented and
  tested offline.
- [x] Physical Cockpit endpoint and owner-key SSH access to the diagnostic host.
- [x] Signed bundle admission, staging, RAUC backend, idle admission and automatic
  staging policy tested offline.
- [x] Browser upload, reconnect-safe image jobs and recovery archive export tested
  offline.
- [x] Interrupted image-job resolution independently verified offline; see the
  [delivery record](host-image-job-resolution/record.json).
- [ ] Deliver bounded image-job history rollover as a separate reviewed task.
- [ ] Add production onboarding, TLS, network/access forms, software catalog and
  complete assembled-system update testing.

## Recovery and user interfaces

- [x] Independent 512 MiB recovery image boots in ARM64 testing and supplies
  keyboard, mouse and touch diagnostic workflows.
- [x] Physical recovery selection was captured with the earlier diagnostic loader.
- [x] Read-only recovery diagnostics and verified archive export are implemented
  and tested offline.
- [ ] Integrate trusted recovery-media identification, signed restore, first-boot
  state initialization and preserved-slot recovery operations.
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
