# Public printer definitions — draft 0.1

The owner-selected requirements are [the hardware page](printer-hardware-page-design.md)
and [definition sources](printer-definition-sources-design.md). On 2026-10-06 the
owner narrowed initial bundled choices to factory SV08 hardware; third-party
upgrades and add-ons will arrive through definition sources. No Funssor, Eddy,
CN3D or chamber kit is claimed as a complete built-in definition by this delivery.
Historical instance configurations and mappings remain compatible.

## Compact author format (compact-1)

A modder supplies product identity and changed Klipper settings. Omit `kind` to use
compact format; `format_version` may be omitted or explicitly `compact-1`. Existing
rich0.1 definitions and catalogue/index0.1 remain supported.

```json
{
  "id": "funssor-cn3d-hotbed",
  "name": "Funssor CN3D heated bed",
  "version": "1.0.0",
  "extends": "sv08.factory.hotbed",
  "heater_bed": { "max_temp": 120 }
}
```

This is the owner's stated factory-equivalent configuration, not independently
verified manufacturer hardware. `max_temp` is Klipper's temperature shutdown limit.
An optional HTTPS `guide` cites the exact installation/product; optional category,
description, licence and sources provide additional detail. Defaults inherited
from factory hardware do not certify a replacement. PID/calibration stays local.

`extends` accepts any built-in definition ID, a same-catalogue definition ID, or a
list combining bases. Aliases: `sv08.factory.hotbed`→`sv08-main.bed_assembly`,
`sv08.factory.hotend`→`sv08-tool.hotend_assembly`, `sv08.factory.mainboard`,
`sv08.factory.toolhead_board`, `sv08.factory.printer`→`sv08.factory`. Other factory
presets use `sv08.factory.<preset>` (e.g. probe, stepper_x, exhaust_fan). For a kit
use `extends: ["my-bed", "sv08.factory.probe"]`. Missing/cyclic/deep bases and
conflicting component/connection ownership are rejected. No other repository or
mutable branch is consulted to expand inheritance.

Put a single Klipper section directly on the record, or use `configuration` for
several sections. Field values are typed JSON numbers, booleans, arrays or strings,
not executable Klipper text. Coverage follows the finite managed generator:

| Hardware | Compact Klipper section(s) |
|---|---|
| Bed/hotend/chamber | `heater_bed`, `extruder`, `heater_generic chamber_temp` |
| Temperature sensors | `temperature_sensor NAME` (sensor_type or temperature_mcu) |
| Motion/drivers | `stepper_x`…`stepper_z3`, `extruder`, `tmc2209 NAME` |
| Fans | `fan_generic NAME`, `heater_fan NAME` |
| Probe/filament/pressure input | `probe`, `filament_switch_sensor NAME`, `gcode_button NAME` |
| Outputs/LEDs | `output_pin NAME`, `neopixel NAME` |
| Display/accelerometer | `display` (uc1701 wiring), `adxl345 NAME` |
| Printer geometry/levelling | `printer`, `bed_mesh`, `quad_gantry_level`, `safe_z_home` |
| Heater verification | `verify_heater heater_bed` or `verify_heater extruder` |
| Boards/finite check-only rules | factory inheritance; explicit documented `advanced.mapping` / `advanced.behaviours` |

