# Guard one remote recovery reboot

2026-09-29. Bounded correction under the owner's existing writerless-eMMC goal;
optional new features remain paused. The prior coordinator passed a failed UART
readiness check and original recovery now provides neither SSH nor a console.
See the measured failed probe in the requirements below.

Permit exactly one reviewed emitted keyboard sequence with current redundant environment
counters unknown. This replaces the fresh pre-reboot environment read requirement
only for this recovery attempt, because original recovery has no command access.
Do not assume A=2, preserved environments, retained RTC, or new-loader SD routing.
Jobs/claims/markers remain disabled. Missed interception, script reset or failed
return stops; no automatic second attempt. Read both environments and compare
Linux/RTC time immediately after SD SSH returns, before any staging or reboot.
This procedural exception requires delegated approval and a separate exact-operation
Sol/high review. No hardware action follows solely from feature approval.

Keep the already reviewed serial commands, script, hashes and capture behavior.
Add only an optional readiness callback after serial identity, competing-descriptor
checks and TIOCEXCL, before the existing countdown wait. Callback failure must
close/release resources and transmit nothing. A bounded coordinator guard uses
that callback to report actual PID, UART identity and owned private capture
file descriptor; it waits for one exact acknowledgment or stops. The coordinator
must receive live readiness over its child channel, verify bindings and live
process, and abort before HID if any check fails. No fuser-only readiness claim.
The guard defaults to inspection. It performs no device writes except the fixed
keyboard reports after explicit --apply and exact-operation review.

Use the existing root SSH connections from the coordinator, with pinned host
keys, to launch the identified Beelink controller and send exactly one fixed
KVM keyboard sequence: Ctrl-Alt-F2, release, Ctrl-Alt-Delete, release. Validate
/dev/hidg0 against the KVM Keyboard gadget metadata and measured char identity.
No arbitrary commands, key text, power/control-line operations, explicit force-reboot command,
retry, shell interpolation or changes to authentication. Verify the exact pinned
recovery Ctrl-Alt-Del mapping first; physical response remains an observation.

After controller exit, recreate the bounded receive-only transient collector;
starting a stopped/removed transient unit is insufficient. On refusal/timeout/
abnormal exit, preserve outputs and restore receive-only capture, with no further
HID or reboot. Exercise actual guard/collector recreation with fake subprocess
and HID descriptors for failed readiness, dead process, malformed/stale identity,
callback/ack failure, partial HID writes, successful ordering and abnormal exit.
Reuse the accepted loader/serial/writer tests outside changed readiness behavior.

One implementer owns scripts/sv08_recovery_boot_guard.py,
scripts/sv08_serial_boot_route.py (optional readiness hook only),
tests/test_sv08_recovery_boot_guard.py, tests/test_sv08_serial_boot_route.py
(focused callback tests), and docs/hardware/host-recovery-reboot-guard.md.
No upstream/build/MCU/writer changes, private credentials, policy rearming or
physical operation. Keep scripts/receipts/captures below 64 MiB and isolated
scratch below 512 MiB. Independent delivery verification precedes physical review.
Retire this diagnostic guard once supported recovery exposes authenticated reboot
and boot selection. No release or printer commissioning claim.

## Explicit CAD risk amendment

The exact systemd 257.13 recovery image disables the kernel's direct CAD path
and maps an ordinary SIGINT to the orderly reboot target. Its standard final
SuccessAction=reboot-force follows shutdown/umount/final targets. However the
unmodified CtrlAltDelBurstAction default can perform an early forced reset after
more than seven CAD events within two seconds. Mutable host repeat settings and
a delayed or failed release mean four HID reports do not prove one host event.
Do not claim the absence of that force path, a guaranteed release deadline, or
exactly one observed reboot. A new image override cannot be installed through the
currently inaccessible host.

The bounded proposal explicitly accepts that existing burst/stuck-release risk
for this one recovery sequence, subject to independent approval and immediate
Sol/high operation review. The identified installed medium is the spare; the
factory module is stored, independent recovery is retained, PSU remains off,
printer services are disabled, and no writer job/claim/marker or incomplete
whole-device transfer exists. Original recovery is designed for read-only media;
normal-slot persistent writes and boot-attempt effects after a missed interception
must remain possible rather than claimed absent. A forced reset could interrupt
those writes. Existing owner authorization accepts the spare/recovery path;
feature approval still grants no hardware authority.

The sender checks fresh gadget identity, uses four fixed reports with prompt
release, records each syscall/elapsed result, and never sends a repeated press,
force fallback or second sequence. Release failure stops and is an uncertain
outcome requiring separately reviewed recovery. An unexpected reset or missed
SD return also stops; current environment/RTC readings are mandatory after any
successful return. Offline guard tests establish sender behavior only. They do
not certify host key-repeat timing, hardware response or forced-reset absence.
