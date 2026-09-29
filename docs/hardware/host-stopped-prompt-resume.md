# Resume the stopped SD loader

2026-09-29, test-sv08-01, owner-reported H616_JC_6Z_V1.2. This is a bounded
[approved correction](../features/sd-stopped-prompt-resume/record.json) within the
writerless-eMMC goal. Optional new features remain paused.

The guarded keyboard return physically emitted all four reviewed reports after
live exclusive UART admission. The durable 18,955-byte capture records systemd
SIGINT, ordered shutdown, SPL/DRAM initialisation, U-Boot 2026.07, both MMC
controllers and the countdown. The controller sent only the countdown-interrupt
space and stopped at `CB1@uboot:~$ ` because it expected `=> ` and mistook the
actual prompt for a Linux shell. No MMC/fatload/hash/source commands were sent.
The independent supervisor recreated a receive-only collector; its measured
LimitFSIZE is 4194304 and Restart=no. This does not prove successful SD Linux
return, redundant eMMC counters, RTC retention, touch or printer functions.

Prompt provenance: retained effective new.config SHA-256
`6acb5de178be927a6c0cd71f906f5cf51f23a7ae2d2d87e880e33849536857bf`,
line738 CONFIG_SYS_PROMPT="CB1@uboot:~$ ", and private UART capture
`local/sd-recovery-host/guarded-return-first.raw` SHA-256
`ed9074ded59d4aec42f11bbc95e4e2cd21b7283ba6a89336687fc7ff2c0102e9`.
Sources accessed 2026-09-29. MMC0 bad-CRC/default-environment output concerns
this SD loader's selected environment source; it establishes no eMMC counter
values. Boot messages reporting a PMIC are software observations, not a verified
physical inventory change.

The [controller](../../scripts/sv08_serial_boot_route.py) now recognises only the
exact configured prompt at a line boundary including its trailing space. It
removes that exact prompt for Linux-shell detection; other login/Password/shell
output still refuses, including forbidden output sharing a read with the valid
prompt. Normal countdown routing uses the same measured prompt.

Explicit `sd-resume` defaults to inspection. Its physical policy must retain
fresh_environment_reviewed=false and the existing exact one-return exception,
and require stopped_uboot_reviewed, no_intervening_text_sender_reviewed and
no_residual_command_reviewed to be literally true, plus the exact captured
transcript SHA. Missing/changed admission refuses before capture/serial/TX.
The coordinator must establish that only the previous interrupt space was sent
and that receive-only capture has been the only UART owner since. Historical
capture is not current prompt proof: after exclusive UART and private durable
capture admission, send one empty newline to obtain a fresh exact prompt.
Unknown/Linux/missing prompt stops; no second newline or retry. The empty newline
would execute an empty Linux command, but residual input is separately excluded.

Only after fresh prompt admission does the unchanged command allowlist select
MMC0, require SD identity, load exactly1075 boot.scr bytes, validate exact SHA
`ce18bf74e3d8ae840bfb90129ba28515ba89cbd2759bc32ecd0418f6987d1ddd`,
and source the script. Existing payload hashes, root/envelope args, exact command
echoes, fixed addresses, UART topology/termios checks, competing-descriptor
refusal, capture-before-TX fsync and 1MiB capture limit remain. Nothing is sent
after source. No HID, reset, power/control-line, environment/media write,
writer/job/claim/marker rearming or command-shell input is added.

Independent delivery and fresh Sol/high exact-operation review precede any UART
operation. Replace private operation-review provenance with the actual passing
review; do not reuse failed reviews or pretend counters are fresh. Preserve the
consumed HID attempt receipt. Retain independently surviving capture restoration
with absolute 4MiB-per-file caps and no systemd restart. Reserve one fresh private
resume capture, retain stdout/stderr, and stop on any uncertain outcome. Do not
rotate evidence or create new paths to retry a consumed attempt. After successful
pinned SD SSH return, freshly validate both redundant raw environments and
compare RTC/Linux UTC before staging, jobs or further reboot.

54 focused offline guard/serial tests passed without skips. Actual configured
fragmented prompts, countdown and stopped resume, mixed valid/forbidden output,
wrong MMC/count/hash, missing/changed resume admission, capture refusal/durability
and existing guard/capture-limit checks are covered. Fixture transport replaces
physical UART/HID; these results do not establish successful physical resume.
No loader, kernel, writer, MCU, dependencies or full images changed. The diagnostic
is retired when recovery exposes supported authenticated boot selection.

## Physical continuation and capture limitation

The separately reviewed one resume completed on 2026-09-29. A fresh exact
prompt, MMC0 SC16G/SD identity, 1075-byte load and the pinned SHA were observed;
the controller sent source and returned its successful routing receipt. The
599-byte private transcript SHA is
`f6881b549fdac00a903be68c3416d734e152e07281e39ffc70fcccaf797d218f`.
A new network SSH service responds and KVM shows the recovery GUI at1024x600;
these observations do not yet establish authenticated shell admission.

The coordinator's temporary wrapper supplied a malformed 65-character supervisor
nonce. systemd-run accepted the unit launch, but its process immediately refused
the nonce. The wrapper continued routing without a surviving supervisor. That
was another coordinator preflight error, not a successful restoration result.
The capped receive-only collector was recreated manually after the controller
released UART; its active state, 4MiB file limit and Restart=no were measured.
Early Linux boot output, including this boot's regenerated SSH fingerprint,
was missed. Preserve the failed wrapper and supervisor journal; validate nonce
length and actual supervisor readiness before any future controller launch.
Do not repeat either consumed HID or resumed-UART attempt.

The offered new SSH fingerprint is intentionally not recorded as independently
verified. The existing console-fingerprint enrollment requirement remains until
trusted independent evidence or an explicit owner one-boot decision resolves it.
No signed job, claim, writer marker, environment policy or eMMC write was armed.
Both redundant environment values and RTC retention remain pending authenticated
read-only access.
