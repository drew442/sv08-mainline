# Printer runtime catalogue and storage contract

The current design requirements are [Printer hardware page](printer-hardware-page-design.md)
and [Creator-published definitions](printer-definition-sources-design.md).
These replace the prior board-first page and preset-form design. This document
records runtime compatibility facts, not an alternative interface specification.

The existing runtime validates `catalog/printer/catalog.json` and structured
instance drafts. Reference mappings carry pinned source paths, hashes and line
locators. Unknown hardware identity, contacts, electrical limits and calibration
remain unknown. No board identity, clock, polarity or curve is inferred from a
similar product. Octopus non-Pro/Pro references are distinct.

The printer Store acquires host exclusion before feature exclusion. Mutations
compare revision and loaded host identity. Reviews bind draft, catalogue,
generator and host context; uncertain acknowledgment requires reconciliation.
Corrupt/newer-schema input is preserved for diagnostic export. Private MCU
identities belong to the instance, not published definitions or browser storage.
Incomplete selections can be saved. Generated candidates remain inactive until
explicit, reviewed managed publication. See [the public contract and publication
requirements](printer-public-format.md). Built-in choices are factory SV08 only;
third-party definitions use the source workflow.

Sensor generation uses a positive allowlist. Full candidates require resolved
motion, currents and thermal inputs. Preserve upstream heater protections.
Custom curves and calibration belong to a specific sensor/component fingerprint.
The Funssor complete-bed reference lacks supplied thermistor identification;
manufacturer temperature claims do not establish a replacement software cutoff.
The Sovol MAX module uses a separate CAN controller; original-SV08 adaptation
and compatible module firmware remain installation requirements.

New supported catalogue data uses the same semantic validation and generation
pipeline. Public definitions, source identity, lock snapshots, deterministic
composition and managed output must follow the two current design briefs.

[Shared-shell runtime invariants](printer-cockpit-panel.md) cover session,
navigation and exact staging. [Dated installed evidence](../features/printer-upgrade-profiles/installed-evidence.md)
records previous delivered software, not the new design's acceptance.
