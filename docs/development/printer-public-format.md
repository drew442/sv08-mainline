# Public printer definitions — draft 0.1

The owner-selected requirements are [the hardware page](printer-hardware-page-design.md)
and [definition sources](printer-definition-sources-design.md). On 2026-10-06 the
owner narrowed initial bundled choices to factory SV08 hardware; third-party
upgrades and add-ons will arrive through definition sources. No Funssor, Eddy,
CN3D or chamber kit is claimed as a complete built-in definition by this delivery.
Historical instance configurations and mappings remain compatible.

## Authoring and publication

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
