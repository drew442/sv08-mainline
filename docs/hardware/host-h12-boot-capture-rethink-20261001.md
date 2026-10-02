# H12 boot capture: separate monitoring from host startup

2026-10-01. Original SV08, test-sv08-01, owner-reported H616_JC_6Z_V1.2.
This research responds to the owner's request to rethink H12, use practical
bounded experiments and temporarily use GPT-6 Astra/high until H12 is resolved.
Printer function is unnecessary during host-image development. Temporary use of
headers/ports and additional USB-TTL hardware is permitted; soldering is a last
resort. This is not physical qualification of a new wiring or reset procedure.

## Problem and direction

The owner reports that connecting the onboard USB-serial port supplies host power.
The H616 can start emitting before USB enumeration and terminal opening finish.
A faster terminal or reconnect loop cannot recover bytes already lost. The
solution is to have a receiver active before the event being observed.

Two approaches directly address that ordering:

1. Keep the onboard USB bridge connected and recording, then reset the H616 in
   software. The [first urh-04 attempt](host-h12-urh04-first-boot-20261001.md)
   already captured SPL, main U-Boot and Linux after an ordered SSH reboot, so
   this works in at least that measured software state. Current recovery lacks
   SSH; identify another existing software control before building more guard
   infrastructure.
2. Power an external USB-TTL receiver independently from Beelink and attach it
   to the existing H616 console TX and common ground. Start capture before
   applying host power. This can cover cold boot without depending on the
   onboard bridge's enumeration. Exact accessible signal point and voltage need
   identification on the installed board.

## Practical first diagnostic

Retained `build/host-kernel-61851-v1/output/.config` enables
CONFIG_SERIAL_8250_CONSOLE, CONFIG_MAGIC_SYSRQ, CONFIG_MAGIC_SYSRQ_SERIAL and
CONFIG_SUNXI_WATCHDOG. MAGIC_SYSRQ_DEFAULT_ENABLE is 0x1, but that does not
establish the live sysctl policy. Linux documents serial BREAK followed within
five seconds by a command; `h` prints help. Therefore one BREAK plus `h`, with
capture active, is a useful non-rebooting trial for current kernel control.
A positive help response establishes live serial SysRq handling, not permission
for every SysRq operation or proof of successful reset. A later reset is a
separate reviewed experiment; SysRq `b` resets immediately without syncing, so
it must not be sent casually as the discovery probe.

A separate Sol/high reviewer admitted one help-only diagnostic with conditions.
The coordinator verified the current collector identity/source/sole descriptor,
limits, private script hash and recovery path, then ran one bounded probe.
BREAK returned after approximately 258 ms; `h` was sent about 2.7 ms later.
The five-second receive window produced **zero bytes**. This is inconclusive:
it does not establish whether the live policy, target liveness, BREAK delivery
or serial receive path prevented a response. No reset command or repeated probe
followed. Raw response and operation receipts are retained.

Receive-only collection was independently verified restored with a new PID,
matching pinned source/cmdline, a new ready event, sole O_RDONLY UART descriptor,
12-hour runtime, 4 MiB per-file cap, Restart=no and private umask. Original log
inodes/content were preserved. Opening the port and driver BREAK handling can
change modem lines/configuration; no claim of zero electrical side effects is
made. No explicit DTR/RTS or target-power operation was issued.

## Warm capture physically demonstrated

A separate Astra/high action review admitted a revised, fixed keyboard trial
under the latest direct owner instruction and standing same-spare recovery
scope. The September 29 disabled-marker condition applied to its named guard
exception; this experiment does not reuse that guard or assert marker absence.
The earlier Sol/high FAIL and its candidate remain preserved. Its concrete
nonblocking HID release defect was corrected with blocking writes; possible
held-key/forced reset and incidental boot writes remain acknowledged.

The coordinator kept the existing receive-only serial collector open, switched
to VT2 with Ctrl-Alt-F2/release, waited one second, and sent Ctrl-Alt-Delete/release
once through the existing KVM keyboard. The remote sender had a 13-second TERM
plus 2-second KILL bound. All four eight-byte reports were accepted and the
sender exited zero in about 1.65 seconds. More importantly, the target recording
shows `Received SIGINT`, activation of `reboot.target`, orderly shutdown and
`reboot: Restarting system`, followed by:

- `U-Boot SPL 2026.07 (Sep 13 2026 - 00:00:00 +0000)`;
- initial DRAM diagnostics and main U-Boot reporting 1 GiB;
- main `U-Boot 2026.07`, H616 identity and the full three-second autoboot countdown;
- two bad-CRC/default SD environment messages, the 1250-byte wrapper and preserved
  720-byte original recovery script;
