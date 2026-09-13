# Host OS completion checklist

Updated 2026-09-12. This is the completion gate for the new host, not a claim
that all project work is complete. Printer availability and read-only host
enumeration were re-established on 2026-09-12; see the
[online evidence](test-sv08-01-online-20260912.md).

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
  The [exact 6.18.51 compilation experiment](host-kernel-compile.md) now pins and
  applies the kernel series and builds the kernel, modules and checked diagnostic
  device trees. The [physical one-shot trial](host-kernel-trial.md) reached SSH on
  6.18.51 and returned to the original kernel using the existing working loader.
  The targeted radio fixes, upstream regulatory signature selection and passive
  scan now pass; production packaging and association remain outstanding.
  [Debian kernel/board packages](host-kernel-packages.md) pass isolated installation.
  The [corrected board A/B loader](host-sv08-ab-boot.md) now builds with inspected
  SPL voltage settings, selected DT and compiled environment guard. Compose clean
  host/recovery roots and the complete disk before its physical trial.
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
  Transaction upload-lease composition now has real lock/exclusion tests;
  authenticated LAN endpoint and assembled coordinator wiring remain open.
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
- [x] Serialize automatic staging/arming with opt-out and reject malformed policy
  booleans before service admission; [policy tests](host-transactions.md#automatic-update-opt-out-boundary)
  cover manual operations and cancellation without implicitly undoing an armed update.
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
- [x] Independently rebuild Pycairo and streaming-form-data; preserve executable
  sections while normalizing debug paths, then assemble identical Moonraker debs
  and pass the browser/API file test. See [wheel evidence](host-compiled-wheels.md).
- [ ] Finish independent rebuilds of the remaining packages/compiled wheels; retain complete source,
  toolchain and license manifests. A successful single build is insufficient.
- [ ] Harden the recovery intake completion receipt against concurrent lock replacement;
  retain the independently revalidated assembly gates. See the
  [recorded reporting limitation](host-recovery-image.md#resources-and-preservation).
- [ ] Assemble finalized boot/root/recovery/data filesystems and signed release
  artifacts only after boot/persistence integration; capacity fixtures are not
  deployable images. Test complete 8 GB occupancy including update staging/state.

## Administration and recovery UI completion

- [x] Implement responsive Cockpit host page and native GTK recovery screen with
  shared review/apply semantics; [UI evidence](host-admin-ui.md) records scope.
- [x] Connect policy and image transaction adapters; test stale review, preserved
  generations, cancellation and customization guards without hardware writes.
- [x] Keep recovery diagnostics usable with missing/corrupt read-only state.
- [ ] Build/pin/measure Cockpit and independent GTK/input/accessibility closures;
  integrate actual authenticated login, owner provisioning and persistent TLS keys.
  [Cockpit integration](host-admin-cockpit.md) pins the host delta and tests
  real isolated PAM/sudo/helper sessions. The [independent recovery image](host-recovery-image.md)
  now has a measured closure and actual VM input/accessibility startup. Production
  identity/TLS and assembled-release acceptance remain open.
- [x] Implement bounded browser upload, signature/error/progress presentation and
  jobs that survive a closed browser or dropped LAN connection offline.
  [Authenticated upload](host-admin-upload.md) and [durable image jobs](host-admin-image-jobs.md)
  pass their actual Cockpit and independent-worker fixtures. Production/physical
  acceptance remains in the release and human checks below.
- [ ] Deliver reviewed resolution of ambiguous image-job receipts and bounded
  history rollover, preserving retry identities and original outcomes. Include
  RAUC service-side inactivity evidence before releasing the admission gate;
  current ambiguous/full ledgers remain blocked without automatic replay. The
  [approved resolution task](../features/host-image-job-resolution/proposal.md)
  precedes a separately scoped history-rollover delivery.
- [ ] Finish additional-software catalog, dependency/space preview, admitted APT
  install/remove, service configuration and customization reconciliation.
- [ ] Implement network/access forms, connectivity rollback, host naming/hosts
  consistency and controlled idle restart. Ordinary administration must need no shell.
- [x] Implement reviewed recovery data export with checksummed/readback-verified
  archives, source/destination change refusal, GTK workflow and actual read-only
  source/FAT32 fixture; [export evidence](host-recovery-export.md).
- [x] Connect the installed GTK entry to verified pre-mounted export admission;
  [offline evidence](host-recovery-media.md) covers filesystem/block read-only
  preservation, actual cancellation/apply, device reuse and shared exclusion.
- [x] Combine recovery archive verification into one complete bounded readback;
  [measurements and regressions](host-recovery-readback.md) retain corruption,
  truncation, media and publication checks with approximately 50% fewer logical reads.
- [x] Assemble the complete 512 MiB independent ARM64 recovery diagnostic image;
  [offline evidence](host-recovery-image.md) covers actual boot/restart, virtual
  keyboard/mouse/direct touch, identity refusals and retained package metadata.
- [ ] Connect independent recovery target identification, preserved-slot boot,
  USB/LAN signed restore and export of readable user data without formatting it.
  Integrate/review the trusted premounter with the independent image, including the
  complete system-media inventory and participation by every media mutator. The
  [approved export composition](../features/host-recovery-export-composition/proposal.md)
  covers the next independent boot-to-export journey; restoration remains separate.
- [ ] Add touch text entry for recovery network/credential workflows where needed.

## Human and powered-printer tasks

New feature development is paused by the owner. Existing host hardware-test
preparation continues. These physical tasks do not block independent authorized
preparation; the full checklist is a release gate, not a first-boot prerequisite.

- [x] Connect the documented USB-C **USB to UART** socket to Beelink and verify
  the console; [115200-baud marker capture](test-sv08-01-host-console.md) passed
  after replacing the cable on 2026-09-13. SSH is also reachable.
- [x] Start console logging before a subsequent boot and capture SPL/U-Boot/kernel
  output. The [2026-09-13 warm reboot](test-sv08-01-host-console.md) reached SSH
  with a new boot ID and no failed units. The logger has now been stopped.
- [ ] Establish complete host power isolation for a true cold-boot capture:
  host uptime continued across the reported printer switch-off/on with the USB
  console attached. Determine the remaining power source before claiming a
  cold boot; do not assume the printer switch alone makes board work safe.
- [ ] Optionally attach HDMI capture and a controllable USB HID emulator to
  Beelink for graphical tests, preserving the physical touchscreen input path.

- [ ] When access is convenient, provide readable host PCB revision, DRAM/radio
  and PMIC markings/photos, or board documents that identify the installed host.
  Do not remove heatsinks or powered components merely to obtain a marking.
- [x] Restore printer availability and collect radio SDIO identity/driver,
  camera descriptor and V4L2 formats, boot-file and display enumeration evidence;
  [2026-09-12 results](test-sv08-01-online-20260912.md) preserve operation limits.
- [x] Test negotiated MJPEG 640×480/15 fps capture on the new kernel: 60 frames
  decoded successfully, 14.7648 fps measured. [Physical evidence](host-kernel-trial.md)
  also records successful radio initialization and a passive scan over wired SSH.
- [ ] Validate Wi-Fi association/authentication and sustained operation on the
  selected new kernel without disrupting the recovery connection. Validate
  sustained camera streaming and UI presentation; short capture is insufficient.
- [x] Capture the first new kernel trial and return to the original kernel using
  the vendor loader; [physical evidence](host-kernel-trial.md) passed. A new
  U-Boot/A/B loader still requires its own physical trial and capture.
- [ ] Preserve current spare-module data/image before writing a future reviewed
  whole-device candidate. The current single-root system needs image replacement,
  not an untested live repartition.
  The owner accepts the existing backups and recovery path; another full backup
  is optional and must not be imposed as a prerequisite for the first trial.
- [ ] With a reviewed bootable candidate: test cold boots, storage/network/USB,
  required onboard Wi-Fi and HDMI/touch, camera, thermal/cpufreq and watchdog.
- [ ] Test the local recovery UI with HDMI touch only, keyboard only, and
  keyboard + mouse; verify focus, cancellation, USB selection and readable errors.
  Use a reviewed independently booted recovery candidate with named-profile root,
  namespace and removable-medium evidence; test actual media removal/replacement.
- [ ] Attend recovery and power-interruption tests with loads safe and backed-up
  expendable data; demonstrate A→B→A, failed trials, both slots failed and USB-reader
  restoration. Restore MCU backups separately when that test is planned.
- [ ] Complete sensor checks, probing/motion/heater commissioning and representative
  prints under the named modified hardware profile before release support.

The existing [recovery tasks](test-sv08-01-recovery-tasks.md) and
[sensor bring-up](test-sv08-01-sensor-bringup.md) remain applicable. No outstanding
boot, update or printing acceptance criterion is satisfied merely by building
application packages or by passing workstation emulation checks.
