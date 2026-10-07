# Authoring SV08 definitions

Read README.md and reference/README.md before editing. Use compact JSON: product
identity, immutable version, factory or local inheritance, and only changed Klipper
settings. Keep component details under advanced when required.

Use exact manufacturer documentation for hardware, pins, sensor types and limits.
Cite guides and sources; distinguish documented facts from examples and assumptions.
Do not guess electrical mappings or publish private MCU identities, credentials,
measured offsets, PID calibration or printer-specific state as universal defaults.

Use reference/schemas/compact.schema.json for compact records and the matching
rich schema for advanced records; catalog.schema.json describes catalog.json.
Schema validation checks document shape. Full SV08 validation checks supported
settings, inheritance, wiring and safety constraints. Follow README.md commands.

Bump published versions before changing bytes. Run tools/update_catalog.py, then
validate with SV08 Mainline before proposing publication. Keep catalog.json and
definitions ordinary non-executable files. Preserve attribution and licensing.
Do not operate printer hardware or publish changes without owner authorization.
