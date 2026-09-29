# Guard one remote recovery reboot

2026-09-29. Bounded correction under the owner's existing writerless-eMMC goal;
optional new features remain paused. The prior coordinator passed a failed UART
readiness check and original recovery now provides neither SSH nor a console.
See the measured failed probe in the requirements below.

Permit exactly one reviewed recovery reboot with current redundant environment
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
No arbitrary commands, key text, power/control-line operations, force reboot,
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
