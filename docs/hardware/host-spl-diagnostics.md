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
wait helper's `%08lx` formatting. An independent `gpt-5.6-sol` medium-effort
delivery review passed the artifact, source, bounds, configuration, and sandbox
checks (see the private review record). The loader-only write to the identified
USB eMMC completed and direct readback verified the v3 loader hash. The strict
whole-image comparison stopped at 4 MiB because the mutable U-Boot environment
differs from the factory baseline; no claim of whole-image equality is made. The
artifact remains diagnostic and is not a release image.

The v3 loader was then booted on `test-sv08-01` after a controlled power cycle.
Serial evidence shows the corrected DRAM diagnostics, successful 1 GiB result,
U-Boot bootflow, Linux `6.18.51-sv08-candidate1`, read-only root and `/usr`,
the recovery UI, both Klipper STM32 devices, and the MGS1 camera. Network access
was not validated because the previously recorded `.141` address did not answer.

On 2026-09-14, a controlled warm reboot from the subsequently successful normal
A host boot did not complete. Receive-only serial output stopped during a later
DRAM candidate probe after 68,426 bytes, without another `DRAM:  1 GiB`, U-Boot,
or Linux marker. The capture remained unchanged while the receive service stayed
healthy. This is a measured diagnostic-loader warm-boot failure, not a conclusion
about the DRAM hardware cause; no reset, loader write, or environment write was
issued after observing it.

The final visible candidate was the row-size probe (`cols=8`, `rows=17`), whose
controller initialization returned false. Upstream `mctl_auto_detect_dram_size()`
then unconditionally copies to the attempted DRAM address. That makes the
diagnostic trace stop before it can report the failed probe cleanly. The next
diagnostic artifact will retain every electrical setting and successful-path
operation, but checks both size-probe calls. On failure it prints either
`SV08-DRAM: size columns init failed` or `SV08-DRAM: size rows init failed` and
calls `hang()` before any DRAM access. This is a fail-stop observability change,
not a training workaround or a warm-boot fix. It requires a fresh build, artifact
review, and a loader-only eMMC write before physical testing.

The fresh v4 build is recorded in
[`host-spl-diagnostics-20260914-v4.json`](host-spl-diagnostics-20260914-v4.json).
It produced a 786,105-byte loader with SHA-256
`5ead4d129a42140cbf0502da0ec66c753d4aec97d5f993408f8cdde055ac3d41`.
The eGON checksum and SPL SRAM boundary were checked, its FIT and effective
configuration match v3 byte-for-byte, the nine native calibration cases pass,
and all five sandbox invalid-state cases reach the guarded recovery path. Linked
disassembly confirms either false size-probe result prints its marker then calls
`hang()` before the relevant `memcpy`. This remains an offline artifact until a
separate delivery review accepts it for a bounded loader-only write.

Independent review accepted the v4 safety properties, then found that the two
new marker strings used a literal backslash-n. No hardware action was taken. The
next fresh artifact corrects that output-only defect before delivery review; v4
is retained as evidence but is not the artifact to write.

The corrected artifact is
[`host-spl-diagnostics-20260914-v5.json`](host-spl-diagnostics-20260914-v5.json):
loader SHA-256
`78948fdaf6ca695c126d35d52b76493c04b49828d3a8ff183719faccdb9f9e48`.
Its two linked failure markers contain real newlines, while the FIT, TF-A and
effective configuration still match v4. It awaits its separate delivery review.

The independent v5 delivery review passed. The identified spare was then checked
through the recorded USB reader: its capacity, six PARTUUIDs, unmounted state,
valid raw environments, and v3 loader hash all matched the recorded target. At
23:53:50 UTC on 2026-09-14, only the 786,105-byte loader span at offset 8192 was
replaced. A direct-I/O comparison and a separate logical readback both returned
v5 SHA-256 `78948fdaf6ca695c126d35d52b76493c04b49828d3a8ff183719faccdb9f9e48`.
The partition geometry remained unchanged and the USB reader was powered off.
The [v5 record](host-spl-diagnostics-20260914-v5.json) has the target evidence.
No full-media equality claim is made because the valid redundant U-Boot
environment intentionally differs from the earlier factory baseline. Reinstall
the spare with printer and external USB power disconnected; the next operation
is a captured physical boot, not a heating, motion, firmware, or environment
write.

That captured v5 cold boot completed at 23:55:22 UTC. The failing warm-reboot
candidate from the prior v3 trace (`cols=8`, `rows=17`) returned success on this
attempt; the real-newline failure guards did not fire. The trace contains one
each of `DRAM: 1 GiB`, U-Boot 2026.07, Linux
`6.18.51-sv08-candidate1`, and the serial `sv08` login prompt. Cockpit HTTPS
returned 200 and TCP port 22 accepted connections. SSH public-key authentication
remains rejected because the installed image predates the persistent-key seeding
correction; no live configuration change was made. This is one successful cold
boot, not a repeatability result or a DRAM fix.

