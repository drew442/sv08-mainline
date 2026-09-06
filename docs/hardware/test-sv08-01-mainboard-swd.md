# Test printer 01: mainboard SWD backup

Date: 2026-09-06. Status: full mainboard flash and option bytes captured twice;
matching reads verified. Restoration remains untested.
The owner reports the printer is now powered down and ST-Link USB is connected
to a separate workstation. This resolves the earlier powered-printer arrangement
in the [intake record](test-sv08-01-backup-and-stlink.md). The owner subsequently confirmed the pinout, mainboard power LED and removal
of the USB extension. Board revision and physical MCU markings remain unknown.

## Initial attempts (before owner wiring confirmation)

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

## Successful retry and method review

After the owner's confirmation, st-info still returned zero chip ID/capacity,
although it no longer printed the earlier SWD-entry error. Installed workstation
package `openocd=0.12.0-1build2` and reviewed its ST-Link and STM32F1 scripts.
Both OpenOCD drivers explicitly support **ST-Link/V2**; this was not a V3 setup.

| Method | Result |
| --- | --- |
| HLA ST-Link, `hla_swd`, 100 kHz | Programmer detected; target examination failed |
| Native ST-Link, `dapdirect_swd`, 50 kHz | `STLINK_SWD_DP_FAULT` during attachment |
| Native ST-Link, 5 kHz | Cortex-M3 examination succeeded |
| Native ST-Link, 950 kHz | Examination, identity reads and complete captures succeeded |

The sequence establishes a working method, not the cause of the earlier failure:
speed, driver and prior connection state changed. OpenOCD reported approximately
3.214–3.217 V through the programmer. This is adapter telemetry, not an independent
meter measurement at the MCU supply.

The successful setup was:

```sh
sudo -n openocd \
  -c 'gdb_port disabled; tcl_port disabled; telnet_port disabled' \
  -f interface/stlink-dap.cfg -c 'transport select dapdirect_swd' \
  -f target/stm32f1x.cfg \
  -c 'adapter speed 950; reset_config none; stm32f1x.cpu configure -event examine-end {}; init; echo [read_memory 0xE0042000 32 1]; shutdown'
```

No explicit reset/halt, erase, unlock, programming or option-byte write command
was issued. The default STM32F1 examine-end register-writing hook was disabled.
OpenOCD still initializes core debug registers and breakpoint/watchpoint state;
this was maintenance debug attachment, not a passive observation. Reset release
messages in its log do not establish a commanded target reset.

## Readback evidence

Target role is the owner-connected mainboard; PCB revision and exact package
marking remain unknown.

| Field | Read result |
| --- | --- |
| SWD DPIDR | `0x1ba01477` |
| Core | Cortex-M3 r1p1, CPUID `0x411fc231` |
| DBGMCU_IDCODE | `0x10036414` |
| Factory flash-size halfword at `0x1ffff7e0` | `0x0200`: 512 KiB |
| FLASH_OBR | `0x03fffffc`: RDPRT and OPTERR clear |
| RDP option halfword | `0x5aa5`: unprotected value and complement |
| FLASH_WRPR | `0xffffffff` |
| Flash range | `0x08000000` through `0x0807ffff`, 524,288 bytes |
| Option range | `0x1ffff800` through `0x1ffff80f`, 16 bytes |

After checking identity, capacity and protection, `dump_image` captured each
range twice at 950 kHz without halting the core explicitly. Byte comparisons,
length checks and SHA-256 verification passed on the downloaded copies; hashes
also match the separate workstation copies.

- Full flash SHA-256:
  `5f67d2c67205cbd96b21c900a882778b61fbcf775755748f3165210e88ad056d`.
- Option bytes SHA-256:
  `c0b942fbb9fe967ec0e7b675e080d48c930fc5fe3fde70f6dd6f9646fdffc0d3`.

The first 35,988 bytes match the pinned vendor binary exactly; all remaining
bytes are `0xff`. This confirms the installed mainboard application at zero
offset, with no separate preceding bootloader in this captured flash range.
Its build uses the 8 MHz reference selection; physical oscillator marking and
frequency remain unmeasured. See [artifact evidence](test-sv08-01-firmware.md).

Private dumps and manifest: `backups/test-sv08-01/mainboard-20260906/`.
Private commands, installation record and logs:
`local/test-sv08-01/mainboard-swd-20260906-retry/`.
A second copy of the dumps remains on the separate workstation; its temporary
path is recorded privately and should be moved to durable backup storage.
The [sanitized observation](../../profiles/test-sv08-01/observations/2026-09-06-mainboard-swd-backup.json)
records the result. Earlier failed-attempt records remain historical evidence.

## Remaining hands-on work

Keep printer supply off and disconnect ST-Link USB before moving wires.
Record mainboard PCB/MCU/oscillator markings, then connect the programmer to the
**toolhead's separately verified** SWD header using the corresponding Sovol
diagram and board labels. Report when ready. The toolhead needs its own identity,
capacity, protection checks and two complete reads; do not reuse the mainboard
512 KiB range or its firmware. Restoration remains untested for both boards.

## Sources

- [Sovol four-wire connection procedure](https://wiki.sovol3d.com/en/How-to-burn-firmware-to-the-motherboard-adapter-board),
  accessed 2026-09-06; no revision shown. It requires printer power off and a
  separate computer for programmer USB.
- [st-info v1.8.0 source](https://github.com/stlink-org/stlink/blob/v1.8.0/src/st-info/info.c),
  accessed 2026-09-06: probe syntax and target information path.
- [st-flash v1.8.0 source](https://github.com/stlink-org/stlink/blob/v1.8.0/src/st-flash/flash.c),
  accessed 2026-09-06: future read commands also halt the core; a flash read should
  not be described as having no effect on MCU execution. No st-flash read command was run.
- [Existing artifact evidence](test-sv08-01-firmware.md), pinned vendor ELF debug
  macros inspected 2026-09-06; physical board revision remains unknown.

- OpenOCD 0.12.0 installed scripts `interface/stlink.cfg`,
  `interface/stlink-dap.cfg`, and `target/stm32f1x.cfg`, inspected 2026-09-06;
  [adapter documentation](https://openocd.org/doc/html/Debug-Adapter-Configuration.html).
- [ST PM0075 Rev 2](https://www.st.com/resource/en/programming_manual/cd00283419-stm32f10xxx-flash-memory-microcontrollers-stmicroelectronics.pdf),
  August 2012, pp. 17–20 and 27–29: protection, option bytes and registers;
  accessed 2026-09-06.
