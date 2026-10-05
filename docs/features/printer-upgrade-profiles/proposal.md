# Named bed and separate CAN chamber module profiles

Add the named Funssor bed choice to the original SV08 bed interface reference.
Retain existing conservative board-reference power/temperature settings, omit PID
and clear the old factory sensor curve. The exact supplied thermistor remains
unknown in the manufacturer's page: allow saving this choice and choosing its
sensor, but do not generate a complete candidate with a guessed sensor.

Sovol's pinned SV08MAX chamber_hot.cfg provides a separate CAN MCU, two EPCOS
sensor inputs with 20000-ohm reference bias, and a watermark-controlled chamber
heater. Add a distinct chamber board role and typed chamber heater kind, with
source-backed pin/default provenance. A single checkbox selects this module and
its internal board/devices. CAN identity remains private and explicitly entered;
serial transport and mainboard GPIO substitution are unsupported. Preserve
upstream heater verification; do not copy vendor macros, relaxed verification,
firmware or sample CAN UUID. The module's MAX installation/manual is reference
evidence, not original-SV08 hardware compatibility or mainline-firmware acceptance.

Checks: catalog/schema and primary-line provenance, backward draft acceptance,
role-qualified pins, collisions and transport/identity rejection, both sensor and
full-mode generation, source/refusal persistence; full existing offline/staging
regressions; Chromium module add/remove and named-bed incomplete-save journey.
Self-validation covers reversible offline development only. Installed delivery
and actual adapter/firmware/wiring commissioning remain pending.