- Linux `6.18.51-sv08-candidate1` and original recovery startup.

**The early warm-boot capture problem is solved for this measured state.** The
USB cable stayed connected, the receiver stayed open, and no extra hardware,
power cycle, soldering or printer operation was needed. The next H12 operation
can use this observed warm-reset path with a prepared serial controller to stop
at U-Boot and return to the known SD system. That interception/return was not part
of this capture-only trial; its later measured result follows below.

This does not establish cold-start-only fault capture, reliable reset from a
hung kernel, DRAM reliability or urh-04 preflight acceptance. No preflight FIT
entry or `PREFLIGHT_PASS` occurred. Current raw environments/marker/RTC still
need reconciliation after an authenticated SD return. The old guard proposal
remains unapproved; capture success does not approve or require its implementation.

The 115-second observation retained **72,158 new console bytes**, with received
events from 04:50:10 through 04:51:25 UTC. Exactly one SPL banner was observed;
original recovery reached its target and reported startup complete. No collector
port error appeared. A separate postcheck found the same PID64017/starttime and
sole O_RDONLY descriptor, intact log inodes and active original caps.

Raw capture SHA-256:
`5a2c53575437e311ae95487a59d9f7c1e82cbdf39fd7a8e687235b5d87e728d3`.
Event slice SHA-256:
`3e43179cf2918ea7dfdc702ea5fee26a4731837d521655d35a7588e6f70d77c0`.
Keyboard receipt SHA-256:
`b26b4ab3148ac2758ddc487f5ccf9c168fbe811ace838d75470acbca26688b16`.
Revised action review SHA-256:
`08e35cc528c204b8e40434f24bbde072f1f51cff0cbceae40fc8b2e581c6d554`.
These are private evidence under the scratch directory below, not committed logs.

The first coordinator admission stopped before any HID because its termios
comparison omitted baud bits in `c_cflag`. That comparison was corrected against
the independently observed attributes; the refused admission and original
script were preserved. This was not a second keyboard attempt. The actual
keyboard attempt has one canonical exclusive receipt.

## SD return physically demonstrated

A later independently reviewed operation kept USB connected, prepared the sole
serial controller, and sent one fixed keyboard reboot sequence. The controller
intercepted the positive U-Boot countdown, verified the stopped prompt, selected
SD MMC device 0, loaded the 1075-byte `boot.scr`, checked SHA-256
`ce18bf74e3d8ae840bfb90129ba28515ba89cbd2759bc32ecd0418f6987d1ddd`,
and sourced that script. The recording contains one SPL banner and SD Linux
startup. Its 80,694 bytes have SHA-256
`2bbcf2a8842cc967fd9ac88e1a9fdcc4110e4729a9e96a7a7cc8d03a388676eb`.

Authenticated SSH subsequently identifies `sv08-sd-recovery-test`, Linux
`6.18.51-sv08-candidate1`, boot ID
`5ec209ff-5f02-4596-b393-519a43154893`, and SD root PARTUUID
`deaf981d-7441-428c-bf43-ce40bca6ca65`, mounted `ro,norecovery`.
No failed systemd units were reported. An independent Beelink postcheck found
the operation controller inactive with success and the restored passive
collector active, PID 66942, with the sole O_RDONLY serial descriptor and
unchanged pinned source. Submission of a restoration service alone was not
counted as restoration evidence.

Fresh read-only intake identifies the same 31,272,730,624-byte spare on controller
`4022000.mmc`, now `/dev/mmcblk0` rather than its earlier Linux node. Both raw
environment records have valid CRCs and flags 5/4; both contain `BOOT_ORDER=A B`,
zero A/B counters and expired job `8bd9a5860bc40abf37f14e5011544d18`.
Linux and the RTC were inventoried; raw environment beforeimages are retained
outside target tmpfs. This is SD recovery success, not physical urh-04 acceptance.

A separately reviewed read-only p5 inspection subsequently matched the recorded
1250-byte wrapper, 720-byte original recovery script and 48,902,416-byte FIT.
The 18-byte `SV08-REIMAGE-ONCE` marker remains present. The staged directory
contains exactly the marker, original script and FIT. Available p5 space is
105,455,616 bytes. The private mount was unmounted, its scratch directory removed,
and PID1's global mount table was unchanged. Receipt SHA-256:
`3893fa185e205c42e93efb7b3f10a59b29c3af876c9de453b3240b753738914a`.
Linux and the RTC differed by less than two seconds at intake. Fresh signed
preflight preparation and artifact verification subsequently passed on Beelink
with the accepted selector repair; no listener, target staging or boot was
performed by that build. Physical preflight remains unpassed.

