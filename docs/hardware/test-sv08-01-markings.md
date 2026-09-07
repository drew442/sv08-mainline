# Test printer 01: MCU and reference markings

Recorded 2026-09-07 from the owner's transcription. Toolhead markings were read
from a **spare factory SV08 toolhead**, described by the owner as the same type.
Mainboard markings were not described as coming from a spare. No photographs
or frequency measurements were supplied. Raw marking strings remain private.

| Assembly inspected | Parsed part number | Reference marking | Agreement with existing evidence |
| --- | --- | --- | --- |
| Mainboard, owner-reported | STM32F103VET6 | YXC 8.000 | Published U14 is VET6; installed SWD capacity is 512 KiB; installed vendor build selects 8 MHz |
| Spare toolhead, owner-reported | STM32F103CBT6 | YXC 8.000 | Published U5 is CBT6; installed toolhead SWD capacity is 128 KiB |

The concatenated toolhead transcription begins with STM32F103CBT6; subsequent
characters are retained privately without interpreting their manufacturing
codes. They are not PCB revision identifiers. The reference's 8.000 marking is
evidence of a nominal 8 MHz component, not a measured frequency, tolerance or
complete component specification.

The installed toolhead's generic firmware target string `stm32f103xe` is not
a contradiction: its independently read flash-size register reports 128 KiB.
Both installed firmware dictionaries identify USB on PA11/PA12.

## Subsequent owner confirmation

Later on 2026-09-07 the owner confirmed the installed toolhead is configured
identically to the inspected spare. This supports the 8 MHz installed reference
as owner-reported equivalence. The original transcription still came from the
spare; no photograph or direct frequency measurement is implied. The earlier
provisional assessment below records the scope at initial intake.
See [host integration](test-sv08-01-host-integration.md).

## Scope and board variants

The spare markings support an **8 MHz candidate** for the installed toolhead.
They do not directly identify its crystal or prove identical board routing,
thermistor circuitry or GPIO behavior. Keep the installed clock field unknown
until corroborated on that board. Offline candidates can be prepared with the
assumption explicit; do not silently promote them to flash-approved artifacts.

The consulted Sovol schematic and official original-SV08 documentation did not
establish a conflicting toolhead MCU variant or provide an exhaustive PCB
revision inventory. This is not proof that only one revision exists. SV08 Max,
Zero, aftermarket boards and mechanical hotend revisions must not be treated
as interchangeable electronics.

A PCB revision marking is useful for associating a board with a schematic and
tracking electrical changes. It is not itself a compiler input or a prerequisite
for offline builds. If inaccessible or absent, record it as unknown and verify
the relevant MCU, clock, USB wiring and output circuits directly before hardware
validation. Identical MCU and crystal markings alone do not establish identical
heater, thermistor or fan circuits.

## Next work

- Prepare separate mainboard and toolhead candidates: STM32F103, USB PA11/PA12;
  8 MHz is owner-supported on the mainboard and provisional on the installed
  toolhead. Respect each measured flash capacity.
- When accessible, confirm the installed toolhead's 8.000 marking, or establish
  its reference selection through independent installed-board evidence.
- Record PCB labels/photos opportunistically; do not require unnecessary
  disassembly solely to obtain a revision string.
- Follow the [bootloader assessment](test-sv08-01-katapult.md). No firmware write
  is authorized merely by recording these markings.

## Sources

- Owner report, 2026-09-07; [sanitized observation](../../profiles/test-sv08-01/observations/2026-09-07-markings.json).
- [Sovol inventory and primary schematic links](stock-sv08.md), S1/U14 and S2/U5,
  page 1, pinned vendor commit a60644875f8c756d20b3828c9416518b414b5491.
- [ST STM32F103x8/xB datasheet](https://www.st.com/resource/en/datasheet/stm32f103cb.pdf)
  and [ST STM32F103xC/xD/xE datasheet](https://www.st.com/resource/en/datasheet/stm32f103ve.pdf),
  ordering information and device feature tables, accessed 2026-09-07.
- [Sovol original-SV08 documentation](https://wiki.sovol3d.com/en/SV08),
  accessed 2026-09-07; no comprehensive PCB revision list established.
