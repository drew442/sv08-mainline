# One-shot kernel trial on the existing spare

2026-09-13. This is a temporary test of the new kernel/DT against the existing
Debian bring-up root and vendor bootloader. It does not activate A/B or validate
printing. The [compile record](host-kernel-compile.md) and
[decision 0015](../decisions/0015-board-kernel-compile-baseline.md) define scope.

## Loader and target evidence

The [physical console capture](test-sv08-01-host-console.md) establishes the
vendor loader's `mmc 1:1` boot-script load path. The captured bootloader prefix
contains `bootdelay=-2`, `boot_scripts=boot.scr.uimg boot.scr`,
`boot_prefixes=/ /boot/`, and a scanner that continues to the next script when
`source` returns. It also contains the `fatrm` command/help. These are binary
defaults plus observed boot behavior, not an interactive environment dump.
The new dispatcher must be tested unarmed on hardware before those source
observations are promoted to a working fallback.

Fresh SSH inspection identifies the spare as a 31,272,730,624-byte MMC, product
SBG6PX, root on mmcblk2p2 and FAT boot on mmcblk2p1. Boot had 220,110,848 bytes
free and root about 6.09 GB free at inspection. No existing `boot.scr.uimg` or
extlinux configuration was found in the checked boot locations. UUIDs and raw
identity/hash records stay under ignored `local/host-kernel-61851/`.

A pre-trial read-only runtime capture reports vendor host temperatures of
44.774–45.584°C, CPU policy frequency 1.2 GHz, and AXP1530-named DCDC1/2/3
readbacks of 0.96/1.10/1.50 V. ALDO1/DLDO1 report 1.8/3.3 V. These are kernel
driver reports, not instrument measurements. The private
`vendor-runtime-baseline.json` supplies comparison values for the candidate.

## Dispatcher and staging boundaries

The [template](../../configs/host-os/diagnostic-boot.cmd.in) is rendered with the
freshly identified root UUID and target **`mmc 1:1`**, then wrapped with
`mkimage -A arm -T script -C none`. Render `@TRIAL_DIR@` as
`sv08-trial-61851-c1` and `@RADIO_BOOTARG@` as `module_blacklist=8189fs` for
the first wired trial. Its directory contains `Image`, `board.dtb`, `uInitrd` and, only when
separately armed, `armed`. Never reuse the marker for another artifact set.

1. Hash and retain the original boot files, confirm the target and absence of
   an existing dispatcher, and stage only the new **unarmed** dispatcher.
2. Start console logging and reboot. Require its return-to-original marker,
   unchanged original kernel and SSH, and unchanged original boot-file hashes.
3. After the kernel/module build and artifact review, stage the alternate files
   and unique module release without replacing the vendor files. Build a matching
   initramfs with Debian initramfs-tools and wrap it using the existing legacy
   ARM/Linux/ramdisk/gzip format. Inspect contents and module dependencies.
4. Check file sizes against the actual loader addresses: kernel 0x40080000,
   DT 0x4fa00000, script 0x4fc00000 and initrd 0x4ff00000. Account for kernel
   relocation/initrd expansion and firmware reservations, not only file sizes.
   Hash back the installed artifacts before creating the marker.
5. Arm and reboot with logging. The marker is consumed before any candidate
   load; failed deletion, a retained marker or any failed load refuses handoff.
   Candidate bootargs bypass vendor BoardEnv overlays and transiently mask
   Klipper, Moonraker and KlipperScreen services.
6. Inspect kernel, actual DT, root, regulator reports, Ethernet/SSH, USB,
   temperatures and failed units. Reboot to confirm return to the original
   kernel because the marker was consumed. Keep heater/motion tests separate.

The original boot.scr, boot.cmd, BoardEnv, Image, uInitrd, DT/overlay files and
vendor module directory remain the fallback. Do not save U-Boot environment or
change the raw bootloader. A hung candidate may still require the owner's reset
with all relevant power sources considered; the USB cable may keep the host
powered. Serial control-line reset has not been established.

## Offline validation

```sh
python3 tests/diagnostic_boot.py \
  --uboot build/u-boot-sandbox-v1/u-boot \
  --work build/diagnostic-boot-v1 --execute
```

Seven invocations pass against real temporary FAT files and U-Boot 2026.07
sandbox: marker consumption/returned boot, second invocation, no marker, missing
Image, deletion refusal using a nonempty directory, wrong-device refusal, and
subsequent correct-device use of the preserved marker. Only the target interface
and root UUID are substituted. Real `booti` receives dummy offline payloads and
returns with sandbox's "Booting is not supported" message; neither Linux execution
nor ARM64 image-header validation is claimed. The script's original
scanner variables remain unchanged. This is not the vendor 2021.10 binary or a
power-interruption test. No unattended update policy uses this temporary marker.

## Unarmed physical result

The independently reviewed dispatcher was staged on test-sv08-01 after fresh
root/boot UUID, capacity and original-file hash checks. Its 1,527-byte legacy
script image has SHA-256
`8074e3be0652a9f7ccaecabcd758383351ed210594d430e02f7d0a92f782f430`.
It was generated from project commit `37385d4`, with a fixed build timestamp,
the private root UUID and target `mmc 1:1`. Its installed readback matched.
No trial marker or candidate boot files were staged in this step.

