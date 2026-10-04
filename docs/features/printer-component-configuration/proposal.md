# Printer hardware configuration in Cockpit

Kind: feature. Date: 2026-10-04. Author: coordinator, informed by separate
Sol6.1/medium planner and sensor-source researcher. Independent approval pending.
Owner intent is recorded in [owner request](owner-request.md).

## Problem and intended outcome

The installed Cockpit host page has working authentication/administration but no
structured printer hardware configuration. Private Klipper files require manual
editing. Existing profiles are source/evidence inventories, not executable board
catalogs. Deliver a real installed **Printer hardware** page: choose a mainboard,
choose its connected devices and their connections, choose a toolhead board and
its devices, review validation/results, save a private draft, generate and apply
an **inactive candidate**, and export/import the structured configuration.

The user should not need to edit JSON or know raw MCU pin names for documented
connector defaults. Advanced pin details remain visible and editable within the
board's documented capabilities. Every board/component entry has provenance;
unknown values remain visible. Selecting a board does not attest which board is
physically installed or select MCU clocks/flash offsets/firmware.

Before/after evidence compares absent workflow with actual authenticated
board/device selection, persistent draft, generated config, review/cancel/apply
and reload. No printing or performance claim follows. Fine calibration is deferred;
use default component curves, including clearly named Sovol factory defaults.
The independent source research establishes that the existing custom definitions
are exactly vendor factory values, not newly tuned curves. Do not reinterpret the
owner's request as requiring an invented generic replacement sensor.

## User flow

1. **Boards:** mainboard and toolhead sections, board/revision dropdown, transport
   and private MCU identity, documented-reference versus installed-match status.
2. **Connected devices:** cards beneath each board for axes/motors/drivers,
   bed/hotend heaters, temperature sensors, fans and probe/filament inputs.
   Select component type/preset, then connector; show connector and rendered pin,
   direction/inversion/pull-up and the relevant electrical/temperature fields.
   Common fields first; advanced details expandable. No arbitrary config editor.
3. **Review:** show missing values, incompatible connections, resource collisions,
   default origins, changed settings and generated Klipper text. Distinguish
   syntactically valid candidate from physical commissioning evidence.
4. **Save draft** preserves incomplete selections. **Review candidate → Apply**
   saves a complete generated candidate in feature-owned storage, explicitly
   inactive. Cancel is the default. Export the draft or generated text; import a
   bounded structured draft only, show differences, and explicitly save it.
5. Reopen after browser disconnect/relogin and retain the draft/current candidate.
   Keep one prior configured candidate for restoration through review/apply.

Changing a board explicitly confirms and clears its affected pins, connectors,
polarity/electrical overrides and dependent assignments. Preserve the previous
saved candidate and unaffected board; never remap by connector index/name.
Changing a component clears incompatible dependent settings and invalidates review.
Use keyboard-accessible forms/focus and responsive 1024×600/desktop layouts.

## Architecture and extensibility

Use supported separate Cockpit package `sv08-printer`, a fixed finite JSON helper,
and one ordinary navigation link from the custom `sv08-host` shell. Preserve its
Shell selection and existing host RPC protocol. Reuse selected Cockpit base1 and
existing session behavior; no new authentication, sudo policy or daemon. If a
bounded source/runtime check disproves support for second-package navigation,
record the exact issue before choosing the smaller supported alternative.

Versioned declarative `catalog/printer/` board/component JSON and schema supply
UI fields and generator validation. No executable catalog plugins or user-supplied
templates. A contributor adds data, primary source references and positive/negative
fixtures for an existing device kind without changing runtime/UI code. A new
kind/resource-sharing rule is an explicit small code extension. Add a contributor
recipe and example. Do not modify pinned upstream or introduce dependencies.
Custom code fills the catalog-to-Klipper gap; retire it if upstream gains an
adequate supported equivalent, preserving structured exports and migration tests.

Initial useful choices:

- Sovol original SV08 mainboard and Extra_MCU reference mappings, sourced from
  pinned vendor config and published drawings. Unknown drawing/installed revision
  stays unknown; connector names only when actually documented.
