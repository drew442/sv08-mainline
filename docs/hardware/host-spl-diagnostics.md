# H616 SPL memory-initialization diagnostics

2026-09-13, test-sv08-01; PCB revision remains unknown. This is continuation of
physical host bring-up, not a new product feature or a production DRAM fix.
The [first full-image boot](host-board-image.md#first-physical-boot-stopped-in-spl-dram-initialization)
stopped at `DRAM:`. A separate diagnostic artifact adds visibility without
selecting unverified electrical settings.

## Scope and review

The [diagnostic manifest](../../configs/host-os/sv08-boot-dram-diagnostic.json)
adds one [temporary patch](../../patches/u-boot/0004-sv08-dram-diagnostics.patch)
to the existing pinned U-Boot/TF-A/board integration. The previous manifest and
artifact remain historical. The effective configuration, voltage/clock/timing
settings, rank/width search order, register writes, A/B environment and kernel/OS
payloads are retained. Serial output changes elapsed timing; it can change the
symptom, so successful diagnostic execution alone is not memory stability proof.

Progress messages identify DRAM entry, candidate geometry, system/controller
initialization, training stages and waits with register/mask/expected value.
Two read-calibration loops previously had no time limit. The diagnostic helper
retains completion-before-error priority and returns ordinary error bits to the
existing retry logic. A one-second timeout prints the last sampled status and
calls `hang()`. It does not reboot or continue to boot with untrained memory.
Existing generic DRAM wait timeouts retain their original `panic()` behavior,
which can reset this configuration; their messages now include the last status.
A bus access or stopped timer itself cannot be bounded by a software timer.

Independent proposal review approved this narrow diagnostic scope with an
unchanged electrical configuration, separate artifact review and a bounded
loader write. Delivery review caught that `panic()` resets this build; the new
calibration timeout was corrected to `hang()` before artifact acceptance.
Private review receipts, source comparison and raw board evidence stay in
`local/feature-workflow/spl-diagnostic/`. This short continuation record follows
[the existing review decision](../decisions/0011-feature-agent-workflow.md).

The [native C test](../../tests/dram_diagnostic.py) extracts the helper from the
actual patched source and executes scripted register/time sequences: full/half
width completion, completion with error bits, partial completion, immediate and
delayed errors, both stuck masks, and unsigned timer wrap. Nine cases pass.
This is not an emulation of the controller or proof of physical training.

## Reproduce

Use the same pinned archives, compiler and CB1 board patches as the
[base loader](host-sv08-ab-boot.md), a fresh output directory, and:

```sh
python3 scripts/build_cb1_boot_candidate.py \
  --config configs/host-os/sv08-boot-dram-diagnostic.json \
  --work build/sv08-dram-diagnostic-new \
  --uboot-archive build/ab-source-intake/u-boot.tar.gz \
  --tfa-archive build/ab-source-intake/tf-a-c2a0e708.tar.gz \
  --patch-directory local/os-design-20260909/armbian/patch/u-boot/v2026.07-sunxi64/board_bigtreetech-cb1 \
  --execute
python3 tests/dram_diagnostic.py \
  --source build/sv08-dram-diagnostic-new/u-boot-source
python3 tests/uboot_board_candidate.py \
  --build build/sv08-dram-diagnostic-new \
  --sandbox build/u-boot-sandbox-v1/u-boot
```

Review the actual ROM checksum, SPL SRAM/code/BSS bounds, final FIT contents,
compiled electrical configuration and guarded environment before writing.
Builder success alone does not check all of those conditions. The first Beelink
build lacked the host GnuTLS development header; after installing build
prerequisites, use the fresh v2 result, not that failed v1 directory.

The [artifact record](host-spl-diagnostics-20260913.json) identifies the exact
compiled output. Independent review recomputed the 40,960-byte ROM checksum,
checked SPL code/BSS bounds and the actual halt instruction path, and found the
effective configuration, entire FIT and TF-A byte-identical to the baseline.
All five existing A/B guard sandbox cases passed against the linked environment.
The 786,105-byte loader ends at disk byte 794,297. It remains a non-deployable
diagnostic, not a release.

## Hardware continuation

The owner returned the spare to the same USB reader. Its capacity, six partition
identities and unmounted state were checked, then all 7,818,182,656 bytes were
read with direct I/O. The hash still matched the original complete image. The
first 16 MiB was preserved privately; no additional backup prerequisite was
introduced.

Only an independently reviewed loader span starting at byte 8192 and ending
below 1 MiB may be changed. Compare the entire image footprint after writing
against the original image with exactly that span replaced; check GPT and eject
before removal. The resulting whole-image digest is different from the original
compressed download and must be recorded separately. Neither redundant raw
environment nor any filesystem partition is part of this write. Extra capacity
beyond the factory-sized image is outside the readback scope.

The write completed at 07:11:36 UTC on 2026-09-13. Exactly 786,105 loader bytes
were written at offset 8192. Direct-I/O readback compared every byte of the
7,818,182,656-byte footprint against the original with that exact replacement;
all other bytes matched. GPT inspection matched the original geometry and all
partitions remained unmounted. The USB writer was safely powered off. New media
SHA-256 (not the original download checksum):

```text
64ae94f42fde30f88891762b144604d27cf2bb8db2769a388b90f4365cba0f9f
```

Reinstall with mains and every USB power source disconnected.
Start serial capture before reconnecting USB or switching on. This attempt is
for diagnosis; HDMI can still remain blank, and no heater or motion request is
part of it. The factory module and the accepted USB writer/ST-Link paths remain
available. The [first physical diagnostic A boot](host-board-first-boot.md) succeeded;
repeatability and the exact earlier failure cause remain unresolved. That report
also records a tiny-printf formatting defect in these diagnostic messages.

## Provenance and retirement

Primary source: U-Boot commit `ece349ade2973e220f524ce59e59711cc919263f`,
`arch/arm/mach-sunxi/dram_sun50i_h616.c`, `dram_helpers.c`, `dram_dw_helpers.c`,
`board/sunxi/board.c`, `lib/panic.c` and `lib/hang.c`, read 2026-09-13 in the pinned
source tree. The patch follows those files' GPL-2.0+ license. No `upstream/`
working tree was modified. Remove diagnostic logging after identifying the
cause; submit a minimal generally useful timeout/error fix upstream only once
its controller behavior and failure policy have hardware evidence. Retain this
artifact record as failed/diagnostic evidence, not a supported release.


## Corrected v3 build

After the first physical boots, the `%p` formatter issue was corrected and the
patch was regenerated with valid hunk counts. A fresh Beelink build completed
from the pinned inputs; its loader is 786,105 bytes with SHA-256
`f0cba95ba8434c5cf684d874ded4f5caa937ce952e575fe377c4da7e00661827`.
The native helper test again passes nine scripted cases and now checks the shared
wait helper's `%08lx` formatting. This v3 artifact is retained for independent
review; it has not been written to hardware. The installed diagnostic loader is
unchanged and remains the tested A/boot source.
