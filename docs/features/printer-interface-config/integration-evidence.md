# Inactive printer interfaces: offline delivery evidence

Checked 2026-09-23 for the modified `test-sv08-01` candidate. This is offline
configuration evidence only. The include is not installed or activated on the
printer, and no physical heat, motion, pause, resume or cancellation was tested.

The tracked include adds only `virtual_sdcard`, `pause_resume`, `display_status`
and `respond`. Its fixed G-code path is `/run/sv08/printer_data/gcodes`; it has
no `on_error_gcode` override or machine section. The pinned host Klipper source
is `f0892d82b0f1c1228454f09eb508eddde2250f4b`. The matched MCU dictionary
for the two simulated MCUs has SHA-256
`86665c7ba90587f09347af0001faf3681cc35819141b5c37c1f646e49a15125b`
and identifies the same Klipper revision.

`python3 -m unittest tests/test_printer_controls.py -v` passed all five tests.
The tests execute pinned Klippy in file-output mode with a disposable synthetic
printer and cover `SDCARD_PRINT_FILE`, `M23`/`M24`, pause, resume, cancellation,
status and response commands. A caught invalid G-code command exercised the
upstream default `TURN_OFF_HEATERS`: the synthetic heater target changed from
40 to 0. That result does not establish physical heater shutdown. The same
tests check the four-section contract, service and persistent G-code paths, and
H01/H02/H05 prerequisites for later H06 control use.

The coordinator separately checked the ignored private machine candidate
(SHA-256 `695a5e1c10b89a09df8a3c39852479cba786378fc33774c4a92c2d5def241842`)
with the byte-identical tracked controls file (SHA-256
`eab50d74e277951ea1678072d9b0c547675ce5f56779e78ae5a996cf0062e206`).
The private file was copied unchanged and one relative include directive was
appended in a disposable directory. Strict parsing found 34 distinct sections:
the original 30 machine sections plus exactly one of each new control section,
with `virtual_sdcard.path` at the fixed host path. Thus no private machine value
or existing section was changed or duplicated. Pinned Klippy file-output
configuration of this exact overlay exited 0, configured both simulated MCUs,
and recorded no configuration error or shutdown. The sanitized run log SHA-256
was `06492c7fdfd803db9234f8551b516a35fc9f94de73e006e941c7cc451d61d204`;
the private log and configuration were not committed. The earlier first attempt
omitted the second MCU's dictionary argument and exited 255; the corrected
two-dictionary run above is the accepted result.

These results satisfy the offline checks `pc-01` through `pc-08` in the
[approved proposal](proposal.md), subject to independent review. Existing
[commissioning gates](../../hardware/coordinated-human-tasks.md) still control
physical use. In particular, upstream `RESUME` may move and restart arbitrary
G-code, `PAUSE` does not shut down heaters, and bare `CANCEL_PRINT` does not
guarantee heater, fan or host-stream shutdown. Output-safe wrappers and the
first print remain later H06 work after H01/H02/H05 evidence.