- BigTreeTech Octopus **non-Pro** reference from pinned
  `generic-bigtreetech-octopus-v1.1.cfg`, and EBB reference from
  `sample-bigtreetech-ebb-canbus-v1.2.cfg`. Preserve exact revision/variant exclusions
  and upstream warnings. These are selectable documented candidates, not tested
  compatibility. No Octopus Pro substitution and no inferred MCU clock/offset.
- Named Sovol factory hotend/bed curves, and supported pinned Klipper Generic3950,
  EPCOS100K and ATC Semitec choices. Standard PT1000 may be included only with its
  distinct documented input circuit requirements. Display each curve's origin.
- Parameterized stepper motor/TMC2209, bed/hotend assembly, fan, probe and filament
  input options. Do not invent motor SKU ratings, heater watts or safe defaults.
  Populate configured reference values only with their correct evidence labels;
  they are distinct from measured limits and explicit user values.

A board has named MCU-local signals, connector/contact mappings where documented,
capabilities (ADC, digital input, output, step/dir/enable, driver bus), reserved
pins, channel counts and explicit sharing rules. Validate canonical MCU+GPIO
identity rather than alias text. Reject conflicting allocations, incompatible
roles, missing bus addressing/CS, capacity overflow and reserved pins. Never use
`duplicate_pin_override`. Separate digital pull-up flags from analog resistance.
Board selection does not copy old machine calibration or silently choose polarity.

Temperatures must be finite min<max and respect known component limits. Motor
current fields distinguish RMS and peak; missing rating/sense-resistor facts stay
unknown. A saved draft may be incomplete. Candidate generation requires all fields
needed for the selected output mode; physical evidence gaps are clearly reported
and do not masquerade as measured compatibility. Explicitly selected reference
values can generate a **provisional inactive candidate**; physical activation still
needs the existing commissioning checks. Do not require users to complete heated
calibration merely to save/export a useful default-curve sensor candidate.

## Persistence and generation

Store private machine data beneath the active generation's owned
`config/printer-hardware/` directory through the existing verified configuration
view. Resolve the actual boot/registry/generation, allow the trusted existing view
symlink, reject traversal or unexpected links inside owned paths. Keep serials,
private settings and backups out of public catalog, URLs, localStorage and logs.
Files0600/private directory; do not change ownership of the wider config tree.

Use existing Store exclusion before a feature lock, bounded acquisition and atomic
publication. Bind Save to expected draft revision (stale-tab refusal). Bind Review
and Apply to the exact draft/catalog/generator/mode/current-candidate revision;
revalidate under lock. A normal content/revision hash is sufficient identification,
not a permission/token system. Edits, cancel, privilege loss, logout/disconnect or
context changes invalidate review. Unknown acknowledgment reconciles current
revision before any retry. Refuse incompatible/trial/unknown generation context.

One draft, current complete candidate and one previous complete candidate suffice.
Proposed bounds:128KiB draft/import,64attachments,512KiB generated bundle,4MiB total
including publication space; account for shared-data reserves using accepted APIs.
Corrupt/unsupported state is preserved and reported, never replaced with defaults.
No-space/interrupted publication preserves the old complete candidate. Unknown
catalog/schema can be viewed/exported for diagnosis without silent migration.
Generation copies/rollback use existing config persistence rather than global state.

Sensor-only generation uses a small positive allowlist: explicit MCU transports,
kinematics none, temperature_sensor with selected default curves/pull-ups/bounds,
and optional approved empty-action input sections. Factory custom thermistor
sections are allowed only for the two fixed sourced factory definitions. No heater,
stepper, fan, output-pin, motion probe, macro or arbitrary include in this mode.
Use a dedicated generator; do not strip heaters out of a printing config.

Full inactive SV08 candidate generation supports the existing CoreXY/four-Z
geometry, explicit axis/endstop/probe choices and chosen component sections.
Incomplete required geometry/current/control/protection facts produce field
blockers, not an invented runnable file. Preserve upstream heater protections;
no automatic homing/start macros or restoration of vendor pressure-probe extras.
Schema-owned deterministic generation must reject names/value injection and raw
arbitrary Klipper text. Parse complete fixtures using pinned Klipper file-output
and matching MCU dictionaries. That proves syntax, not hardware compatibility.

