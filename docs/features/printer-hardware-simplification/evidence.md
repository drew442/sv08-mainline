# Offline simplification evidence

Base revision: `7423621`. Coordinator self-validation; no independent review claim.
This evidence covers the simpler source UI and catalog/runtime support, not the
installed printer, physical circuit compatibility, heater operation or printing.

- `python3 -m unittest discover -s tests -p test_printer_configuration.py`:
  38 tests passed, including atomic replacement, unrelated-device preservation,
  collision rejection, default PT1000 and advanced custom NTC curve rejection cases.
- `python3 -m unittest discover -s tests -p test_stage_printer_ui.py`:
  11 staging and preservation tests passed.
- `node --check ui/printer/app.js`, `git diff --check`, catalog JSON Schema and relevant document links: passed.
- `tests/test_printer_browser_fixture.py` with Node 22.23.2 and cached Chromium
  1208 running `tests/printer_browser.mjs`: complete journey passed at
  1024×600, 1440×900 and 390×844. Added bed/hotend dropdown, enclosure-fan toggle,
  NTC/PT1000 swap, board bias, preserved bounds, cleared PID, saved profile and
  reload checks. Connection setup stays open while editing its transport. Ordinary advanced settings remain collapsed.
- Generated PT1000 and custom three-point NTC sensor configs reached `ready` in
  pinned Klippy `f0892d82b0f1c1228454f09eb508eddde2250f4b` file-output mode with
  the existing disposable Python environment and matching main-MCU dictionary.
  No physical MCU connection was made. See sanitized [parser receipt](parser.json)
  and [browser receipt](browser.json).

Corrected checks: collision fixture originally selected a fan-incompatible pin;
changed it to an independently allocated heater output. The browser harness needs
Node 22's WebSocket, not the host's Node 18. A reused fixture already on generation B
could not reproduce its A-to-B stale-context test; the passing run used fresh state.
Moving candidate tools into a details panel changed the keyboard order; the browser
check now opens that panel and verifies focus reaches its summary and output mode.
The first parser probe looked for a log message not emitted by file-output mode;
the corrected probe queried the actual Klippy API `info.state`.

Selected component `profile` and `custom_curve` are optional structured draft fields;
legacy drafts remain accepted. Catalog revision and generator version 4 bind new
reviews. The simple assembly selector omits PID gains, including reference gains. PID gain entry is separate from hardware settings under candidate preparation. Full PID output still requires valid gains; hardware Save is independent.
Pin/current/temperature/cold-extrusion protections remain enforced. No gitlink,
upstream lock, toolchain, live printer settings or installed host was changed.

Remaining: exact product specifications for Funssor/CN3D bed, hotend upgrades and
chamber heater; supported wiring and limits for their presets; updated installed
runtime/catalog/UI packet and its preservation checks. Existing installed evidence
applies to the previous interface, not this revision.
