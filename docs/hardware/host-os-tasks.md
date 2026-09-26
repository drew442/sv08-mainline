# Host OS completion checklist

Updated 2026-09-13. This is the completion gate for the new host, not a claim
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
- [x] Derive the board recovery root without changing the authoritative QEMU
  assembly, and test partition-only read-only selection with real partitioned
  VM success/integrity-refusal cases; see [board recovery](host-recovery-board.md).
- [x] Compose a clean host root with board packages, persistence hooks and
  administration UI; correct the missing runtime boot ID required by jobs.
  [Diagnostic composition](host-board-image.md) records first-boot scope and
  private pilot provisioning, which does not complete production onboarding.
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
- [x] Compose the offline boot-health service: validate the prepared boot record,
  select non-stopping boot admission for reconcile/confirm, check host OS health
  during a target trial, retain bounded failure evidence and gate Klipper until
  durable confirmation. The host image integration enables the health unit; this
  has a 50-second process deadline within its 60-second systemd limit and
  bounded persistent failure records when the state store is usable. This is
  unit, staging and host-selected disposable QEMU A→B/A fallback evidence.
  Signed installation, automatic U-Boot selection and attempt decrement, and
  H02/H07 hardware acceptance remain open.
- [ ] Finish board configuration, physical boot-service reconciliation,
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
- [x] Build/pin/measure Cockpit and independent GTK/input/accessibility closures;
  the immutable-root Cockpit TLS path now stores its generated identity under
  `/data` in an offline ARM64 service boot; see the [evidence](host-admin-cockpit-tls-persistence-evidence.md).
  [Cockpit integration](host-admin-cockpit.md) pins the host delta and tests
  real isolated PAM/sudo/helper sessions. The [independent recovery image](host-recovery-image.md)
  now has a measured closure and actual VM input/accessibility startup. Physical
  TLS, production owner provisioning and assembled-release acceptance remain open.
- [x] Implement bounded browser upload, signature/error/progress presentation and
  jobs that survive a closed browser or dropped LAN connection offline.
  [Authenticated upload](host-admin-upload.md) and [durable image jobs](host-admin-image-jobs.md)
  pass their actual Cockpit and independent-worker fixtures. Production/physical
  acceptance remains in the release and human checks below.
- [x] Complete independent ARM64 service-backed verification of ambiguous
  image-job disposition, including an orphaned RAUC install and writer exclusion.
  The implemented browser inspection/disposition retains the original unknown
  outcome and refuses new identities at full history; bounded history rollover
  remains a separately scoped delivery. See the [approved resolution
  task](../features/host-image-job-resolution/proposal.md) and
  [verified delivery](../features/host-image-job-resolution/record.json).
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
- [ ] Integrate the reviewed recovery-media policy and an explicit first-boot state
  initialization flow. Physical v3 boot confirmed that the current diagnostic image
  intentionally lacks both policy and `/data/sv08/state.json`, leaving recovery in
  read-only inspection mode as designed.
- [ ] Add touch text entry for recovery network/credential workflows where needed.

## Human and powered-printer tasks

Dispatch physical actions through the [coordinated human queue](coordinated-human-tasks.md).
Reuse one applicable observation across all consumers; the entries below retain
their detailed acceptance criteria and historical evidence.

### Latest board-image commissioning result — 2026-09-25

The v4 image was physically attempted after its verified write. Slot A failed
in `sv08-prepare.service`; on the next boot, changed SPL DRAM geometry was
reported, U-Boot found no valid slot, and the independent recovery GUI started.
The service exception is not in the receive-only capture. Offline image
inspection found that v4's boot initramfs omitted the persistent-identity hook
staged into rootfs, the likely cause of the prepare failure. The integrator now
regenerates the target initramfs, and finalization rejects an image without the
hook. The isolated recovery GUI reports that its own `/data/sv08/state.json`
and `recovery-media-policy.json` are absent; the built data filesystem contains
`state.json`, and the recovery message does not show device-side data loss. See
the [v4 first-boot record](host-board-image-20260924-v4-first-boot.md).

At the owner's request, the GL-RM1V2's persistent EDID was changed from its
2560×1440@60 `2k60` mode to a custom 1024×600@60 preferred mode. The updater
accepted it and the recovery display remains visible. The KVM's 2560×1440
capture format is independent; the printer's selected HDMI mode and the exact
touchscreen timing still need physical validation. The owner need not change
any cable or power state for this EDID record. A future A retry requires a
separate reviewed write/readback through H03.
The [v5 replacement candidate](host-board-image-20260925-v5.md) passed
independent offline review, was written once to the identified spare eMMC, and
passed a full direct-I/O readback hash. On 2026-09-25 the owner reinstalled it;
the A slot reached SSH with `/data` and Wi-Fi working. Cockpit failed because
TLS certificate generation targeted the immutable root. One A trial attempt
was consumed and trial confirmation remains masked; avoid reboot until the next
reviewed action. See the [v5 first-boot record](host-board-image-20260925-v5-first-boot.md).
The receive-only UART watcher missed SPL/U-Boot because its first device path was
stale; the corrected listener was opened after this boot and cannot recover it.

