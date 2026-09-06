# Test printer 01: mainboard SWD connection attempt

Date: 2026-09-06. Status: programmer detected; MCU connection unsuccessful.
The owner reports the printer is now powered down and ST-Link USB is connected
to a separate workstation. This resolves the earlier powered-printer arrangement
in the [intake record](test-sv08-01-backup-and-stlink.md). Physical four-wire
continuity, board revision and target voltage remain unverified.

## Tool and connection evidence

The workstation runs Ubuntu 24.04.4 LTS amd64. Installed the repository package
`stlink-tools=1.8.0-1build2`; package/tool hashes and installation output remain
private. The programmer enumerates as USB `0483:3748` and reports firmware
`V2J37S7`. This establishes communication with the programmer, not the target.

Two correctly parsed probe attempts were made, in sequence:

```sh
sudo -n st-info --probe --hot-plug --freq=100
sudo -n st-info --probe --hot-plug --freq=50
```

Both reported `Failed to enter SWD mode` and an unknown target. The printed zero
chip ID, flash size and SRAM size are failure values; they are not measurements
of a zero-capacity MCU or evidence of readout protection. Target identity,
protection state and flash range remain unknown. No firmware dump was attempted.

The flags request hot-plug attachment without an explicit reset. No erase,
unlock, option-byte modification, firmware write or explicit reset command was
issued. Debug connection attempts are maintenance operations, not passive USB
inventory, even when no flash write is requested.

The first invocation put options before `--probe` and was rejected by this
version's argument parser. The corrected syntax above is the relevant target
connection attempt. An unprivileged help invocation also lacked USB permission;
both actual probe attempts used sudo, so that permission error does not explain
their SWD failure.

## Physical checks before another attempt

1. Keep printer supply power off. Unplug the programmer USB before touching or
   reseating wires; then confirm **3.3V to 3V3, GND to G, SWDIO to IO, SWCLK to CK**
   against the actual programmer and board labels. Do not rely on cable colours
   or connector orientation from memory. The 3.3 V lead still needs confirmation.
2. With the wiring fixed and programmer USB connected to the separate computer,
   note any mainboard power indication. If a meter is available, measure 3V3
   relative to G at the board header without bridging adjacent pins. Record the
   actual voltage; a programmer LED alone does not show target power is present.
3. Report the result before retrying SWD. If wiring and power check out, investigate
   reset access and MCU markings. The four-pin mapping has no NRST connection;
   do not blindly switch to connect-under-reset or assume protection is the cause.

The mainboard vendor artifact candidate contains
`CONFIG_STM32F103GD_DISABLE_SWD 0` in its ELF debug macros. This is supporting
build evidence, not proof of the installed program or live debug-pin state.
It does not eliminate wiring, power, reset or other target-access issues.

Private logs are under `local/test-sv08-01/mainboard-swd-20260906/`; no MCU backup
binary exists from these attempts. The [sanitized observation](../../profiles/test-sv08-01/observations/2026-09-06-mainboard-swd-attempt.json)
records scope and unknowns. Once connection succeeds, read identity/protection
before choosing the full flash range, and stop if obtaining a read requires erase.

## Sources

- [Sovol four-wire connection procedure](https://wiki.sovol3d.com/en/How-to-burn-firmware-to-the-motherboard-adapter-board),
  accessed 2026-09-06; no revision shown. It requires printer power off and a
  separate computer for programmer USB.
- [st-info v1.8.0 source](https://github.com/stlink-org/stlink/blob/v1.8.0/src/st-info/info.c),
  accessed 2026-09-06: probe syntax and target information path.
- [st-flash v1.8.0 source](https://github.com/stlink-org/stlink/blob/v1.8.0/src/st-flash/flash.c),
  accessed 2026-09-06: future read commands also halt the core; a flash read should
  not be described as having no effect on MCU execution. No such command was run.
- [Existing artifact evidence](test-sv08-01-firmware.md), pinned vendor ELF debug
  macros inspected 2026-09-06; physical board revision remains unknown.
