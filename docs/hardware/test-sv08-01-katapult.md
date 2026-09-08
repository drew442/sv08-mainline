# Test printer 01: Katapult preparation

Updated 2026-09-07. The owner requires routine updates without physical access.
[Decision 0003](../decisions/0003-usb-mcu-updates.md) selects Katapult USB.
[Bootloader and application artifacts](test-sv08-01-mcu-build.md) now build
offline with matching offsets. The [toolhead bootloader](test-sv08-01-toolhead-katapult.md)
is now programmed with matching full readback. Subsequent
[toolhead USB tests](test-sv08-01-toolhead-usb.md) verified two application uploads,
software re-entry and a ready host connection. The
[mainboard bootloader](test-sv08-01-mainboard-katapult.md) is now installed with
matching full readback; its USB/application tests remain pending.

## Choice for project goals (2026-09-07)

Katapult over the existing USB transport remains the preferred maintenance
choice. Keep direct ST-Link/OpenOCD flashing as the bring-up alternative and
independent recovery method. There is no demonstrated need for a custom
bootloader or a CAN conversion.

| Option | Project fit | Tradeoff |
| --- | --- | --- |
| Direct SWD, Klipper at zero offset | Simplest initial build and existing full-flash rollback layout | Every MCU update requires physical programmer access |
| Katapult over USB | Preferred for repeatable host-driven updates and Klipper bootloader entry | Adds a pinned artifact and requires matched application layout and hardware testing |
| STM32F103 ROM UART loader | Possible fallback if boot pins and UART are accessible | Requires a different physical connection; no advantage over the working ST-Link here |
| stm32duino, HID or MSC USB bootloader | Alternatives documented by Klipper | Also require board configuration and layout changes; no project-specific benefit established |

Do not assume these STM32F103 parts have the factory USB DFU interface of some
other STM32 families. Klipper documents their ROM programming path as UART.
Katapult's USB upload path is provided by the installed flash bootloader.

The [new marking evidence](test-sv08-01-markings.md) agrees with the MCU capacity
measurements. Mainboard 8 MHz now has owner-reported marking support. Toolhead
8 MHz was initially provisional because its marking was read from a spare;
the owner has now confirmed installed/spare equivalence. PCB revision
labels are useful evidence, not a hard gate for offline preparation.

## Benefit and consequence

Katapult supports USB as well as CAN and UART; this printer does not need a CAN
conversion to use it. Its upstream configuration includes STM32F103. Future
application updates could then use the host's USB connection, reducing repeated
SWD wiring. Board-specific clock, communication pins and boot entry still need
review.

The [mainboard](test-sv08-01-mainboard-swd.md) and
[toolhead](test-sv08-01-toolhead-swd.md) have matching repeat-read full backups.
Both installed applications occupy zero offset. Installing a bootloader changes
that layout and replaces existing firmware bytes. A zero-offset factory binary
cannot simply be uploaded at the new application address: it must be rebuilt
for that address. Restoring factory operation would require restoring the correct
board's original flash through SWD, as well as selecting the factory host system.

## Preparation tasks

- [x] Preserve both original full flash ranges and readable option bytes twice.
- [x] Establish toolhead capacity as 128 KiB through the size register and capture;
  keep it distinct from the 512 KiB mainboard.
- [x] Inspect a fixed Katapult source revision:
  `ec59b9bb9ad6c2ec8d4dc6831fbc77f0b308e29e`.
  This is now a pinned project submodule; offline builds pass, hardware tests remain.
- [x] Owner supplied mainboard and spare-toolhead MCU/reference markings;
  see the separate evidence scopes in the marking record.
- [ ] Corroborate the installed toolhead reference; verify relevant USB and
  output circuitry for each board. Record PCB revisions when accessible.
- [x] Build Katapult with recorded toolchain/configuration and retained SWD;
  optional GPIOs are unassigned. Review actual output circuits before writes.
- [x] Build the shared per-board candidate with an 8 KiB application offset;
  check ELF ranges, vectors, sizes, hashes and clean rebuild agreement.
- [x] Cross-build the AArch64 host helper and archive matching host sources.
- [x] Complete and test the host dependency environment and live helper loading;
  see [host integration](test-sv08-01-host-integration.md).
- [x] Toolhead USB re-entry and two application updates verified.
- [ ] Repeat installation and USB tests for the mainboard.
- [x] Prepare the exact per-board installation and SWD rollback commands using
  identified targets and reviewed artifact paths/hashes. Review erase scope,
  readback verification and boot entry behavior before a write. See
  [initial programming preparation](test-sv08-01-initial-programming.md).
- [ ] Install during maintenance with loads safe, verify programming, then test
  USB bootloader enumeration and application update/re-entry. Record these as
  separate hardware tests before printer-service activation.

The source's “Build Katapult deployment application” menu concerns an optional
deployer; it is not by itself the new Klipper application's offset selection.
For initial ST-Link installation, review the direct bootloader output and its
actual generated application address. Do not substitute a deployer binary.

## Recovery limits

The full toolhead backup covers 0x08000000–0x0801ffff; the mainboard backup covers
0x08000000–0x0807ffff. Retain each manifest and option capture. Proposed factory
rollback is to reconnect SWD, re-identify the board, restore its full original
flash at 0x08000000, and verify the entire range before normal power-up.
Option bytes are evidence, not an instruction to rewrite them. This restore
path has not yet been exercised.

Until reviewed artifacts exist, keeping the ST-Link connected is useful
preparation but is not enough to choose or flash a bootloader binary.

## Sources

- [Katapult README at reviewed revision](https://github.com/Arksine/katapult/blob/ec59b9bb9ad6c2ec8d4dc6831fbc77f0b308e29e/README.md),
  accessed 2026-09-06: supported transports, board configuration, installation
  and matching Klipper application offset.
- [Katapult STM32 Kconfig at reviewed revision](https://github.com/Arksine/katapult/blob/ec59b9bb9ad6c2ec8d4dc6831fbc77f0b308e29e/src/stm32/Kconfig),
  accessed 2026-09-06: STM32F103, clock/USB selections and optional deployer.
- [Pinned Klipper STM32 Kconfig](../../upstream/klipper/src/stm32/Kconfig),
  commit f0892d82b0f1c1228454f09eb508eddde2250f4b: application offset choices.

- [Klipper bootloader documentation](https://www.klipper3d.org/Bootloaders.html)
  and [bootloader entry](https://www.klipper3d.org/Bootloader_Entry.html),
  accessed 2026-09-07: STM32F103 alternatives and Katapult entry integration.
