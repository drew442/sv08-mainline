# Simplify printer hardware choices

Use board dropdowns, board-specific bed/hotend assembly choices and fan checkboxes
as the everyday interface. Keep MCU connection setup expandable, low-level device
fields under advanced settings, and candidate generation/export/import separate
from the primary Save hardware settings button. Save does not require PID tuning.

Component selection replaces its named assembly and sensor dependency atomically,
preserves unrelated devices, and validates exclusive pins and board/device names.
Record the selected profile independently of editable sensor/settings overrides.
Sensor changes restore the documented board-input bias, preserve temperature bounds,
clear custom NTC overrides and heater PID gains, and allow saving before later tuning.
Add the pinned Klipper PT1000 definition and an advanced three-point custom NTC curve.
No new heater activation, live configuration or service mutation is included.

Acceptance: offline catalog/store checks, assembly replacement/collision checks,
PT1000/custom-curve validation and pinned Klippy file-output readiness; staging
regressions; Chromium everyday hardware save/reload and fan toggle, existing session,
stale-context, lost-ack, import/export and responsive journeys; inspect the whole diff.

The complete owner request also requires product-specific upgrade choices and an
installed page. Those remain separate pending tasks. The exact Funssor/CN3D kit,
hotend upgrades, fan and chamber-heater models/connections were requested on
2026-10-05. The manufacturer's complete-kit page does not provide its thermistor
configuration. No speculative upgrade or chamber-heater preset is added.
