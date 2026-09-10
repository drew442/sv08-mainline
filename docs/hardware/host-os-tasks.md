# Host OS completion checklist

Updated 2026-09-10. This is the completion gate for the new host, not a claim
that all project work is complete. Printer remains offline for this work.

## Completed offline

- [x] Factory-capacity Debian baseline and conservative slot-content budgets.
- [x] Pinned Klipper, Moonraker, Mainsail and KlipperScreen package assembly.
- [x] Hash-locked ARM64 runtimes; separate compiler chroot and source wheel provenance.
- [x] Moonraker loopback API with no failed components/warnings and no MCU connection.
- [x] KlipperScreen virtual-display window and local test-Moonraker connection.
- [x] Complete stack populated into a 2 GiB ext4 fixture with successful fsck.
- [x] Two identical fresh Mainsail builds with preserved unique precache entries.
- [x] Ustreamer package candidate for the retained camera.
- [x] Explicit standard-GPT/SPL collision reproduction and relocated-GPT fixture checks.
- [x] Actual U-Boot sandbox discovery of relocated GPT and bounded A/B selection.
- [x] State-generation, SQLite WAL, rollback and mode/customization regression tests.
- [x] Real mount-namespace tests for immutable/writable roots and explicit persistence.
- [x] Full Debian ARM64 QEMU boots through immutable → writable → immutable,
  preserving customization, config, PID 1 identity, hostname and SSH host key.
- [x] Full ARM64 A → B → A boots verify late configuration/database copy,
  separate trial state, paired mounts and fallback with shared artifacts preserved;
  see [Linux rollback evidence](host-rollback-build.md).
- [x] Real writable APT/dpkg installation, ordinary service activation and package
  record/file preservation after returning to immutable mode.
- [x] Two identical clean RAUC ARM64 package builds and actual inactive ext4/vfat
  partition installation on the distro kernel; see [RAUC evidence](host-rauc-build.md).
- [x] Signed verity bundle and actual paired inactive-slot RAUC file installation.
- [x] Read-only admission checks reject signed layout/state/Klipper mismatches;
  see [bundle policy evidence](host-bundle-policy.md). Builder cross-checks and
  coordinator wiring remain outstanding.
- [x] Untrusted-key, wrong-compatible, corrupt-payload and corrupt-signature rejection with all slot
  files unchanged. See [state/update evidence](host-state-build.md).

## Offline implementation and release work still required

- [x] Compile pinned upstream U-Boot/TF-A plus the reviewed CB1 board patches
  twice with identical binaries; [compile evidence](host-cb1-boot-compile.md)
  records the inherited 720 MHz DRAM clock and unverified hardware assumptions.
- [ ] Finish the source-reproducible board boot chain: resolve complete U-Boot,
  TF-A, kernel and driver source/patch pins and licenses; compare board assumptions
  with captured evidence. Do not deploy the unverified CB1-equivalence claim.
- [x] Allocate redundant raw environment regions outside GPT/SPL/partitions; test
  real RAUC/libubootenv/sandbox writes, corruption fallback and recovery dispatch.
  See [environment evidence](host-environment-build.md).
- [ ] Wire the environment to the verified board MMC index/default loader and
  complete physical power-loss validation; sandbox results do not establish these.
- [ ] Finish OS persistence integration beyond the tested state/mount implementation:
  boot tests now cover PID 1 identity, persistent system state and core service
  startup in a VM; extend them to the remaining application services and hardware. Implement controlled idle mode-change reboot.
  Preserve customizations and avoid a shared root overlay.
- [x] Implement durable transaction ordering and failure-injection tests; see
  [transaction integration](host-transactions.md). Production admission/backend/health
  wiring remains separate.
- [x] Bound early-boot preparation with deadlines and reboot on failure; actual
  ARM64 identity-failure and timeout tests pass. See [boot failure evidence](host-boot-failure.md).
- [x] Connect real RAUC/U-Boot device backend to transaction and idle admission;
  the ARM64 VM verifies install/hash/arm/cancel and final-attempt counter behavior.
  See [backend evidence](host-rauc-backend.md).
