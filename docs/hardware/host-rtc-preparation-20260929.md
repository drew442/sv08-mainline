# H12 hardware clock preparation

2026-09-29, test-sv08-01; board revision H616_JC_6Z_V1.2 is owner-reported.
The running [SD recovery host](host-sd-recovery-host-first-boot-20260929.md)
remained USB-powered, with printer PSU off, spare installed and factory eMMC
stored. This operation updated only the H616 hardware clock. No storage,
environment, MCU, alarm, heater/motion or reboot operation was performed.

A separate high_consequence_reviewer on GPT-6 Sol/medium returned PASS WITH
CONDITIONS for one RTC_SET_TIME followed by readback. Before execution, the
coordinator verified its own NTP synchronization, pinned SSH session, deployed
helper hash and unoptimized Python invocation. Fresh intake measured sole
rtc0, character device 251:0, driver `sun6i-rtc 7000000.rtc`, sysfs path below
7000000.rtc, RTC OF compatibility `allwinner,sun50i-h616-rtc`, system compatibility
`sovol,sv08`, and kernel 6.18.51-sv08-candidate1.

Default inspection passed. The coordinator supplied fresh trusted UTC, required
Linux time agreement within ten seconds and repeated that gate immediately
before one RTC_SET_TIME (standard Linux rtc_time ABI). RTC_READ_TIME matched
within three seconds. Fresh Linux and RTC comparison showed 2026-09-29
06:52:22 UTC, replacing the previously measured January 1970 RTC date. No
retry or rollback occurred. The helper includes no alarm or reboot command.

This proves only this clock write and readback. It does not establish battery
backing, cold-power persistence or warm-reboot retention. The later separately
reviewed boot must recheck clock agreement before any time-limited writer job
or claim. If retention fails, leave claims disabled and investigate rather
than weakening signed-job validity checks.

Private evidence under `local/sd-recovery-host/`, SHA-256:

- `set-reviewed-rtc.py`: `d9b14d3d03f2589f03e37bc027278405a63c8fa4c47babe55f597da648f97a6d`.
- `rtc-review.json`: `3ef46d5b381d6b248326c00feb157828e90ecf425b21800baf26b50e9839702c`.
- `rtc-coordinator-time-intake.txt`: `6d5bae84af6d67a689fe976c01ae08ae815c3d54420c6bf8239c3b0560473c0d`.
- `rtc-fresh-intake.txt`: `fec1274e08bbeb7cdd73b2369f5f3671835630957e33019da36d3f03acba35a4`.
- `rtc-deployed-helper-sha.txt`: `d7b69adbbb4001cfba3759d353d9934a1630c967c36442b9bb64c4b13c64a8d8`.
- `rtc-inspect.json`: `9fd2631afea6ffc92801bda6b83a46191d8fc38ed61bc7b3f3093fa7d02194f4`.
- `rtc-execute.json`: `b318d05b0d33a2735bf3ac870baea27104f129602882e95276e4870ed11ea29e`.
- `rtc-after-clock-comparison.txt`: `8b41b52d3f1248dc3c52d35a29f454762bee4537d7a5e1ff5d261042ac23e8de`.

The one-off helper and complete intake remain local. Its purpose is this
commissioning clock correction; supported host time synchronization/RTC tooling
should own routine updates in a released image. The review is not hardware
authority; the owner's existing host-preparation authorization covered this step.