With exclusive serial capture running, an SSH-requested clean reboot produced:

```text
Found U-Boot script /boot.scr.uimg
SV08_TRIAL_RETURN_TO_ORIGINAL
Found U-Boot script /boot.scr
```

SSH returned on `5.16.17-sun50iw9` with a new boot ID and no failed systemd units.
The original Image, uInitrd, boot.scr, boot.cmd and BoardEnv hashes were unchanged.
This verifies actual vendor-loader script precedence and unarmed fallback;
marker deletion and candidate kernel execution remain untested on hardware.

Private staging evidence and console capture are under
`local/host-kernel-61851/unarmed-dispatcher/`. The retained console snapshot has
SHA-256 `4a62517b5be64d869d0d1a3cbf692923230d510d08ab9d4fbea2785d4764fc0a`.
## Armed wired trial and return to original

The completed [artifact set](host-kernel-compile-20260913.json) was reviewed,
installed separately and read back with matching hashes. The dispatcher was
updated only to add `module_blacklist=8189fs`, isolating the radio source defects
described in the compile record. Its replacement is 1,551 bytes, SHA-256
`3ab8ae4cfa6dbd9e32f44005293f1e953b5916cf9248986c3ab91dcbe639ecff`.
Two independent fresh seven-case sandbox runs passed. Independent review found
the previously tested unarmed control flow unchanged.

On 2026-09-13 the armed warm reboot consumed its marker, loaded the reviewed
files, executed `booti`, and reached SSH on **6.18.51-sv08-candidate1**. DHCP
assigned a different address; the existing SSH host key verified the printer.
The live DT passed the diagnostic property checks, including the 105°C critical
trip and absent CPU OPP references. There were no failed systemd units. All three
printer services were inactive and masked; `8189fs` was absent from loaded modules.

Measured host evidence, with PCB revision still unknown:

- Systemd reported 4.676 seconds kernel and 6.448 seconds userspace, 11.124 total;
  this excludes bootloader time and is one diagnostic run, not a benchmark.
- Ethernet negotiated 100 Mbps/full duplex using the AC300 PHY and supported SSH.
- HDMI reported connected with 1024×600 preferred mode; USB touch, MGS1 camera
  and both Klipper MCU interfaces enumerated. Display usability, touch events,
  camera capture and MCU protocol operation were not tested in this trial.
- Thermal drivers reported approximately 46–48°C. CPU clock reported 1.008 GHz
  and its supply 1.0 V; GPU/system and DRAM supplies reported 0.96 and 1.50 V.
  These are driver reports, not instrument measurements or load validation.
- PWM5 requested the AC300 clock. Its driver has no `get_state` operation, so
  debugfs's zero/disabled “actual” fields are unavailable readback, not proof of
  a disabled physical clock. Ethernet operation supplies functional evidence.

The expected CPU-frequency probe failure reflects the intentionally removed OPP
references. An SDIO voltage-range warning also exists in the vendor baseline.
The candidate reported invalid/missing wireless regulatory database signature;
radio packaging must resolve this before Wi-Fi validation. No panic was observed.

A second clean reboot, with the marker absent, returned through the original
boot.scr to **5.16.17-sun50iw9** and SSH at the prior address. No systemd units
failed; all five original boot-file hashes remained unchanged. This proves the
tested warm one-shot trial and subsequent fallback, not power-loss resilience,
cold boot, A/B deployment, GPU/DVFS, Wi-Fi or printing support.

Private runtime, live DT and fallback receipts are under
`local/host-kernel-61851/`. The combined console snapshot SHA-256 is
`2e129df5cb4720beda91bbefe086af5f03a8e76419aa4b63342a98fd4883d01f`.
Candidate files and the updated dispatcher remain installed **unarmed**; ordinary
boots use the original kernel. Removing the added dispatcher restores the prior
dispatcher arrangement.

## Radio follow-up preparation

The separately reviewed [radio patch](../../patches/rtl8189fs/README.md) addresses
the three identified startup/strict-array defects. The follow-up uses a new
`@TRIAL_DIR@` of `sv08-trial-61851-c2` and an empty `@RADIO_BOOTARG@`; all kernel,
DT and initramfs bytes remain the same. Both template variants pass seven sandbox
cases. The patched candidate-only module replaces its prior file after retaining
that file privately; vendor modules are untouched. The c1 marker is not reused.

Debian package `wireless-regdb` version `2026.05.30-1~deb13u1`, installed
`/usr/share/doc/wireless-regdb/README.Debian` (2026-02-13, read 2026-09-13),
prescribes `update-alternatives --set regulatory.db /lib/firmware/regulatory.db-upstream`
for custom upstream kernels. The follow-up selects that existing alternative.
The database payload is identical; its signature changes to the upstream-trusted
one. Signature verification stays enabled. The previous shared selection was
automatic/Debian; restore with `update-alternatives --auto regulatory.db`.
This is a shared firmware-link change, not a slot-isolated setting. Production
packaging must choose the appropriate signature for its selected kernel.
