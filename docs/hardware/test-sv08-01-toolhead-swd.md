# Test printer 01: toolhead SWD backup

Date: 2026-09-06. Full flash and option bytes captured twice; matching reads
verified. Target role is the owner's reported toolhead connection. PCB revision
and physical MCU/oscillator markings remain unknown. Printer supply remains off
under the established maintenance arrangement, with ST-Link/V2 on the separate
workstation. No flash/option-byte write, unlock, erase or explicit reset/halt
command was issued.

## Connection and identification

Used the [mainboard method](test-sv08-01-mainboard-swd.md) with OpenOCD package
0.12.0-1build2, ST-Link/V2 firmware V2J37S7 and native `dapdirect_swd`.
The first 950 kHz attempt read the SWD DPIDR but failed core examination at
0xe000ed04. Retrying at 5 kHz identified the target; guarded captures subsequently
succeeded at 100 kHz. This does not establish the cause of the first failure.

Reset was configured as `none`, the default examine-end hook was cleared, and
debugger network services were disabled. Core debug register initialization still
occurs during attachment. Adapter voltage telemetry was approximately 3.229–3.240 V;
it is not a meter reading at the target.

| Field | Observed value |
| --- | --- |
| SWD DPIDR | `0x1ba01477` |
| Core | Cortex-M3 r1p1 |
| DBGMCU_IDCODE | `0x20036410` |
| Flash-size halfword, `0x1ffff7e0` | `0x0080`: 128 KiB |
| FLASH_OBR | `0x03fffffc`: read protection and option error bits clear |
| RDP option halfword | `0x5aa5` |
| FLASH_WRPR | `0xffffffff` |
| Captured flash range | `0x08000000–0x0801ffff`, 131,072 bytes |
| Captured option range | `0x1ffff800–0x1ffff80f`, 16 bytes |

The measured 128 KiB capacity agrees with the schematic's capacity candidate.
The firmware's generic `stm32f103xe` build string does not measure flash size
or establish the physical package marking.

## Preservation and contents

Identity, capacity and protection assertions preceded `dump_image`. Both full
flash reads are byte-identical, as are the option reads. Local hashes match those
on the separate workstation.

- Flash SHA-256:
  `8527d07b40cdee678b83b9aa8e4118bab844694faef2cb3eebd7d2db2e3633c0`.
- Options SHA-256:
  `c0b942fbb9fe967ec0e7b675e080d48c930fc5fe3fde70f6dd6f9646fdffc0d3`.

At flash base the stack vector is `0x20005000` and reset vector `0x080000bd`;
VTOR reads `0x08000000`. The embedded Klipper dictionary at byte 25,296 reports
`v0.12.0-4-g3bfe0b7-dirty`, build date 2025-07-22, 72 MHz configured runtime
clock and USB pins PA11/PA12. It agrees with the earlier live report.
Bytes after offset 31,179 are all 0xff. These observations support the installed
application at zero offset; the preserved mainboard binary is not its substitute.

The clock-register snapshot was RCC_CR=0x00004d03, RCC_CFGR=0x001de400.
Do not infer the physical oscillator frequency from the firmware's 72 MHz
constant or treat this maintenance snapshot as normal powered operation.
Clock-source verification remains a build prerequisite.

Private files and manifest: `backups/test-sv08-01/toolhead-20260906/`.
Private logs and exact guarded capture commands:
`local/test-sv08-01/toolhead-swd-20260906/`.
A second dump copy remains under the workstation's `~/sv08-recovery/`.
The [sanitized observation](../../profiles/test-sv08-01/observations/2026-09-06-toolhead-swd-backup.json)
records results. Recovery by restoration has not been demonstrated.

## Next step

Both MCU backups now exist. See the [Katapult assessment](test-sv08-01-katapult.md)
before changing the flash layout. Keep the programmer available for recovery;
a retained factory eMMC cannot undo MCU writes.

## Sources

- Owner's toolhead connection report and direct SWD/file inspection, 2026-09-06.
- [Stock references](stock-sv08.md), toolhead schematic S2, page 1; the actual PCB
  revision remains unknown.
- [ST PM0075 Rev 2](https://www.st.com/resource/en/programming_manual/cd00283419-stm32f10xxx-flash-memory-microcontrollers-stmicroelectronics.pdf),
  August 2012, pp. 17–20 and 27–29, accessed 2026-09-06: protection and option bytes.
- [Pinned Klipper STM32 Kconfig](../../upstream/klipper/src/stm32/Kconfig),
  commit f0892d82b0f1c1228454f09eb508eddde2250f4b: build-target terminology.
