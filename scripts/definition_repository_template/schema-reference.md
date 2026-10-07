# SV08 definition schema reference

This reference contains the complete public JSON Schema set used by this version
of SV08 Mainline, for compact authoring and rich definitions. All schemas use
JSON Schema Draft 2020-12. Point your editor or validator at the appropriate local
file; do not add an unsupported $schema field to definition documents.

| Document | Schema |
| --- | --- |
| Compact modification (no kind) | [compact](schemas/compact.schema.json) |
| Catalogue index | [catalog](schemas/catalog.schema.json) |
| Board | [board](schemas/board.schema.json) |
| Component | [component](schemas/component.schema.json) |
| Connection | [connection](schemas/connection.schema.json) |
| Assembly / kit | [assembly](schemas/assembly.schema.json) |
| Finite behaviour | [behaviour](schemas/behaviour.schema.json) |
| Common rich definition fields | [definition](schemas/definition.schema.json) |

Read [the complete public format guide](public-format.md) for inheritance, supported
Klipper sections, examples, sources, validation and immutable versions. The guide's
project links point to public upstream documentation. [field-registry.py](field-registry.py)
contains the complete typed managed component field registry, choices and printer
geometry validation rules, copied from this build for reference; it is not a
standalone validator or something to install on the printer.

JSON schemas describe structural constraints. They do not fully express supported
setting values, inheritance resolution, dependency hashes, board capabilities, pin
collisions or physical suitability. Run SV08 Mainline's printer_definitions.py
validate and preview commands before publishing. Unsupported arbitrary Klipper
settings and executable configuration are rejected. Calibration stays local.
