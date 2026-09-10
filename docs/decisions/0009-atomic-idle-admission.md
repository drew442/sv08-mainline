# 0009: Atomic idle admission inside Klipper

Date: 2026-09-10. Status: offline-tested extension candidate; not enabled on hardware.

An HTTP idle check followed by stopping Klipper has a race: a new print can start
between those operations. Use a separately packaged Klipper extension with a local
Unix sequenced-packet socket. The extension acquires the public G-code mutex,
checks the configured idle timeout, print/pause state, motion queue and every
configured heater, acknowledges admission, then keeps the mutex held through the
normal `request_restart('exit')` shutdown path. The host updater must wait for
service exit before writing. No queued G-code can pass between admission and exit.

Refuse an occupied mutex immediately, rather than waiting behind a long-running
command. Reject missing status providers, active/paused/error print state,
unelapsed idle timeout, queued motion, independent manual-stepper queues, heat
targets/PWM, stale or non-finite temperatures and temperatures above 50 °C. The
configuration may lower that temperature ceiling, never raise it. Klipper's stale
reading sentinel is zero, so zero or negative readings also refuse automatic
admission. This is a conservative update policy, not thermistor calibration or a
replacement for heater protection. Existing configured heater protections remain.

The socket is owner-only under `/run`. Incomplete clients time out without taking
a command lock; malformed requests and disappeared clients do not authorize a
stop. A stale owned socket may be replaced, but regular files, foreign sockets
and active listeners are preserved. The root-side admission callback holds the
same flock used by service-start checks, accepts only an affirmative extension
response, waits for services to stop and retains the barrier through the write
operation. It restores previously active services after the operation. A failed
or unresolved stop surfaces an error without enqueueing a competing restart.

This extension uses supported module loading and existing public Python entry
points, not a modified G-code dispatcher or a source-tree patch. Its package
requires the exact reviewed Klipper package; the host/MCU commit remains unchanged.
No module configuration or service activation ships in the package. Retire the
extension when upstream Klipper provides equivalent atomic idle-and-exit admission,
retaining the queued-command failure tests as acceptance evidence.

[Build and test evidence](../hardware/host-update-admission.md) distinguishes real
pinned reactor/dispatcher execution from simulated hardware statuses. Production
update scheduling, ownership/authentication UI, health confirmation and physical
validation remain open. Confirmation needs its own admission/health policy; the
service-stopping callback is for staging/package work, not an assumption that a
running application's health can be checked while it is stopped.
