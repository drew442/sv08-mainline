# Test printer 01: USB bootloader/application candidate

Built 2026-09-07. Status: offline builds verified; no firmware flashed.
[Decision 0003](../decisions/0003-usb-mcu-updates.md) selects Katapult USB updates.
The installed toolhead's reference remains provisional; see
[marking evidence](test-sv08-01-markings.md).

## Artifacts and layout

Private outputs are in `artifacts/test-sv08-01-mcu-usb-v1/`, including manifest,
ELFs, firmware dictionary, binaries, a Klipper source archive and AArch64 helper.
The [public build observation](../../profiles/test-sv08-01/observations/2026-09-07-mcu-usb-build.json)
contains hashes, toolchain versions and validation limits.

| Artifact | Size | Load address | SHA-256 |
| --- | --- | --- | --- |
| Katapult | 4,720 bytes | 0x08000000 | `0d293f1fabc3b6c81e8fe436230d0765d6e339e460f4e04b3228432022dec2b7` |
| Klipper | 41,588 bytes | 0x08002000 | `5e989df184cdbb86b80d218e8c257fa655537f7f5add5c4281fdff5bd6ba59e5` |

Katapult launches at exactly the application's 8 KiB offset. Its image fits the
reserved region; the application ends at 0x0800c274 (exclusive), within both
measured flash capacities. Initial stack/reset vectors are in valid RAM/code
ranges and the reset vectors have the Thumb bit set. ELF load segments were
reviewed, including initialized RAM data's flash load address. The generic
upstream configuration conservatively links against 64 KiB flash and 20 KiB
RAM; those defaults are not new measurements of either physical MCU.

Both MCU BIN **and ELF** files matched byte-for-byte after a clean rebuild in
the same build directories. This establishes local repeatability, not bitwise
reproducibility across different paths, toolchains or machines. The source
revisions and compiler versions are recorded; no patches were used.

The single candidate pair is associated separately with the mainboard and
toolhead: both select STM32F103/USB, but only the mainboard has an installed-board
8 MHz marking report. Do not interpret sharing the binary as approval to flash
both targets.

## Rebuild using upstream tools

Run from the project root on an Ubuntu 24.04 amd64 build workstation.
Install dependencies separately; no upstream installer is used:

```sh
sudo apt-get install --no-install-recommends \
  gcc-arm-none-eabi=15:13.2.rel1-2 \
  binutils-arm-none-eabi=2.42-1ubuntu1+23 \
  libnewlib-arm-none-eabi=4.4.0.20231231-2 \
  libnewlib-dev=4.4.0.20231231-2
```

Initialize the pinned submodules without `--remote`. Use new, isolated build
directories; these commands intentionally fail if the clone destinations exist.
The pinned upstream worktrees are not build destinations.

```sh
git submodule update --init --depth 1
mkdir -p build/mcu-usb-v1
git clone --no-hardlinks upstream/katapult build/mcu-usb-v1/katapult
git -C build/mcu-usb-v1/katapult checkout --detach ec59b9bb9ad6c2ec8d4dc6831fbc77f0b308e29e
git clone --no-hardlinks upstream/klipper build/mcu-usb-v1/klipper
git -C build/mcu-usb-v1/klipper checkout --detach f0892d82b0f1c1228454f09eb508eddde2250f4b
cp configs/mcu/test-sv08-01/katapult-usb-8mhz.config build/mcu-usb-v1/katapult/.config
cp configs/mcu/test-sv08-01/klipper-usb-8mhz-8k.config build/mcu-usb-v1/klipper/.config
make -C build/mcu-usb-v1/katapult olddefconfig
make -C build/mcu-usb-v1/katapult -j4
make -C build/mcu-usb-v1/klipper olddefconfig
make -C build/mcu-usb-v1/klipper -j4
arm-none-eabi-readelf -lW build/mcu-usb-v1/katapult/out/katapult.elf
arm-none-eabi-readelf -lW build/mcu-usb-v1/klipper/out/klipper.elf
sha256sum build/mcu-usb-v1/katapult/out/katapult.bin build/mcu-usb-v1/klipper/out/klipper.bin
```

Preserve the generated configs, tool versions, build logs and hashes. Check
`CONFIG_LAUNCH_APP_ADDRESS=0x8002000` in Katapult and
`CONFIG_FLASH_APPLICATION_ADDRESS=0x8002000` in Klipper. Optional LED/button,
double-reset entry and initial pin assignments are disabled in this candidate.
Software-requested entry and empty-application entry remain in upstream Katapult.
The bootloader is `katapult.bin`, not an optional deployer.

## Host artifact

Klipper host sources were archived from the same f0892d82 revision. Its upstream
C helper source list was cross-compiled into an AArch64 shared library using
upstream flags without x86 SSE flags. The exact command remains in
`build/mcu-usb-v1/host-helper-command.txt`. Host Python syntax compilation passed.

This is not a complete host installation: the dependency environment, live
library loading, MCU protocol connection, service configuration and printer
configuration remain untested. The printer host did not answer SSH on 2026-09-07.
Cross-compilation does not validate its ABI on the Debian host. Do not activate
the helper or printer services solely on this evidence.

## Initial installation and routine update plan

Initial SWD installation and later USB updates are separate operations. Before
initial writes, corroborate the installed toolhead reference and review output
circuits in the powered maintenance arrangement. Record each target's persistent
USB identity once it enumerates; never choose a board by ttyACM ordering.

The initial procedure must identify the SWD target again, verify its backup
hashes, deliberately clear the old zero-offset application, program and verify
Katapult, then prove its USB enumeration before uploading the offset Klipper
application. An unreviewed full-chip erase command is not provided here.

For subsequent updates, use the pinned Katapult tool. The reviewed CLI accepts:

```text
python3 upstream/katapult/scripts/flashtool.py -d <identified USB device> -s
python3 upstream/katapult/scripts/flashtool.py -d <identified USB device> -f <reviewed offset Klipper binary>
```

These are workflow templates, not commands executed on this printer. The upload
command can request entry from Klipper; the USB path can change on re-enumeration.
Resolve the correct Katapult identity and verify it before retrying. Stop Klipper
first and establish idle/zero heater targets under the maintenance procedure.
Preserve the bootloader and option bytes during routine application updates.
Test re-entry and repeat upload on both boards before declaring remote updates
validated. Restore tests remain outstanding.

## Remaining tasks

- Human: corroborate the installed toolhead's reference; inspect output circuit
  behavior needed for safe bootloader operation.
- Human, when ready for USB tests: disconnect programmer USB before changing
  wiring/power arrangements, then restore the printer host to normal power
  under the maintenance plan. Do not combine programmer supply and printer
  power without a reviewed arrangement.
- Agent: complete the host dependency environment and configuration migration;
  prepare exact target-bound install/rollback commands once hardware inputs are
  resolved.
- Agent plus hardware session: run the update/recovery acceptance tests from
  decision 0003. No heat or motion is needed for USB bootloader validation.
