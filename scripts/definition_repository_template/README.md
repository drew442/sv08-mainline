# My printer modifications

Publish a public GitHub repository so users can select your modifications in
SV08 Mainline. Edit small JSON files using Klipper setting names. The appliance
handles component mappings and pins the expanded settings when users select them.

## Quick start

1. Extract this ZIP and use the contents of `printer-definition-repository/` as
   your repository root. Edit `catalog.json`: choose your catalogue ID/name and
   `publisher.name`.
2. Edit `definitions/bed.json`, or copy an example. Supply `id`, `name`, `version`,
   the factory component to `extends`, and only the settings your mod changes.

   ```json
   {
     "id": "funssor-cn3d-hotbed",
     "name": "Funssor CN3D heated bed",
     "version": "1.0.0",
     "extends": "sv08.factory.hotbed",
     "heater_bed": { "max_temp": 120 }
   }
   ```

   This illustrates the owner's stated factory-equivalent/120°C configuration;
   it is not a manufacturer certification. Add an HTTPS `guide` for your exact
   hardware and installation. The supplied bed example keeps the factory105°C.
3. Run `python3 tools/update_catalog.py`. It refreshes the index automatically and
   detects missing local bases/cycles. Compact inheritance has no dependency hashes
   to maintain. This stdlib helper does not replace the full hardware validator.
4. From an SV08 Mainline checkout, run:

   ```sh
   python3 scripts/printer_definitions.py validate /path/to/your-repository
   python3 scripts/printer_definitions.py bundle /path/to/your-repository > bundle.json
   ```

5. Commit/push your JSON files as ordinary, non-executable files. If your catalogue
   was executable, use `git update-index --chmod=-x catalog.json` before committing.
6. On the printer open **Definition sources**, enter your repository URL, preview
   and add it. Users can then select the modification under **Printer hardware**.
   Alternatively import `bundle.json` for offline testing.

## Other hardware

Every factory definition is an inheritance base: bed, hotend, mainboard/toolhead
board, probe, fans, filament sensor, steppers, LEDs, display, accelerometer and MCU
sensors. Use the definition ID shown in **Definitions**, or documented aliases:
`sv08.factory.hotbed`, `sv08.factory.hotend`, `sv08.factory.mainboard`,
`sv08.factory.toolhead_board`, `sv08.factory.probe`, `sv08.factory.stepper_x`, etc.
`sv08.factory.printer` is the complete factory printer. `extends` can name another
file's definition ID or list several bases to form a kit; `assembly.json` shows it.

Use `configuration` when editing several Klipper sections, such as `extruder`,
`tmc2209 extruder`, `fan_generic enclosure_fan` or `verify_heater heater_bed`.
New devices require an explicit documented board ID and connector/pin. Unknown
hardware, raw code and unsupported settings are rejected, not guessed. Custom
board mappings and finite check-only levelling rules are under `advanced`.
See the complete public format reference for section/field coverage.

PID gains, measured Z offsets, private MCU identities and calibration stay local;
do not publish them as universal defaults. Already published versions are
immutable: bump versions before changing their bytes. Updating a source does not
silently change selected settings. Keep guide/source attribution and GPL terms.

## Included files

- `definitions/bed.json`: a compact bed modification.
- `definitions/board.json`: factory mainboard inheritance example.
- `definitions/assembly.json`: local bed + factory probe bundle.
- `definitions/behaviour.json`: advanced, explicit no-additional-check example.
- `fixtures/installation.json`: disposable preview input, not a printer identity.
- `tools/update_catalog.py`, `catalog.json`, `LICENSE`, `.gitignore`.

Format: https://github.com/drew442/sv08-mainline/blob/main/docs/development/printer-public-format.md
