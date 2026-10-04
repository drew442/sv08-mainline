# Commissioning host completed — 2026-10-04

The bounded commissioning-host goal is complete. Separate independent delivery
verification passed all three installed checks and the approved constraints;
see [findings](reviews/20261004-installed-findings.md),
[formal result](reviews/20261004-installed-result.json), and
[verified runtime](reviews/20261004-installed-runtime.json).
The accepted [execution evidence](installed-evidence.md) retains its pre-review
wording and exact source hashes; this record supplies the final acceptance.

- Healthy normal restart and HW-667 cycle: automatic A3/B0 confirmation,
  persistent state and SSH/TLS identity, immutable mounts, unchanged B/recovery.
- Actual Cockpit login/elevation/Stop/logout/relogin and simple local theme;
  requested installed account password persists.
- Exact installed host package/helper and both live MCU build/dictionary matches;
  input-only private config parsed in installed file-output mode and left inactive.

The first failed normal helper check and both repaired defects remain documented.
Two later healthy transitions are bounded evidence, not long-term boot reliability,
complete A/B failure qualification or a supported release. Stale authorization
notice and unavailable image-staging backend remain explicit UI limitations.
Sensor accuracy, input transitions, heat/motion and printing are not yet commissioned.

The owner authorized autonomous PSU control via Beelink sv08-power on/off/status.
The reviewed October4 ON/identify/OFF sequence passed; fresh status says OFF.
H616 remains USB-powered on the same boot. No HW-667 change was needed. All seven
printer/update service masks remain and serial ports are closed. H12 stays complete;
its abandoned/deferred scope remains unchanged. Next work is attended sensor/input
commissioning under a separate exact operation review, before any heat or motion.