An earlier controller attempt refused before arm, HID or serial transmission
because `systemctl show` omitted empty command arrays. Its capture was empty;
the controller was stopped and passive capture restoration independently
verified. The corrected, separately reviewed attempt used typed D-Bus properties
to verify the exact service commands and empty auxiliary arrays. Both attempts
and reviews remain preserved; no receipt or failed candidate was reused.

Private evidence is under
`local/feature-workflow/probes/h12-sd-return-20261001b/`: the complete capture and
event receipts, strict SSH enrollment under the owner's address-based trust,
`sd-state.json` and `postcheck-collector.json`. Their respective SHA-256 values
are `0c9fde1f1bb818063961f57976d7f5d1d9bf368fd5d79f03e7b746df3eb4a8b3`
and `08bd51302ce3cbeafec265882fab2e0901f64085cb0f6fd589e68cb3d3e944df`.

## Cold-boot receiver experiment

After signal identity and electrical levels are established, the first wiring
trial uses only adapter RX to host TX and adapter ground to board ground. Leave
adapter TX, VCC, RTS and DTR disconnected. The onboard bridge can remain the
host power source; the external receiver must already be enumerated and recording
before that host-power connection. Use the known console rate, 115200 8N1.
Check that the chosen adapter does not feed the unpowered board through its RX
input; a voltage-selector label alone does not establish the adapter's signal
levels or leakage. If a receive-only connection back-powers the board, use an
appropriate buffered/isolated receiver rather than accepting ambiguous startup.

Observe from the first emitted SPL bytes through U-Boot and kernel. Absence of
Boot ROM text is not a capture failure; this is a test of available console output.
Retain a continuous timestamped raw recording. Capture alone can succeed without
printer services, motors, heaters or a functional printing configuration.

Only after capture works should bidirectional control be considered. An external
TX output must not be tied to an onboard bridge TX output driving the same H616
RX net. Use one transmitter, or positively isolate the other. Clips or an existing
verified connector are preferred before soldering.

## What the documents actually establish

Sovol's `MCU_PIN_definition.pdf`, page 1 (printed manual page 23), labels UART0,
UART3 and the USB-to-UART Type-C connection. Closer visual inspection associates
the UART0 arrow with the Type-C port; it does not provide a verified separate
TTL-header pin order. The pictured board is marked V1.1; the published MCU
schematic filename says V1.2, and the installed V1.2 remains owner-reported.
Do not transfer a header pinout from SV08 Max, Zero or a BTT CB1.

The EXP2 RESET label is the STM32 NRST net in
`H616_JC_6Z_V1_2_MCU.pdf`, page 1, U14 pin 14. It is not evidence of an H616
reset connection. No confirmed accessible H616 reset pad/button or complete
host/USB-bridge power schematic was found in these two published documents.

H616 UART0 uses PH0/PH1 in the selected software/pin mux; an SoC pin assignment
does not locate a connector or accessible PCB pad. Other UARTs need bootloader
and kernel console routing changes; simply enabling a Linux overlay will not
recover the current SPL output. USB gadget console starts too late for SPL.
FEL is a boot/recovery transport, not a transparent stream of normal boot logs.
A VBUS blocker alone does not solve the problem if bridge and host both lose
power. Do not short an unidentified reset/PMIC or power net.

## Sources and execution record

Primary documents accessed 2026-10-01:

