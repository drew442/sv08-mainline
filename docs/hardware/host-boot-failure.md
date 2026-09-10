# Bounded early-boot preparation failures

2026-09-10. Full Debian ARM64 QEMU checks, not physical bootloader or power-loss
validation.

`sv08-prepare.service` now has a 120-second startup deadline, 15-second stop
deadline and `FailureAction=reboot-force`. An identity, state-copy or mount failure
must return to boot selection instead of waiting indefinitely at an emergency
shell. The selected boot chain must persistently consume attempts before each
Linux trial, never replenish exhausted counters, and dispatch recovery when no
eligible attempts remain. That selection behavior has separate
[sandbox evidence](host-environment-build.md).

Two guest checks passed under `build/host-qemu-failure-v1/`:

- The real early-boot integrator was given swapped root A/B PARTUUIDs. It rejected
  the mounted-root mismatch and systemd rebooted, with filesystem teardown/sync
  visible in `boot.log`.
- A disposable copy of the unit replaced its preparation command with `sleep 30`
  and shortened only the fixture deadline to 3 seconds. Systemd reported a startup
  timeout, terminated the command and rebooted; see `timeout-boot.log`.

Both runs used the existing kernel/initramfs, a disposable copy of the six-partition
rollback disk, QEMU virt storage without network/USB passthrough, and `-no-reboot`
so the process exited at the guest reboot request. Neither ran the printer probe
or started hardware outputs. The selected target ARM64 systemd also verified the
unchanged production candidate unit. The [public evidence](host-boot-failure-20260910.json)
records log hashes and scope; the temporary shorter timeout is not shipped.

This does not handle a hung kernel, broken Boot ROM/U-Boot, failed initramfs mount
before systemd, or an unresponsive storage device that prevents reboot. Initramfs
failure already uses its panic/reboot path; hardware watchdog and real A/B/recovery
power-interruption tests remain outstanding. A board image cannot be released
until bounded boot selection, health confirmation and independent recovery are
integrated. See [remaining tasks](host-os-tasks.md).
