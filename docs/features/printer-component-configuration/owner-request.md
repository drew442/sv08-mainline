# Owner request — component configuration and sensor commissioning

Date: 2026-10-04. Authority: direct owner instruction in the project conversation.

## Two delivery goals

1. Complete the next sensor-only commissioning work using component default
   calibration curves. Defer fine tuning those curves. The owner's BLE temperature
   sensor is in the printer chamber beside the bed and remains available as an
   ambient reference. Preserve input/temperature protections; no heating or motor
   operation is part of this sensor-only goal. Physical input transitions still
   need observation of the relevant action; a BLE chamber reading is not a contact
   measurement or a heated-range calibration.
2. Develop and deliver a Cockpit configuration section for selecting printer
   hardware. Organize it by mainboard and toolhead board, with connected components
   beneath each board: motors/drivers, heated bed, temperature sensors, limits and
   other relevant devices. Show the relevant input/output pins. Prepopulate
   documented defaults and common options, make it easy for users, and make future
   hardware support straightforward for contributors.

The owner requests development of the idea, goals and implementation, not merely
a mockup. Concrete design, source-backed initial catalog, validation, persistence,
configuration generation and installed user journey are to be proposed and
independently reviewed under the existing delegated workflow. Default curves mean
component definitions without new calibration tuning; they do not authorize
inventing unknown sensor identities, pull-up circuits or board pin assignments.

## Existing authority and boundaries

The owner authorized autonomous printer PSU on/off/status through Beelink
`/usr/local/bin/sv08-power`. USB power through HW-667 is independent and can keep
H616 running while PSU is off. Hardware operations remain coordinator-owned with
exact review where required. Printer configuration editing must distinguish a
saved draft from active hardware settings; choosing a board cannot silently
reassign pins or energize outputs. Preserve private per-printer identities and
existing accepted configuration/firmware/update contracts.

The commissioning-host goal is complete, and H12's abandoned/deferred scope stays
unchanged. Fine calibration is explicitly deferred, not a prerequisite for this
new work. Heating/motion/first-print commissioning follow their own evidence gates.