## v2 full-image boot: differing auto-detection result

The complete v2 diagnostic image embeds the exact v5 loader, verified by its
loader-span hash before the eMMC write and by the v2 physical readback. Its
first captured boot reached Linux and administration services, but the loader
selected a different successful rank/width candidate: one rank at **16-bit**
width, 10 columns and 15 rows. It consequently reported **512 MiB**, with Linux
exposing 485,376 KiB after reservations. A controlled second v2 A boot selected
one rank at **32-bit** width with the same columns/rows and reported 1 GiB, with
Linux `MemTotal` of 999,672 KiB. The earlier v5 cold capture from the same loader
source and artifact also selected 32-bit width and reported 1 GiB.

This is evidence that rank/width auto-detection is not yet a reliable basis for
identifying the installed DRAM capacity. It does not identify the board memory,
justify an electrical change, or establish a stable fallback configuration. The
v2 capture nevertheless reached U-Boot, Linux and the `sv08` login prompt; its
raw capture hash and read-only host observations are in the
[v2 board-image record](host-board-image-20260915-v2.json). Further reboot or
memory-stress testing must use an explicit, reviewed attempt budget.

## Captured final-size-validation failure

After rearming the diagnostic environments, a fresh receive-only capture reached
the 32-bit rank/width candidate and both size probes, then the final selected
10-column/15-row `mctl_core_init()` returned false. The existing diagnostic
source printed `SV08-DRAM: size validation` and continued into size calculation;
the capture stopped at 16,583 bytes with no `DRAM:` result, U-Boot, Linux or login
marker. This is the same fail-open diagnostic gap that the earlier two size-probe
guards were intended to prevent, now observed at final validation.

The next diagnostic source revision adds only a matching final-validation guard:
on a false final `mctl_core_init()`, it prints
`SV08-DRAM: final size validation init failed` and calls `hang()` before the size
calculation. It retains all electrical settings and successful-path behavior.
The revision needs a fresh build, source/native test, artifact review and a
separately identified loader-only write before it can be used on hardware.

The guarded v6 artifact is now recorded in
[`host-spl-diagnostics-20260915-v6.json`](host-spl-diagnostics-20260915-v6.json).
It is 786,105 bytes and has SHA-256
`166b4251ffb3c2db6d3b90536650c399b3e5443b06e5c78a0ad2f8ca9fbf6b40`.
The built source changes only the final `mctl_core_init()` failure path. Linked
SPL disassembly confirms a false return prints the new marker and calls `hang()`
before `mctl_calc_size()`. Its FIT, TF-A, effective configuration and every byte
from loader offset 40,960 onward equal v5; 25,980 changed bytes are confined to
the SPL region. The eGON checksum, SPL bounds, nine native helper cases and five
sandbox invalid-state cases pass. It remains a non-deployable diagnostic and has
not yet physically booted.

The identified spare was inspected with its two CRC-valid raw environments at
flags 7 and 6 (`BOOT_A_LEFT=2` and `3`). The v6 loader-only write at byte 8192
then passed a positional readback hash check, leaving both environments unchanged.
An initial implementation error wrote the payload immediately after the second
environment rather than at byte 8192; that 786,105-byte region did not overlap
either environment and was restored byte-for-byte from the verified v2 full image
before the successful positional write. The reader was powered off. The factory-
sized GPT warning on the 32 GB spare remains and was not repaired. Full details,
including the restoration hash, are in the v6 artifact record. The next operation
was a captured physical boot.

The physical v6 boot reached the normal Debian 13 `sv08` serial login and Cockpit
HTTPS endpoint at port 9090. The intended early serial capture did not open: its
unprivileged account lacked permission for the dialout-owned bridge when it
appeared. A late root-owned receive-only capture records the normal login prompt
but cannot show SPL output. Thus the successful loader path ran, while the new
false-final-initialization marker and fail-stop branch remain unobserved. The
factory account name `sovol` was rejected, while the rebuilt image account `sv08`
accepted the owner key. No login recovery or live configuration change was
attempted. The artifact record retains the capture limitation and the next serial
capture must prove its device access before another power cycle.

A root-owned receive-only preflight subsequently opened the same bridge
exclusively at 115200 8N1, recorded its `ready` event, captured zero bytes and
transmitted zero bytes before cleanly closing. The next power-cycle capture must
use that corrected owner and prove `ready` before power is applied.
