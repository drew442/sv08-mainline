# Host OS completion checklist

Updated 2026-09-09. This is the completion gate for the new host, not a claim
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

## Offline implementation and release work still required

- [ ] Finish the source-reproducible board boot chain: resolve complete U-Boot,
  TF-A, kernel and driver source/patch pins and licenses; compare board assumptions
  with captured evidence. Do not deploy the unverified CB1-equivalence claim.
- [ ] Validate relocated GPT discovery in the chosen U-Boot build; allocate and
  test redundant environment storage outside GPT, SPL and partitions.
- [ ] Implement immutable/writable boot mounts, persistent system identity and
  per-release state generations from decision 0004. Mode changes must occur at
  controlled idle reboot and preserve customizations; no shared root overlay.
- [ ] Integrate RAUC paired boot/root slots, health confirmation, fallback,
  independent recovery, signed bundles and offline key handling.
- [ ] Integrate services, authorization, local onboarding, network provisioning,
  idle update staging, next-boot activation, opt-out and customization blocking.
  Keep Moonraker's independent software updater disabled for image-managed apps.
- [ ] Exercise update/mode/package races, late state writes before reboot,
  migration failures, no space, corrupted/wrong-target bundles, rollback and
  customized-image update refusal using actual integration components.
- [ ] Review Mainsail audit findings and complete browser/API/UI workload tests.
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
