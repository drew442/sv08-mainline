# 0003: USB MCU updates through Katapult

Date: 2026-09-07. Status: accepted architecture; hardware validation pending.

## Requirement

The owner requires routine MCU updates without opening the printer or attaching
a programmer. Both original STM32F103 applications currently start at zero
offset. Complete mainboard and toolhead flash backups and readable option bytes
have matching repeat reads.

## Decision

Use upstream Katapult over the existing USB links for both MCUs. Install the
bootloader initially through ST-Link, then update Klipper applications from the
Linux host using a persistent, independently identified USB device path. Keep
SWD as an independent recovery method. Routine application updates must preserve
the bootloader; bootloader replacement is a separate maintenance operation.

Pin Katapult at ec59b9bb9ad6c2ec8d4dc6831fbc77f0b308e29e and retain the existing
Klipper host/MCU pin f0892d82b0f1c1228454f09eb508eddde2250f4b. Select an 8 KiB
bootloader reservation, with the application at 0x08002000. Use USB PA11/PA12,
retain SWD and omit optional GPIO assignments. The first offline candidate uses
an 8 MHz reference; that remains provisional on the installed toolhead.

This uses supported upstream configuration and build mechanisms without patches.
No custom updater or bootloader is introduced. A generic STM32F103 build fits
both measured devices, but the per-board identity, capacity and clock evidence
remain separate. Shared artifact bytes do not establish shared hardware validation.

## Alternatives

Direct SWD updates cannot meet the routine-access requirement. ROM UART also
needs physical access. Other USB bootloaders add a similar installation/layout
change without a demonstrated advantage for Klipper integration. CAN conversion
is unnecessary for the existing USB transport.

## Acceptance

Demonstrate for each board: initial programming/readback; Katapult USB
enumeration; Klipper application upload; host-commanded return to Katapult;
a second application update and verification; and normal application enumeration
after power cycling. Check interrupted application upload recovery and preserve
the bootloader. A build passing offline does not satisfy these tests.

A bootloader cannot guarantee remote recovery from arbitrary broken application
code that neither services USB nor requests the bootloader. SWD may still be
needed for exceptional faults. Avoid promising that physical recovery is never
required.

See [build evidence and workflow](../hardware/test-sv08-01-mcu-build.md) and
[Katapult assessment](../hardware/test-sv08-01-katapult.md).
