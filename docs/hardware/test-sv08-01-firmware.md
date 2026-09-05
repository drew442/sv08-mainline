# Test printer 01: existing firmware artifact evidence

Inspected 2026-09-05 using read-only file hashes, ELF headers/debug information
and the binary's embedded Klipper identify dictionary. This records a candidate
original mainboard build. It is not a flash backup or a verified build recipe.

## Preserved vendor files

The printer's `/home/sovol/klipper/out/klipper.bin`, `.elf` and `.dict` match these
files byte for byte in the pinned Sovol commit
`a60644875f8c756d20b3828c9416518b414b5491`:

| File | SHA-256 |
| --- | --- |
| [klipper.bin](../../upstream/sovol-sv08/home/sovol/klipper/out/klipper.bin) | `9af71bf52d9bc743c73d6dcd10b5394ff9cc26371d6d2de2a0cbe400f4957617` |
| [klipper.elf](../../upstream/sovol-sv08/home/sovol/klipper/out/klipper.elf) | `3b1333d3b529c1a74cae7a8a0c85a5a15e2c76658b810b37d0888369365cff3e` |
| [klipper.dict](../../upstream/sovol-sv08/home/sovol/klipper/out/klipper.dict) | `f019703c33d61641e21ee94244b83607b9015203d7486de2de82392de170b949` |

The binary is 35,988 bytes and the ELF is 1,138,592 bytes. These files are already
preserved through the vendor submodule; raw printer dumps belong in private backups.

## What the files establish

- The ELF is little-endian ELF32 ARM. Its flash load segments start at
  `0x08000000` and `0x08008560`. Reconstructing those segments with zero-filled
  gaps yields exactly the `.bin` contents.
- Its debug macro strings include `CONFIG_STM32_CLOCK_REF_8M 1`,
  `CONFIG_CLOCK_REF_FREQ 8000000` and `CONFIG_STM32_FLASH_START_0000 1`.
  These describe this candidate build's clock selection and application offset.
- The binary begins with stack value `0x20005000` and reset vector `0x080053e1`.
- The compressed identify dictionary starts at byte offset 29,756. Its decoded
  contents match the sidecar `.dict`, including version, build versions and
  reported configuration constants.
- The embedded version is `v0.12.0-40-g77619e91-dirty`, with build timestamp
  2024-03-01 10:46:56. Its GCC 10.3.1 build report and constants match the running
  mainboard's reported identity. The firmware target is `stm32f103xe`, with
  72 MHz runtime clock and USB on PA11/PA12.

The private inspection reports retain the complete build strings. The
[sanitized observation](../../profiles/test-sv08-01/observations/2026-09-05-artifacts.json)
records the evidence and its limits.

## What remains unknown

An identical reported identity does not prove identical installed flash. Neither
MCU has been read through SWD; board markings, physical clock source, protection
state, full flash contents and any bootloader remain unverified. Keep the
profile's installed clock/offset fields unknown until those checks are complete.

The toolhead reports a different July 2025 build. No matching artifact was found
in the bounded `/home/sovol` search, which excluded Git metadata, virtual
environments, caches, `printer_data` and symlink traversal. This was not an
exhaustive disk search. Do not use the March 2024 candidate as toolhead recovery
firmware merely because both devices report the same MCU target string.

The on-disk `.config` and `out/autoconf.h` select ATmega2560 and conflict with
these ARM artifacts. They cannot reproduce this binary. A future upstream build
needs independently reviewed per-board settings and its own toolchain record.