- [Sovol connector drawing](https://github.com/Sovol3d/SV08/blob/a60644875f8c756d20b3828c9416518b414b5491/Motherboard/MCU_PIN_definition.pdf), page 1,
  SHA-256 `8b1f418b4f264442274be6a45abfbcba5c09b7445a168294ca7d730f4a0d18fa`.
- [Sovol MCU schematic](https://github.com/Sovol3d/SV08/blob/a60644875f8c756d20b3828c9416518b414b5491/Motherboard/H616_JC_6Z_V1_2_MCU.pdf), page 1,
  SHA-256 `5d6afc6560feca7bef237e468778e1ff00d6d7c5ee9f22ce5a4c712f76f0a023`.
- [Linux serial SysRq documentation](https://docs.kernel.org/admin-guide/sysrq.html),
  serial BREAK protocol and help/sync/remount/reboot semantics; retained selected
  kernel source/configuration supplies the build-specific checks.
- [linux-sunxi UART development guide](https://linux-sunxi.org/UART),
  voltage, separate power, leakage and console limitations.
- [Allwinner H616 datasheet revision 1.0](https://linux-sunxi.org/images/b/b9/H616_Datasheet_V1.0_cleaned.pdf),
  GPIO multiplex functions, PH0/PH1 UART0; not an SV08 wiring diagram.
- [Allwinner H616 full datasheet](https://mangopi.org/_media/h616_datasheet_v1.0.pdf),
  revision 1.0, pages 23–24, 27 and 29: UART0 supply domain/mux and active-low
  RESET ball A16. No accessible SV08 reset point follows from the BGA pinout.
- [TF-A H616 native reset implementation](https://github.com/ARM-software/arm-trusted-firmware/blob/c2a0e7080d64d69940be4ad0ff6578501f3cbf9e/plat/allwinner/common/sunxi_native_pm.c#L54),
  watchdog-based system reset consistent with the observed warm boot, without
  claiming this capture identifies the handler used.
- [U-Boot Allwinner documentation](https://docs.u-boot-project.org/en/latest/board/allwinner/sunxi.html),
  FEL transport and boot behavior.

A native Astra launch hit the existing thread limit. Under the owner's explicit
temporary model authorization, the coordinator launched a separate supported
CLI session with per-run GPT-6 Astra/high and disabled child delegation. Its completed recommendation is an independent
receiver on the same UART0 TX net for lasting cold capture, with one ordinary
keyboard warm-reboot trial as the cheapest immediate route. Actual
runtime model/effort/full-access/never were observed. Project and user-global model
configuration were not edited. The help diagnostic used a separate Sol/high action reviewer. The revised
keyboard trial used a fresh independent Astra/high session under the explicit
temporary-model authority, carrying the same high-consequence review contract.
Both actual runtime settings were observed; the researcher did not approve its
own experiment.

Read-only Beelink inspection found the existing bounded collector active with
PID 55270; its source hash matched, console was 230456 bytes and event log
733928 bytes. The retained tail ends in original recovery/systemd output. This
is observation of the collector and retained log, not proof of current H616
liveness. No port reopen, serial transmission or reset was performed by that
inspection. Private research, runtime, probe/review and operation evidence remain
under ignored `local/feature-workflow/probes/h12-boot-capture-rethink-20261001/`.

## Corrected preflight entered RAM but did not pass

Measured 2026-10-01, same unchanged host-only setup and named spare on
`4022000.mmc`, CID SHA-256
`08d24eb0a58bc7288c07020a0432586ea6070b78abdd86b209de362c7b42fe8a`.
No new board-revision claim follows from the diagnostic model strings.

Fresh job B (`db4be670b7973f394d4d7b7309e3adc1`) was staged and independently
read back. Separately reviewed deletion removed only the expired job key from
both CRC-valid environment dictionaries; every other field survived. The exact
pinned ARM tool was first reproduced on a disposable regular file: its script
requires `sv08_reimage_arm=` followed by a newline, with two planned stores for
both copies. A key-only line is ignored. The original candidates and failed
probes are preserved. This agrees with upstream
[libubootenv v0.3.5 load-file semantics](https://raw.githubusercontent.com/sbabic/libubootenv/v0.3.5/src/uboot_env.c),
lines 1555–1602 and 1765–1796, accessed 2026-10-01; the exact local executable
experiment, rather than a version assumption, established the tool behavior.

B remained unarmed when its usable signed window ended during review. Its
complete artifact remains durably on Beelink; it was not extended or rearmed.
A distinct fresh job C (`2aadb588e986f7abff61542b06e80dbd`, expiry 12:12:54 UTC)
was built, signed and independently verified, with the accepted selector repair.
Its FIT is 48,902,464 bytes, SHA-256
`b5f527cbb3ee302e106316b5a41790b13db6311a8b106482f4b72fb8fdb1edb2`;
its 2,085-byte selector SHA-256 is
`f1eac4024dc3b24f56af17744f42669b73aebd857b264e4e49447cd6e43caf2f`.

Separate-session Astra/high review under the owner's temporary exception
conditionally accepted the exact stage, arm, activation, claim and boot
operations. A prior listener adaptation was rejected for a wrong source prefix;
its original and rejection remain, and C corrected the prefix before review.
The coordinator recorded actual runtime and all conditions before acting.
Staging restored the known original durably before removing only B's two staged
files; B's off-host artifact and the older four-file failed-attempt archive were
preserved. Independent readbacks accepted C's unarmed chain, then both armed
CRC-valid full dictionaries, then the exact marker and unchanged environment
bytes. An initial RAM receiver refused before creating files; explicit buffer
release fixed its memory retention while keeping the memory gate.

One normal SSH reboot was accepted at 11:32:06 UTC after actual listener
PID/starttime/socket, unused claim, exact read-only NFS client exports, passive
UART ownership and current target/loader/source checks. Serial capture shows
the new preflight FIT and trusted RAM kernel, then
`SV08_H616_COMMISSIONING_REFUSED_OR_UNCERTAIN_CLAIM`. The server still contained
only `.lock` and `armed.json`. The runtime path passed marker consumption and
unmount before attempting automatic return; raw p5 state awaits SD reconciliation.
Its next SPL boot failed DRAM size-row training with
`### ERROR ### Please RESET the board ###`. No repeated reboot was issued.
The listener was stopped with the unused state preserved.

Snapshot: 61,089 captured bytes after the admitted offset, SHA-256
`e385ded12a85ab68e1320c384ba9884bffe5cd98f3d63bdf8a5101701bdd3a67`.
Private source/artifact/review/runtime/action/readback/capture records remain
under ignored `local/feature-workflow/probes/h12-sd-return-20261001b/`, chiefly
`fresh-preflight/fresh-job-c/`. This demonstrates corrected selector delivery
and preflight entry, not `PREFLIGHT_PASS`, an authenticated claim, successful
automatic recovery return or a full-image write.

Source investigation is checking early nonblocking randomness failure before
any connection; the current capture lacks a CRNG-initialized message, which is
a clue rather than proof of `getrandom()` errno. Physical reset is now a real
dependency: the measured Beelink USB2 root hub reports no power switching,
and Linux keyboard/SysRq cannot reset a host halted in SPL. A concrete bounded
USB-replug/SD-return receiver is being prepared for independent review; no
unidentified reset net or forced USB power operation is proposed.

## Startup repair accepted; physical reset still pending

At 12:22 UTC, the reviewed cold-return receiver timed out without observing a
USB disconnect and captured zero bytes. No SD return occurred. Independent
read-only postcheck passed for the restored passive collector: unit
`sv08-recovery-capture-h12coldsd20261001c`, PID 75865/starttime 28158057,
sole UART fd 3 opened read-only, pinned source and original log inodes preserved.
Private receipts and postcheck are in `cold-sd-return-preparation/` beneath
the existing ignored probe directory. The 11:53 request is expired; a physical
reset needs a fresh independently ready receiver window.

The [claim-startup repair](../development/h616-claim-startup-readiness-20261001.md)
passed fresh independent delivery verification on clean commit
`0708a18a2528929ad9a59c22e32d865003e95ed2` and is integrated locally. Actual
reviewer session `01a0f764-e807-7f13-afe8-eea7d9b24487` ran GPT-6 Astra/high
under the owner's temporary H12 exception; this is not a Sol review. The
coordinator observed actual runtime settings. Verification independently
reproduced all 42 startup scenarios, the signed purpose check, focused receipt
checks, unchanged service expiry and four before/after ARM64 binary hashes.
The [feature record](../features/h616-claim-startup-readiness/record.json) is done
for offline delivery. Earlier failed fixtures and physical job C remain retained.
No new physical candidate was built, no old job was rearmed, and H12 preflight,
automatic return, full-image write and hardware qualification remain unpassed.

## Cold-capture work closed as a limitation — 2026-10-02

The owner instructed us to use reasonable workarounds and stop cold-capture work.
Complete initial cold-boot serial output is not a prerequisite for preflight,
installation, commissioning or later boot-outcome testing. Onboard USB enumeration
can miss the first bytes; warm reboot capture is physically demonstrated. Use
warm reboot when Linux runs, coordinated human restart or existing SD/media rescue
when it does not, and HDMI/SSH/later serial observations for diagnosis. No further
external-UART, alternate-interface, soldering or capture-framework work is assigned.
This does not establish cold-start reliability or pass any physical preflight.

D's fresh receiver stopped on October 1 at 14:07:33 UTC after 30 minutes without
an observed USB disconnect, with zero captured bytes. At October 2 00:19 UTC,
the controller was inactive and a separate read-only check verified restored
passive capture: PID 79976/starttime 28788664, sole O_RDONLY UART fd 3, pinned
source, original log inodes and the existing runtime/file limits. Beelink could
not reach printer SSH (no route to host); current SD control remains unproven.
The expired physical request is closed. Regaining control is a practical recovery
dependency, separate from solving cold capture. Private terminal and postcheck
receipts remain beside D's original source/review evidence.
