# Creator definition starter (draft 0.1)

Copy this directory into a public GitHub repository. Edit exact hardware scope,
sources, components and semantic endpoint bindings. Do not publish machine serials,
CAN UUIDs, measured calibration or executable plugins. These are factory SV08
reference examples. The explicit no-additional-check record illustrates a non-contributing
record; add a source-backed rule only when the hardware requires one.

Run `python3 scripts/printer_definitions.py index PATH` after editing and
`python3 scripts/printer_definitions.py validate PATH` before publication from a
checkout of sv08-mainline. File hashes/index are generated. Recommend a stable tag.
No printer connection or application approval needed.
