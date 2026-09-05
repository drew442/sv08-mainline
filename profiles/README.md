# Hardware profiles

Profiles identify supported or investigated hardware combinations. Stock is the
first target; modified electronics are part of the project scope. A JSON record
is metadata, not a flash configuration or a claim that the printer will operate.

The initial [stock profile](stock-sv08/profile.json) is research-only. Its unknown
values are intentional. The format is provisional until build tooling needs a
formal schema.

[Test printer 01](test-sv08-01/profile.json) records an owner-reported modified
bed/hotend and dual display setup on mostly factory electronics. Keep its
configuration and validation distinct from the stock reference.

Each future profile should describe host, mainboard, toolhead, transport, probe,
display, firmware targets, relevant source references, and validation evidence.
Use `null` for unknown machine-readable values. Store actual configuration only
after review; keep serials and calibration in ignored per-printer local files.

Use [the template](TEMPLATE.md) when adding a modified combination. A replacement
toolhead must not silently inherit stock pins, thermistor circuits, MCU targets,
or transport. Share common mechanics explicitly as implementation develops.
