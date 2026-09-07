# Test printer 01: host environment and commissioning preparation

Date: 2026-09-07. The new Debian 13.6 host is online again. Both factory MCUs
enumerate as USB serial devices. Persistent identities remain private.
Klipper and Moonraker remain inactive; no firmware was written or physical MCU
command sent during these checks.

The owner confirms the installed toolhead is configured identically to the spare.
Its 8 MHz reference is now supported by owner-reported installed equivalence,
not an independent frequency measurement. This updates the earlier provisional
[marking record](test-sv08-01-markings.md).

## Completed on the printer host

- Compared all 2,327 staged Klipper source files against pinned commit
  f0892d82b0f1c1228454f09eb508eddde2250f4b: no mismatches.
- Created `/opt/sv08-mainline/venvs/klipper-f0892d8` with Python 3.13.5.
- Built/downloaded 11 runtime wheels from upstream's exact requirements,
  installed using the local wheelhouse, and passed `pip check`.
- Installed and loaded the previously cross-built AArch64 C helper through
  Klipper's CFFI interface; verified its hash against the build manifest.
- Imported the host's runtime dependencies and exercised Klippy's CLI.
- Loaded the [communication-only config](../../configs/commissioning/test-sv08-01-no-outputs.cfg)
  with two dictionaries from the newly built MCU artifact, processed STATUS,
  and exited successfully using `-o` file output.

This validates the selected host environment and configuration parser on this
host architecture. File-output mode does not open the physical MCU serial
devices; its “Configured MCU” log messages describe simulation with supplied
dictionaries. It does not validate the still-installed factory firmware,
actual USB re-entry, sensor readings, heat or motion.

The template uses upstream developer `none` kinematics and contains no output
pins, steppers, heaters, fans or probes. It is for communication commissioning,
not a usable printing configuration. Replace its two serial placeholders only
in an ignored local copy before a later physical connection test.

## Dependency preservation and replay

Wheelhouse on the printer: `/opt/sv08-mainline/wheelhouse/`.
A second local copy and hashes are in
`artifacts/test-sv08-01-host-python-v1/`.
The [runtime lock](../../configs/host/test-sv08-01-python313-arm64.lock) pins
all 11 wheels, including transitive runtime dependencies. It is specific to
Python 3.13/Linux arm64 and the preserved wheels. It does not claim reproducible
wheel compilation: isolated build dependencies were not separately locked.

For another prepared Python 3.13 arm64 virtual environment:

```sh
python -m pip install --no-index --require-hashes \
  --find-links=/path/to/preserved/wheelhouse \
  -r configs/host/test-sv08-01-python313-arm64.lock
python -m pip check
```

This lock was checked on the host using pip's `--dry-run --ignore-installed`
resolver with hashes required. No latest-version upgrade or vendor installer
was used. Pip itself came from Debian's virtual environment bootstrap
(version 25.1.1); its package is not included in the runtime wheel lock.

## Reproduce the file-output test

After staging the config and MCU dictionary, run with absolute local paths:

```sh
printf 'STATUS\n' > input.gcode
/opt/sv08-mainline/venvs/klipper-f0892d8/bin/python \
  /opt/sv08-mainline/klipper/klippy/klippy.py \
  test-sv08-01-no-outputs.cfg -i input.gcode -o mcu-output \
  -d klipper.dict -d extra_mcu=klipper.dict -l klippy.log
```

Retain `-o` for this offline test. Review exit status and log for both configured
MCUs; do not interpret a successful simulation as physical commissioning.

## Next maintenance session

ST-Link USB still enumerates on the separate workstation while the printer is
powered on. Its current target wiring and 3.3 V lead have not been confirmed,
so no SWD probe or write was attempted. The earlier four-wire arrangement
supplied target power through the programmer with printer supply off. Confirm
the current arrangement before choosing the initial flashing step.

Initial Katapult installation, exact target-bound programming/rollback commands,
and repeat USB update tests remain open. Printer configuration migration and
output-circuit validation remain separate from this host setup. Existing
factory firmware is unchanged, and the preserved full backups remain the
recovery inputs.

Private installation/build logs, source comparison and test output:
`local/test-sv08-01/host-integration-20260907/`.
See the [sanitized observation](../../profiles/test-sv08-01/observations/2026-09-07-host-integration.json)
and [USB build record](test-sv08-01-mcu-build.md).
