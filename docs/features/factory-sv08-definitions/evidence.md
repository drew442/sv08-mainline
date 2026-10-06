# Complete factory SV08 definitions — offline evidence

2026-10-06. Coordinator self-validation under the proportionate review decision;
no independent feature-verification claim. Source publication is not a flashable
release or physical hardware validation.

## Delivered behavior

`sv08.factory` 0.2.0 supplies both controller references and 24 factory devices,
plus motion, mesh, gantry and safe-homing settings. A normal “Use factory SV08”
button previews the assembly before selection. Component choices and the separate
Definition sources menu remain available. Direct and creator-bundled bed replacements
preserve the other assembly contributions and invalidate the measured probe offset.
Hardware selections save without PID calibration.

The pinned primary configuration is
`upstream/sovol-sv08/home/sovol/printer_data/config/printer.cfg` at
`a60644875f8c756d20b3828c9416518b414b5491`, SHA-256
`8936ceabc98a6583f3cff17093905162ac516a0996c8714ef62825a6cb005289`.
Field audits include alias resolution, vendor firmware SPI wiring/rate, exact
numeric/Boolean/polarity transformations and pinned mainline defaults. The script
refuses changed primary bytes and produces identical catalogue/public-record bytes
on regeneration. Unrelated catalogue boards and curves are unchanged; gitlinks and
`upstream-lock.json` are unchanged.

Native adaptations are documented in [the runtime catalogue contract](../../development/printer-hardware-catalog.md):
explicit ADXL software SPI, native safe Z home, no sensorless hold current and
mainline-default LED PWM period. Factory controller identities, motor physical
ratings and measured calibration are not published. Documented current defaults
remain usable without fabricated ratings; changing a current or motor connector
requires an owner-entered rating. Legacy candidates still require their original
explicit inputs. The original pressure-contact GPIO is monitored with empty actions;
vendor-specific automatic Z/pressure probing remains a separate workflow.

## Observed checks

- `python3 -m unittest discover -s tests -p 'test_printer_*.py'`: **79 passed**,
  including catalogue/source audits, Store/Budget and durable recovery, definitions,
  controls and publication. Existing pinned validation environment was enabled.
- `python3 -m unittest discover -s tests -p 'test_factory_sv08.py'`: **8 passed**,
  including all 24 devices, finite schemas/negative fields, browser numeric digest
  round-trip, private/calibration gaps, direct/bundled replacement, current/connector
  overrides and complete native Klipper output.
- `python3 -m unittest discover -s tests -p 'test_stage_printer_ui.py'`: **12 passed**.
  Staging includes the new imported fields module through its existing dependency
  closure and runtime file enumeration.
- `python3 scripts/printer_definitions.py validate examples/printer-definitions`:
  four legacy public examples accepted.
- Regeneration idempotence, catalogue/public JSON Schema, generated-adapter agreement,
  unchanged unrelated catalogue entries, relevant Markdown links and `git diff --check`
  passed.
- Actual Chromium and the real disposable Python Store/Budget completed the full
  [browser journey](browser.json): complete-factory preview/cancel/select/save/reload,
  source bundle/disable/remove/offline retention, stale authority/generation and
  lost acknowledgment recovery, existing component controls, keyboard/touch,
  narrow/desktop/200% layouts, and unchanged fixture live configuration. The keyboard
  cancellation check waits for the native board dialog to finish closing before
  starting the next asynchronous operation.

Pinned parser evidence uses Klipper `f0892d82b0f1c1228454f09eb508eddde2250f4b`,
matching dictionary SHA-256
`86665c7ba90587f09347af0001faf3681cc35819141b5c37c1f646e49a15125b`, existing
`build/printer-interface-prep-20260918/venv/bin/python`, simulated MCU file output and
the bounded private API ready check. No serial devices, heater/motion requests,
host installs or service restarts occurred. Factory output passed alongside the
legacy full-output and check-only behaviour fixtures.

## Limits

These checks prove sourced data, composition, software syntax, storage and UI
behavior. The Chromium fixture uses a Cockpit RPC/session shim, not authenticated
ARM64 Cockpit. Physical circuit identity/polarity/ratings, safe operating limits,
calibration and a printing release remain unmeasured. Installation has its own
exact-overlay assessment and receipt; this document does not attest that operation.
Screenshots, private fixture state, payload packets and raw runtime logs remain local.
