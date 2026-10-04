# Default-curve sensor commissioning intake — 2026-10-04

Owner requests default component conversion curves and defers fine calibration;
see [owner scope](../printer-component-configuration/owner-request.md).
The existing bed/hotend definitions exactly match pinned Sovol factory defaults.
Use them unchanged for the candidate input-only baseline; do not replace an unknown
installed sensor with an assumed Generic3950/PT1000 and do not fit to a BLE point.
Actual upgraded sensor part identities remain unknown. This is a proposed
observation configuration, not heater approval or completed H05 acceptance.

Separate [source research](source-findings.md) traces the preserved points,
software pull-ups and input pins to vendor and upstream revisions. Runtime
Sol6.1/medium/full role was coordinator-verified. Schematic pull-ups remain
unverified; source software values are not physical resistor measurements.
The existing installed file-output evidence can be reused for these unchanged
bytes; live MCU input configuration needs a fresh exact action review.

Beelink's existing BTHome reader completed a bounded25-second scan: five
advertisements across three packet IDs, one BTH01 advertiser, 27.67–27.68°C,
49.75%RH and100% battery. [Sanitized receipt](ble-intake.json) binds the private
capture. Mapping to the owner's chamber sensor awaits identity confirmation;
this scan is not a simultaneous bed/hotend comparison. Decoder signed little-endian
0.01°C temperature handling agrees with [BTHome v2 format](https://bthome.io/format/),
accessed2026-10-04. A fresh paired capture is needed for an ambient comparison.

The hotend name alone cannot select a sensor: the manufacturer's current
[CHCB-SV08 page](https://www.trianglelab.net/products/chcb-sv08-hotend-hot-side)
lists NTC and PT1000 options (accessed2026-10-04). This does not identify which part
is installed. Catalog choices must distinguish these alternatives explicitly.

Next: prepare/review a bounded temporary input-only Klippy session, use autonomous
PSU on/off while retaining USB host power, collect repeated temperature/button
baselines alongside fresh BLE advertisements, stop the temporary session and
return PSU off. No heaters/steppers/fans or normal printer service activation.
Attended probe/filament resting→operated→resting checks are separate H05 rows;
X/Y sensorless homing is subsequent motion work. No automatic calibration fitting.
