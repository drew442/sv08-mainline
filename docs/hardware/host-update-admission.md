# Atomic idle admission extension candidate

2026-09-10. Offline native and ARM64 tests; no printer connection, heat or motion.

The [Klipper extension](../../extensions/klipper/sv08_update.py) closes the race
between observing idle and stopping the printer host. Its checks and operating
limits are specified in [decision 0009](../decisions/0009-atomic-idle-admission.md).
It is not enabled in a printer configuration or an automatic update service.

## Build

The [package builder](../../scripts/package_update_admission.py) verifies the
[extension source hash and exact Klipper dependency](../../configs/apps/update-admission.json).
It creates a separate `sv08-update-admission` package owning an extra-module
symlink in the installed Klipper tree. It does not edit `upstream/`, replace core
files, rebuild MCU firmware or enable a configuration section.

```sh
python3 scripts/package_update_admission.py \
  --work build/update-admission-package-new --execute
```

Omit `--execute` for inspection. Fresh v3/v4 builds produced identical packages.
The package was installed in the isolated ARM64 test root and the tests
were repeated using its installed extension, pinned Klipper Python code and
native ARM64 greenlet runtime. Public hashes/results are in
[the evidence record](host-update-admission-20260910.json).

## Test scope

`tests/test_update_admission.py` loads the pinned real Klipper reactor, mutex and
G-code dispatcher. It substitutes only the C helper clock binding with Python's
monotonic clock to avoid any automatic source-tree helper build. Heater, MCU,
queue and printer-status objects are explicit doubles; there is no device I/O.
It verifies an actually queued G-code command attempts to run during shutdown but
cannot acquire the retained mutex. A refusal releases the mutex and leaves
command processing available. Emergency-stop handling remains callable.

The tests also cover active/paused/error state, pending idle timeout, motion,
manual-stepper exclusion, hot/stale/non-finite temperatures, commanded heat/PWM,
missing status, disconnected clients, malformed packets, stale sockets and expired
FD callbacks. Local socket requests execute through the real reactor.
`tests/test_service_admission.py` checks the host callback's ACK-before-stop
ordering, retained process-start lock, service restoration and refusal/stop errors.
Those unit-test systemd operations are doubles; the subsequent guest test below
now exercises the real service boundary.

Native tests need `python3-greenlet`; the tested workstation package is recorded
in the evidence. ARM64 tests use the already pinned Klipper venv. The final target
log is `build/update-admission-arm64-tests-v2.log`. No compiled helper or source
submodule changed during these tests.

## Integration still required

The eventual reviewed configuration will load `[sv08_update]` with its default
`/run/sv08/printer_data/comms/update.sock`; it requires virtual SD, pause/resume,
print statistics, idle timeout, toolhead and heater objects. Do not add it blindly
to an unknown hardware profile. Configurations with independent manual-stepper
queues need a separate reviewed policy.

[The host callback](../../runtime/sv08_admission.py) requires root and a shared
admission lock. On accepted quiescence, it stops Klipper and Moonraker, yields to
the updater, then restores only services it stopped after successful entry. It
never treats an HTTP idle response as permission to stop. It is suitable for
staging/package operations; trial health confirmation needs a distinct policy
that allows its required health services to run. No automatic scheduler, web API,
privileged service or package-wrapper wiring is enabled yet.

Before enabling this on hardware, connect the production transaction backend,
verify cancellation and restart behavior with real systemd/Klipper/Moonraker,
exercise process races and complete the named-profile temperature/motion checks.
The [task list](host-os-tasks.md) retains those gates. Source inspected locally on
2026-09-10: Klipper commit `f0892d82b0f1c1228454f09eb508eddde2250f4b`,
`klippy/gcode.py`, `reactor.py`, `klippy.py`, `toolhead.py`, and
`extras/{heaters,virtual_sdcard,pause_resume,print_stats,idle_timeout}.py`.


## Full ARM64 systemd/Moonraker boundary

The later `build/host-qemu-admission-v1/` run passed using the distro kernel and
real systemd and Moonraker API. The disposable Klipper-named service ran
[the fixture daemon](../../tests/fixtures/admission/klipper_service.py): the actual
pinned reactor/G-code dispatcher/extension with simulated printer/heater status.
It was not Klipper's complete hardware process and connected no MCU.

[The guest orchestrator](../../tests/host_qemu_admission.py) verified that simulated
active-print refusal preserved both service PIDs. Accepted idle admission stopped
both services; an attempted concurrent systemd start failed at the shared flock.
Both services restarted afterward, and Moonraker's real loopback API answered.
A simulated installer exception also restored services. No bundle or package was
written during this test. The public [result](host-service-admission-20260910.json)
keeps that distinction explicit.

The fixture reused the earlier disposable failure-test disk/root files, preserving
those failure logs. The disk/root files were subsequently moved to
`build/host-qemu-backend-v1/` for the integrated backend tests; admission logs
and insertion commands remain in the admission fixture directory.
Its `debugfs.cmd` records inserted files and temporary unit replacements. It
restored the production preparation deadline, used `sv08.test=admission`, disabled
network/USB passthrough and required the QEMU disk serial plus `deployable=false`.
The Klipper unit was replaced only in this disposable image; the production unit
and MCU artifacts are unchanged. `boot.log` records normal guest shutdown.

The next gate is the complete configured Klipper process and named hardware,
followed by actual update/package/mode integration and the automatic policy/UI.