Heater `sensor_type`, `sensor_pin`, `pullup_resistor`, `min_temp`, `max_temp` route to
the associated sensor. Heater/motor/probe/fan fields use the supported typed field
registry; `heater_pin` and `switch_pin` map to their output/input connection.
Known sensor names or exact curve IDs are accepted; ambiguous names require the
curve ID. Optional settings outside the current generator are explicitly rejected;
compact authoring does not add arbitrary Klipper extensions. The authoritative
Klipper heater-bed reference is [here](https://www.klipper3d.org/Config_Reference.html#heater_bed),
with pinned supported fields in [the runtime registry](../../runtime/sv08_printer_fields.py).

New components specify `board` with an exact documented board ID and connector
name or known pin. Inherited connections retain their exact board scope. Raw pins
are checked against that mapping; MCU role, capability and collisions remain
validated. New motor wiring can use a documented `connector`, or Klipper step/dir/enable/UART
pins that together resolve to an exact documented motor channel. Inherited motor
channels accept matching individual pins; moving a channel requires all four pins. Board mappings require documented signals,
connectors and motor channels; advanced does not waive validation. Original SV08
chamber support retains its own chamber board, chamber_temp role and watermark
control. Unsupported boards/outputs remain unavailable.

`advanced` exposes existing typed components/connections, inputs, mapping,
behaviours, dependencies/conflicts, compatibility, printer settings and declared
gaps. Published PID gains, measured Z offsets, MCU identities, physical ratings
and calibration curves are prohibited universal defaults. They belong to local
advanced configuration. Unknown fields, raw macros, scripts and executable
extensions are rejected. See [the compact schema](../../schemas/printer-definitions/v1/compact.schema.json);
full runtime/creator validation checks more than JSON shape.

Expansion occurs once during source preview/import into the same validated rich
record used by existing composition. Author form and resolved base ID/version/SHA
are retained in `extensions.sv08.compact`. Selected snapshots and generated runtime
assets are pinned; generation never repeats inheritance against a later factory
catalogue. Raw authored file hashes stay in the manifest and immutable version
checks. A new expansion of an already selected version cannot silently replace
its snapshot. No publisher verification or physical commissioning is implied.

The downloaded starter uses compact examples. `tools/update_catalog.py` generates
the index/hashes and checks local inheritance; use the full creator validator
before publishing. Commit JSON as mode100644; a failed preview identifies any
executable catalogue/file and the `git update-index --chmod=-x PATH` correction.

## Authoring and publication

The **Definition sources** page provides **Download repository starter (.zip)**.
Extract it as a new repository root. It includes the examples below, a README and
`tools/update_catalog.py` to refresh local dependency and file hashes without a
printer connection. Full validation still uses the project creator CLI. The ZIP is
built deterministically during UI staging, then served as a static asset.

Copy [the creator starter](../../examples/printer-definitions/README.md) into a
public GitHub repository. Its `catalog.json` indexes each JSON file by ID, immutable
semantic version, relative path and SHA-256 of the exact bytes. Public files contain
hardware facts, their sources and reusable settings. They contain no controller
serials, CAN UUIDs, measured PID gains, custom instance curves or probe calibration.

From this repository:

```sh
python3 scripts/printer_definitions.py index examples/printer-definitions
python3 scripts/printer_definitions.py validate examples/printer-definitions
python3 scripts/printer_definitions.py bundle examples/printer-definitions > bundle.json
python3 scripts/printer_definitions.py preview examples/printer-definitions \
  --installation examples/printer-definitions/fixtures/installation.json \
  --definition sv08-bed --mode full
```

Preview exposes unresolved installation inputs and configuration gaps; it does not
contact a printer. The fixture intentionally lacks machine identities and motion
inputs. Publish a public repository URL, preferably with a stable release tag.
Users enter the URL once in Definition sources, review the publisher declaration
and resolved commit, then add the catalogue. This makes choices available without
selecting hardware or applying configuration. Branch movement is resolved to one
commit before any indexed files are fetched. Rename/ownership changes require
explicit readmission; failures retain the existing source.

## Contract

[JSON Schema Draft 2020-12 files](../../schemas/printer-definitions/v1/definition.schema.json)
cover the first draft contract. The directory `v1` identifies the initial schema
family; the wire format is `format_version: "0.1"`, not a frozen 1.0 format.
The runtime validator adds circuit, dependency and typed-setting checks and is the
same engine used by creator tooling. No remote schema is fetched.

Every record has `format_version`, `id`, `version`, `kind`, `name`, `category`,
`hardware`, `compatibility`, `sources` and `license`. Optional description, aliases,
calibration tasks, unresolved facts and namespaced descriptive extensions provide
context. Required unknown capabilities make a definition unavailable; they never
silently change its meaning. Extensions cannot contribute outputs.

Supported record kinds are `component`, `board`, `assembly` and `behaviour`.
Components contain semantic device names, existing supported device kinds, board
roles, typed settings and named endpoints. Connections bind an endpoint to a
source-qualified board scope, documented connector and capability. The signal is
derived from that board mapping. Contacts remain unknown where not documented.
Board mappings cannot embed component presets; assemblies express composition
through explicit dependencies. Common component data is independent of application
UI controls. New device kinds and unsupported GPIO families require a runtime
adapter and are reported unavailable.

Dependencies use ID, version and canonical-record SHA-256, plus an explicit source
for cross-source references. They never implicitly subscribe to another repository.
Installed selections additionally pin source identity and commit. Two sources can
use the same display name or local ID without shadowing each other or built-ins.
A missing dependency, cycle, incompatible version, conflicting ownership or pin
collision stops composition. Shared dependencies survive removal of one owner.
Distinct motors, fans and controller roles coexist within their respective cards.

Inputs are typed numbers, booleans, string choices, sensor curves or private
controller identities. Targets address semantic fields, defaults obey typed bounds,
and identity defaults are forbidden. Values and overrides belong to the instance.
Changes exposes effective values; component details disclose defaults, overrides
and sources and offer explicit reset. Updating catalogue availability does not
update selected versions. Selecting an updated definition explicitly preserves
field overrides for review and invalidates dependent calibration.

Factory adapters omit measured PID gains, physical motor ratings and probe Z
calibration. Uncalibrated heater defaults use watermark control; PID calibration
is a separate commissioning task. No stock calibration is claimed as measured
on the current printer.

The first behaviour capability is a **check-only**
`levelling.preconditions` hook. It supports `at_least`, `at_most` and
`within_range`, an explicit sensor and finite thresholds, provenance, and error
abort. It emits the project-owned `SV08_LEVELLING_PRECONDITIONS` macro; a process
must invoke this hook explicitly. It neither heats nor waits. An explicit `operation: "none"` states that a sample
contributes no additional check; an empty behaviour record is not equivalent.
Compatible checks compose into one deterministic hook, while contradictory
temperature ranges are rejected. Heating, cooling
waits, heat-soak choreography and publisher-authored raw macros are unsupported
capabilities. They must not be approximated by this hook. Factory definitions do
not invent a third-party levelling policy.

## State, privacy and limits

The source manager uses public GitHub API requests without credentials or printer
inventory. Indexed tree entries must be ordinary non-executable blobs; traversal,
links and submodules are refused. Explicit checking of a source and explicit
selection of an upgrade are separate actions. Disable, enable and removal affect
availability; saved drafts, inactive candidates and restoration snapshots retain
selected definitions and runtime assets for offline use.

| Limit | Value |
| --- | --- |
| Manifest or individual definition | 128 KiB |
| Fetched source data | 384 KiB |
| Definitions per source | 32 |
| Sources / accepted cache | 8 / 512 KiB |
| Dependency depth / JSON nesting | 12 / 24 |
| Object fields or array entries | 256 |
| Requests / fetch deadline / request timeout | 96 / 60 s / 10 s |
| Draft / persistent envelope | 128 KiB / 2 MiB |
| Generated configuration | 512 KiB |
| Managed snapshot storage / entries | 2 MiB / 96 |
| Complete-output validation | 10 s wall time, 8 s CPU, 256 MiB address space, 4 MiB per output file |

Updates publish through the existing Store/Budget exclusion and revision protocol.
Local bundles prove indexed bytes; GitHub acceptance re-fetches the exact reviewed
commit. Immutable-version violations are rejected, including versions retained
in draft and candidate snapshots. Shareable drafts omit controller identities and
custom text. Inactive configuration and diagnostic backups are separate private
exports. Browser storage receives no inventory or credentials.

## Managed application

Selections, inactive generated candidates, applied configuration and commissioning
are separate states. Save selections never writes `printer.cfg`. Live application
requires a complete saved full candidate, an exact fresh review, stopped managed
printer services, capacity reserves and complete-output validation.

Publication preserves unmanaged text and explicit include closure, detects duplicate
sections and exact byte drift including SAVE_CONFIG, writes an immutable managed
bundle, then changes one activation include. Files are readable by the SV08 service;
receipts and journals remain private. Restoration preserves original content,
owner, group and mode. Interrupted writes retain a journal and require explicit
reconciliation. No publication or restoration restarts services or invokes G-code.

The validator runs pinned Klipper `f0892d82b0f1c1228454f09eb508eddde2250f4b`
with file output and the matching simulated-MCU dictionary. Staging may supply that
exact dictionary with `scripts/stage_printer_ui.py --validation-dictionary PATH`;
its required SHA-256 is
`86665c7ba90587f09347af0001faf3681cc35819141b5c37c1f646e49a15125b`.
An absent/mismatched asset or unsupported startup/host-hardware extra refuses
application. No physical MCU is contacted. Parser acceptance establishes software
composition only. Hardware matching, calibration and commissioning remain separate.
Advanced custom text requires explicit section ownership and the same complete
validation; unsupported includes/startup behaviours fail rather than being ignored.

## Factory hardware vocabulary (runtime generator 7)

The finite `klipper.factory.v1` capability adds heater-controlled fans, digital/PWM
outputs, neopixels, UC1701 display controls, ADXL345 accelerometers, MCU temperature
sensors and pressure-contact inputs. Existing component kinds gain sourced driver,
sensorless-homing, probe-sampling, filament-delay and heater-verification fields.
Unsupported kinds, enum values, electrical capabilities and operational keys still
fail admission. The public format remains draft 0.1; changed built-in content uses
immutable version 0.2.0. Existing 0.1.0 snapshots retain their content and meaning.

Assemblies may carry finite `printer_settings` groups: `geometry`, `bed_mesh`,
`quad_gantry_level` and `safe_z_home`. These are typed data, never raw startup code.
Conflicting settings ownership refuses generation. New native sections are checked
through the same pinned complete-output validator; sensor-only mode remains
output-free and refuses a complete hardware assembly.

An instance plan can explicitly replace a pinned assembly dependency using its
`replacements` map. Every target carries source, ID, immutable version, digest and
commit, resolves from retained snapshots, and obeys the same depth/cycle/ownership
checks. Selecting a bed directly or through a creator bundle replaces that child
without discarding the full factory assembly. Inactive old snapshots remain for
restoration; source removal cannot silently alter selected components. Shared,
unchanged dependencies preserve local overrides and calibration.