New feature development is paused by the owner. Existing host hardware-test
preparation continues. These physical tasks do not block independent authorized
preparation; the full checklist is a release gate, not a first-boot prerequisite.

- [x] Connect the documented USB-C **USB to UART** socket to Beelink and verify
  the console; [115200-baud marker capture](test-sv08-01-host-console.md) passed
  after replacing the cable on 2026-09-13. SSH is also reachable.
- [x] Start console logging before a subsequent boot and capture SPL/U-Boot/kernel
  output. The [2026-09-13 warm reboot](test-sv08-01-host-console.md) reached SSH
  with a new boot ID and no failed units. For the 2026-09-25 v5 boot the initial
  listener path was stale; a corrected listener was ready only after boot.
- [ ] Establish complete host power isolation for a true cold-boot capture:
  host uptime continued across the reported printer switch-off/on with the USB
  console attached. Determine the remaining power source before claiming a
  cold boot; do not assume the printer switch alone makes board work safe.
- [ ] Optionally attach HDMI capture and a controllable USB HID emulator to
  Beelink for graphical tests, preserving the physical touchscreen input path.

- [x] Development path: qualify a disposable SD launcher and read-only NFS root
  for a bounded Linux diagnostic. The physical v2 test passed; see the
  [result](host-sd-network-first-boot-20260926.md). This is not a full host OS
  or a supported recovery path. Keep the remaining distinction clear: the
  complete Debian host root has not been booted over NFS, and kernel/initramfs
  updates still require updating the SD. See the continuing
  [development assessment](host-network-boot-investigation.md).
- [ ] Optional release recovery path: qualify a removable SD launcher and
  read-only network root. The [investigation](host-network-boot-investigation.md)
  finds this potentially useful. The [192 MiB SD/NFS diagnostic](host-sd-network-root-prototype.md)
  passed one physical trial: SD loader, Linux, wired DHCP and read-only NFS root;
  see the [v2 result](host-sd-network-first-boot-20260926.md) and completed
  [H09 record](coordinated-human-tasks.md). The v1 trial stopped at the missing
  U-Boot `CONFIG_HASH_VERIFY` setting; the corrected v2 passed. This demonstrates
  a disposable development boot, not an authenticated recovery product or
  complete host OS. Complete-host NFS boot, eMMC boot-policy execution, signed recovery and
  fallback remain unverified. Do not change router PXE/TFTP options.

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
- [x] Build the complete factory-sized diagnostic disk and independently verify
  its bytes, partitions, SPL/environments, recovery and access metadata;
  [recorded result](host-board-image-20260913.json). Physical boot is separate.
- [x] Write the complete diagnostic image to the owner-identified spare through
  the USB reader; full direct-I/O readback and GPT checks passed on 2026-09-13.
  The [write record](host-board-image-20260913.json) distinguishes this from boot validation.