**Apply never overwrites live printer.cfg, unmasks/starts a service, resets the
host/MCU, flashes firmware, or actuates hardware.** Display “Candidate saved —
inactive” and a clear commissioning handoff. Actual sensor-only consumption is a
separately reviewed temporary session; output activation follows H06. Existing
manual configuration remains untouched. Structured import is data-only, not an
archive or arbitrary printer.cfg parser. Configuration and MCU software pairing
remain separate concerns across image A/B.

## Staging and installed acceptance

Provide deterministic fresh-root staging and a narrow exact-preimage additive
overlay. New package/helper/catalog and the explicit host navigation delta only;
reuse the actual installed pre-Budget helper closure, not current-main assumptions.
Do not broadly refresh installed runtime/UI. Extend unexpected-package inventory
only for this named package. Keep recovery and diagnostic assemblies inert unless
explicitly staged. Record payload, dependencies, root/data capacity and beforeimages.

Offline browser journeys can use controlled fixtures, clearly labeled. Actual
installed ARM64 helper/package and authenticated Cockpit journeys must be observed
on the named host after independent software verification and exact installation
review. Reuse valid underlying A/B persistence evidence; test this feature's actual
Store/copy/rollback/schema behavior on disposable generations. Repeating a physical
A/B or full VM boot campaign is not a prerequisite for this small addition.

## Acceptance and task split

| ID | Environment | Required evidence |
| --- | --- | --- |
| catalog | offline | Sourced revision-qualified board/component catalog, visible unknowns/default origins, schema and contributor extension fixtures, exact primary pin/capability audit. |
| validation | offline | Meaningful collision/capacity/polarity/circuit/current/temperature/injection/size failures and board-change invalidation, no automatic risky override. |
| generation | offline | Deterministic sensor-only output allowlist and full complete SV08 fixtures parse under pinned Klipper; incomplete mode blocked; protections and previous files preserved. |
| persistence | offline | Actual Store/view context and generation-copy behavior; CAS/stale review, interruption/no-space/corrupt import/unknown-ack/schema downgrade preserve previous complete state; bounded footprint. |
| browser | offline | Board/device dropdowns/forms/pins, save/reopen, board change, review/cancel/apply inactive, export/import/restore, privilege transitions, keyboard/touch at1024×600 anddesktop; no JSON editing required. |
| staging | offline | Exact fresh/overlay inventories and historical installed API closure; inert recovery; no broad refresh; existing host page/RPC/session regression and size report. |
| installed | hardware | Named host real authenticated custom-Shell navigation, package/helper save/reopen/review/cancel/apply inactive/export/import/Stop/logout; correct catalog and defaults, persistent generation storage; root restored ro, masks/inactive printer.cfg unchanged. |

Tasks: `software` owns catalog/runtime/UI/staging and offline checks; `installed`
depends on independently accepted software and covers actual usability. One
implementer at a time, Sol6.1/medium for cross-component design, separate high
verifier for publication/concurrency recovery, separate exact installation reviewer.
Coordinator owns shared records, Git, deployments and human queue. Planner is not
approver/verifier. No new authority, spending, scheduling or licensing decision.

Proposed implementation ownership: `catalog/printer/**`, `runtime/sv08_printer_*.py`,
`ui/printer/**`, one link in `ui/host/index.html`, narrow named-package staging
changes, `scripts/stage_printer_ui.py`, corresponding tests and contributor guide.
Existing state/admission/printing-service behavior must not be changed without
an identified gap and bounded reconciliation. Shared records/ADRs remain root-owned.

## Human dependencies and scope limits

Use existing H01/H05/H06 in [coordinated tasks](../../hardware/coordinated-human-tasks.md).
Current sensor models/physical ratings and input associations may remain unknown;
record those honestly while implementing and saving provisional candidates.
BLE chamber readings support cold ambient sanity only. Physical switch/probe
resting→operated→resting observations require owner action. Heat/motion and fine
calibration are separate. UI delivery must proceed while those physical checks wait.
H12 stays complete; no RAM maintenance, permission anti-replay, cold capture or
deferred automatic launch/return is reintroduced. No new product-layout permission
is required: independent delegated approval reviews this concrete scope.