- [x] Implement private bounded upload intake, verified publication, exclusive
  install leases and explicit cleanup; see [staging evidence](host-upload-staging.md).
  Authenticated LAN endpoint and coordinator wiring remain open.
- [x] Implement transaction reconciliation classification and interrupted-arming
  journal repair with failure-injection tests; no slot selection or inferred health.
- [ ] Finish board configuration, boot-service reconciliation wiring,
  health confirmation, fallback, independent recovery and offline
  release-key handling. Signed metadata admission and device backend tests are
  complete; they do not make the candidate deployable.
- [x] Implement and separately package atomic Klipper idle admission; native and
  ARM64 reactor/dispatcher race tests pass. See [admission evidence](host-update-admission.md).
  Real ARM64 systemd/Moonraker boundary tests also pass with simulated printer
  status. Complete Klipper configuration activation and hardware checks remain open.
- [ ] Integrate services, authorization, local onboarding, network provisioning,
  idle update staging, next-boot activation, opt-out and customization blocking.
  Keep Moonraker's independent software updater disabled for image-managed apps.
- [x] Check state-copy blocks/inodes at staging and trial preparation, including
  sparse expansion, the full late-copy allowance and refusal before installation.
  See [capacity admission](host-transactions.md#state-copy-capacity-admission).
- [ ] Exercise update/mode/package races, late state writes before reboot,
  migration failures, no space, rollback and customized-image update refusal
  across the assembled system. Library failure tests and actual RAUC malformed
  bundle rejection now pass; live admission and power-cut tests remain open.
- [x] Review Mainsail dependency reachability and pin compatible js-yaml/nanoid
  fixes; two fresh patched package builds match. See [audit evidence](host-mainsail-audit.md).
- [x] Browser startup, real packaged Moonraker initialization and configuration
  upload/read/delete pass in a loopback-only namespace with Klipper disconnected.
- [ ] Resolve remaining framework/tooling findings and complete browser/API/UI workload tests.
  Archive-version reporting and deterministic precache ordering now have tested
  patches; retire them when upstream provides equivalent support.
- [ ] Independently rebuild packages and compiled wheels; retain complete source,
  toolchain and license manifests. A successful single build is insufficient.
- [ ] Assemble finalized boot/root/recovery/data filesystems and signed release
  artifacts only after boot/persistence integration; capacity fixtures are not
  deployable images. Test complete 8 GB occupancy including update staging/state.

## Human and powered-printer tasks

These do not prevent the independent offline work above.

- [ ] When access is convenient, provide readable host PCB revision, DRAM/radio
  and PMIC markings/photos, or board documents that identify the installed host.
  Do not remove heatsinks or powered components merely to obtain a marking.
- [ ] Restore printer availability for read-only radio SDIO identity/driver,
  camera formats, boot environment and display diagnostics. Confirm availability
  in the session; no probing is needed while it is deliberately offline.
- [ ] Arrange boot-console capture for the first new boot-chain test where
  practical; retain the factory eMMC and the verified private MCU backups.
- [ ] Preserve current spare-module data/image before writing a future reviewed
  whole-device candidate. The current single-root system needs image replacement,
  not an untested live repartition.
- [ ] With a reviewed bootable candidate: test cold boots, storage/network/USB,
  required onboard Wi-Fi and HDMI/touch, camera, thermal/cpufreq and watchdog.
- [ ] Attend recovery and power-interruption tests with loads safe and backed-up
  expendable data; demonstrate A→B→A, failed trials, both slots failed and USB-reader
  restoration. Restore MCU backups separately when that test is planned.
- [ ] Complete sensor checks, probing/motion/heater commissioning and representative
  prints under the named modified hardware profile before release support.

The existing [recovery tasks](test-sv08-01-recovery-tasks.md) and
[sensor bring-up](test-sv08-01-sensor-bringup.md) remain applicable. No outstanding
boot, update or printing acceptance criterion is satisfied merely by building
application packages or by passing workstation emulation checks.