- [x] Owner reinstalled and powered the spare with logging active. SPL started,
  then stopped at `DRAM:`; HDMI stayed blank. Cold electrical isolation was not
  independently observed. [Failure evidence](host-board-image.md#first-physical-boot-stopped-in-spl-dram-initialization).
- [x] Build and independently review an [instrumented SPL](host-spl-diagnostics.md)
  with progress markers and bounded read-calibration waits, retaining electrical
  settings. Nine native poll cases and five A/B guard cases pass.
- [x] Owner returned the spare to the writer. The reviewed loader-only write,
  full-image comparison, GPT inspection and safe ejection passed. The
  [new media digest](host-spl-diagnostics-20260913.json) differs from the original download.
- [x] Owner reinstalled/powered the diagnostic spare. The [first A boot](host-board-first-boot.md)
  reached verified SSH, immutable state and HTTPS login. The earlier DRAM cause,
  reliable repeat boots, B and recovery remain unresolved.
- [x] Boot the rebuilt v2 full diagnostic image. Its first captured A boot
  reached the seeded `sv08` SSH account, Cockpit HTTPS, immutable state and zero
  failed units. Read-only enumeration found a connected HDMI interface, the
  touchscreen input and both wireless interfaces. The same loader selected a
  16-bit/512 MiB DRAM result on the first A boot and 32-bit/1 GiB on the second;
  see the [v2 board-image record](host-board-image-20260915-v2.json). The later
  attempts and recovery transition are recorded below. This is not a touch,
  Wi-Fi, camera, A/B, recovery, heater or motion test, and it does not establish
  repeatability or DRAM capacity.
- [x] Exercise the remaining diagnostic A attempts and the independent recovery
  selection under receive-only serial capture. The remaining two A boots reached
  serial login and owner-key SSH; the final counter reached zero and the next
  boot mounted recovery root and `/usr` read-only, with the local recovery UI
  process active and no failed units. The current recovery build intentionally
  lacks host-state/recovery-media integration, so only **Check storage** is
  available. A reviewable rearm pair is ready but has not been written.
- [x] **Human handoff — move the installed spare eMMC to the USB writer on
  Beelink.** Power the printer down, remove only the diagnostic spare and insert
  it into the identified USB reader. The prepared private 131,072-byte pair has
  SHA-256 `bd5a2f20268c5d85defbeb398f40e72434898ee0235cf7907d70fe262f76b93e`.
  Before writing, the operator will identify the reader, confirm the six reviewed
  PARTUUIDs, v5 loader hash and CRC-valid flag-3/flag-4 environments, then write
  only the two 64 KiB regions at offsets 4 MiB and 8 MiB, read both back, eject,
  reinstall and capture the next boot. Do not format, resize or auto-repair the
  GPT, and do not write the factory eMMC.
- [x] **Human handoff — reinstall the rearmed diagnostic spare and power the
  printer on after capture readiness is confirmed.** The factory eMMC remains
  untouched. The initial rearmed cycle reached normal A but its capture expired
  before power-on; the outstanding repeat below supplies that trace.
- [x] Repeat a rearmed A boot with a fresh receive-only capture. The captured
  attempt stopped after a false final DRAM controller initialization and before
  `DRAM:`, U-Boot, Linux or login. Reader inspection later confirmed the original
  flag-7/flag-6 environments and A attempts of 2/3 remained in place. See the
  [v2 board-image record](host-board-image-20260915-v2.json).
- [x] Build and review a guarded diagnostic loader that fail-stops before size
  calculation when final DRAM controller initialization fails. The offline v6
  artifact is recorded in [host-spl-diagnostics-20260915-v6.json](host-spl-diagnostics-20260915-v6.json);
  it has not been written or physically tested.
- [x] Write the reviewed v6 diagnostic loader at offset 8192 and verify its
  positional readback. The target identities, original v5 loader, CRC-valid
  flag-7/flag-6 environments and GPT warning were recorded; the reader is powered
  off. The temporary wrong-offset write was restored byte-for-byte before the
  successful positional write; details are in
  [host-spl-diagnostics-20260915-v6.json](host-spl-diagnostics-20260915-v6.json).
- [x] Reinstall the diagnostic spare and boot the v6 loader. The normal Debian
  serial login and Cockpit HTTPS endpoint appeared, but the intended early serial
  capture lacked device permission and retained no SPL output. See the
  [v6 artifact record](host-spl-diagnostics-20260915-v6.json).
- [x] Correct and prove receive-only serial capture access. A root-owned logger
  exclusively opened the identified bridge at 115200 8N1, recorded `ready`, and
  transmitted/captured zero bytes before clean closure. Start the same corrected
  logger before the next power cycle.
- [x] Consume the final A attempt only after the corrected logger recorded
  `ready`. The full trace confirms final DRAM initialization success, 1 GiB,
  U-Boot, Linux, login, owner-key SSH, Cockpit, zero failed units and inactive
  printer services. The newest CRC-valid environment is flag 9 with A exhausted.
- [x] Defer a duplicate v6 recovery-selection boot. The v6 change is confined to
  SPL before U-Boot; its U-Boot/FIT is byte-identical to the previously captured
  v5 recovery path, and the complete v6 normal boot validates the changed SPL
  path. Preserve the running host rather than requiring an unnecessary rearm.
  Recovery selection under v6 remains explicitly unproven.
- [x] Run a bounded non-persistent memory check on the rearmed normal A host.
  A 512 MiB userspace allocation passed full-buffer `0x00`, `0xaa` and `0x55`
  write/read hashes with no failed units. It does not establish full-memory,
  soak, cold-boot or DRAM-capacity reliability.
- [x] Validate a short passive MGS1 camera stream on the rearmed normal A host.
  Thirty 640×480 MJPEG frames decoded successfully from tmpfs storage, and the
  device was restored to 1280×720/25 fps. This does not establish long-duration
  streaming, video presentation or camera behavior while printing.
- [x] Fix immutable dpkg backup scheduling in the integrator; temporary physical
  condition test passed. The installed image still needs this fix in a future build.
- [x] Add `wpasupplicant` and `locales` to the pinned host baseline, and seed
  deterministic `C.UTF-8` locale defaults in the image builders. A fresh image
  build is still required before physical Wi-Fi/locale validation.
- [x] Correct diagnostic pointer formatting to the SPL-supported `%08lx` form,
  regenerate the patch hunk, and extend the native test to cover the shared wait
  helper. A fresh diagnostic artifact remains subject to independent review.
- [x] Capture one warm A reboot; same persistent generation, new boot ID and
  one A attempt remaining. MMC numbering changed; PARTUUID mounts passed.
- [ ] Confirm visible HDMI console/physical touch and test cold-start reliability.

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
