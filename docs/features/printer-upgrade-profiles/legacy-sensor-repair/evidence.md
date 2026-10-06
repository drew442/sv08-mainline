# Legacy sensor assembly replacement repair — 2026-10-06

Owner reported a pin collision preventing the Funssor test selection. Installed
revision 9 retains legacy standalone `bed_temperature` (main PC5) and
`hotend_temperature` (tool PA5). Previously, assembly selection removed only its
canonical names, leaving these occupied inputs behind. Coordinator reproduced
that name/input mismatch; the reported tool collision concerns the same hotend
input mechanism, whereas bed replacement occupies main PC5.

Source `2cbe70c` replaces standalone sensors on the selected assembly's same-board
input atomically, preserves the other board and refuses a sensor used by a retained
heater. Calibration stays associated with the removed hardware. Ordinary validation
errors no longer display an unacknowledged-save hint; genuine reconciliation still
does. Forty-two `test_printer_configuration.py` tests passed, including legacy bed
and hotend replacement, original-draft/other-board preservation and retained
heater dependency refusal. Node syntax and whitespace checks passed.

The [exact operation review](review.md) passed with conditions. A fresh dry run
and two-file overlay installed the catalog runtime and printer controller on
**test-sv08-01**, same diagnostic slot A. Private beforeimages/packet/status remain
at `/data/sv08/printer-assembly-repair-backup-20261006`. The
[immediate](immediate-preservation.json) and [final](final-preservation.json)
checks passed all 52 installed files/eight directories, exact metadata/membership,
saved context, boot/CID, read-only root/boot, seven masked inactive services, absent
live configuration and capacity. PSU was OFF before execution and after acceptance.

The [actual authenticated ARM64 browser journey](browser.json) selected Funssor
bed directly from the preserved legacy draft, then selected the hotend assembly,
without manually removing a sensor or encountering collisions. It also passed
chamber add/remove and inherited navigation/layout checks. No Save/apply was sent;
reload discarded unsaved selections and preserved the original saved state.
Final logout and own Chrome/profile/tunnel cleanup completed. The browser launcher
initially reached its newly started tunnel before it was ready; adding a bounded
connection wait corrected the invocation before authentication. Installation was
not replayed. [Hashes](artifacts.json) bind private receipts retained under
`local/feature-workflow/probes/printer-assembly-repair-20261006/`.

This fixes selection behavior; unidentified Funssor thermistor and original-SV08
chamber adaptation/firmware requirements remain. No physical outputs were activated.
