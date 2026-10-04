# Printer hardware catalog and inactive candidates

This implementation is an offline software candidate with focused source, persistence,
staging and Chromium fixture evidence, pending independent delivery review and
installed acceptance. No board combination is certified compatible.
The separate `sv08-printer` Cockpit package uses the selected Cockpit 337 base1
API and the existing session authorization behavior. The host shell has one ordinary
navigation link. Installed authenticated second-package navigation remains a check.

Choose board references, enter each private MCU transport identity, acknowledge
the provisional reference, and add named connected devices. Forms show the
catalog's supported connectors and canonical pins. Choose inversion and digital
input pull-up explicitly. Analog temperature pull-up resistance is a separate
numeric field. Use the reference preset button only when deliberately selecting
that software default. The two factory presets also supply vendor-configured
min/max bounds, clearly distinguished from measured component limits. Factory thermal points are vendor DEFAULTs, not newly fitted
calibration; selecting one does not identify the physical thermistor or resistor.
Min/max temperatures, motor ratings, geometry and controls require explicit entries.

Save draft accepts incomplete settings. Review reports fields needed for its mode.
Sensor mode positively emits MCU transports, kinematics none, temperature sensors,
the two fixed factory thermistor definitions when selected, and empty-action
filament switch inputs. Output-bearing device selections block this mode. Full mode
requires CoreXY X/Y, four Z steppers, an upstream probe, bed, extruder, motor RMS
ratings/currents, sense resistance, addressing, direction and geometry. It keeps
Klipper heater verification and cold-extrusion protection. Automatic homing/start
macros, vendor pressure extras, arbitrary includes/text and pin overrides are absent.
The accepted printer-controls include remains separately owned and commissioned.

Review defaults to Cancel. Apply saves only an inactive configuration string in
feature-owned storage. It never touches live printer.cfg, services, MCU ports,
firmware or host state. Export is a local browser download; private identities are
not placed in URLs, localStorage, logs or catalog files. Import accepts only bounded
structured data, shows saved/imported values field by field, replaces the visible
forms, and requires explicit Save. Discard returns to the saved draft. Restore
loads the prior candidate's draft; review/apply is required again. Board change
requires confirmation and removes the affected devices and private identity while
preserving the other board and both saved candidates.

## Data and source audit

[Catalog](../../catalog/printer/catalog.json) contains four exact references and
[structured draft schema](../../catalog/printer/draft.schema.json) describes the
versioned envelope. The [catalog schema](../../catalog/printer/catalog.schema.json)
and runtime semantic checks reject mismatched counts, capabilities and fixed
factory definitions. Every selectable capability has an audited exact source line;
commented upstream reference channels are labeled as such. Catalog `kinds` is the runtime/UI field specification. Runtime
rejects unknown keys, kinds, pins and circuit roles; it uses canonical MCU role plus
GPIO for exclusive allocation. No electrical sharing rule is presently enabled.
Channel counts mean evidenced selectable channels only, not total board capacity.
Unknown connectors/contacts, electrical ratings, installed revision/match, MCU clocks
and bootloader offsets remain unknown. No spare pin is inferred from another board.

Primary inputs, accessed 2026-10-04:

- `upstream/sovol-sv08/home/sovol/printer_data/config/printer.cfg`, revision
  `a60644875f8c756d20b3828c9416518b414b5491`; named sections/options identify
  each selected signal capability and motor bundle.
- `upstream/sovol-sv08/Motherboard/MCU_PIN_definition.pdf`, page 1 (printed 23),
  and `Extra_PIN_definition.pdf`, page 1, same repository revision; drawing revision
  unknown. Rendered diagrams confirm selected connector labels. Main EXP2 drawing
  shows 3.3V while vendor aliases label 5V: no EXP assignments are enabled here.
- `upstream/klipper/config/generic-bigtreetech-octopus-v1.1.cfg` and
  `sample-bigtreetech-ebb-canbus-v1.2.cfg`, revision
  `f0892d82b0f1c1228454f09eb508eddde2250f4b`. Octopus is non-Pro only; Pro v1.1
  may inadvertently enable a heater. Samples are reference mappings, not a complete
  connector/contact or circuit inventory. No firmware clock/offset is selected.
- `upstream/klipper/klippy/extras/thermistor.py`, same Klipper revision: common
  component curves and 4700-ohm software default. Vendor hotend uses 11500 ohm.

Exact source SHA-256 values are recorded per board, including both drawings.
Factory hotend points: (25,110000), (100,7008), (220,435). Factory bed points:
(25,100000), (50,18085.4), (100,5362.6). These preserve the vendor settings;
physical limits and sensor identity remain unknown.

## Contributor recipe

For an existing device kind, add a board JSON entry with a unique ID, exact role
and variant, primary source revision/path/page/date/hash, individually sourced
signals/capabilities and motor bundles, supported connector labels, unknowns,
reserved flags and channel scope. Add component data only with its curve origin
and supported input circuit. Do not copy a nearby board's capacities or ratings.
The data-extension fixture in `tests/test_printer_configuration.py` adds a board
without runtime/UI changes and exercises generation. Add a positive config fixture
and negative unsupported-pin/collision fixtures for the new entry. A new kind or
sharing rule requires a bounded code change and independent approval/review.

For example, duplicate an evidenced reference entry in a disposable test catalog,
set `id` to `contributor-fixture`, retain its provenance and change the test draft's
board ID. The existing form fields and generator work unchanged. This test example
is not a new public hardware compatibility claim.

Custom Python fills the structured catalog-to-Klipper and generation-local private
publication gap. Prefer upstream config sections. Retire these adapters when an
upstream supported mechanism provides equivalent behavior, preserving structured
export migration and fault tests. Shared architecture records remain coordinator-owned.

## Persistence and staging

The fixed helper uses `/data/sv08`, `/run/sv08/boot.json` and the existing verified
`/run/sv08/printer_data/config` view. Store lock precedes the feature lock; both use
nonblocking acquisition. Registry, boot slot/release/generation, nontrial mode and
view target must agree. Unexpected links inside feature storage refuse. The single
0600 state envelope under a 0700 `config/printer-hardware` directory atomically
publishes draft/current/previous together, with fsync and directory fsync. The wider
configuration tree's ownership/modes remain untouched.

Save uses expected revision CAS. Review binds draft, revision, current candidate,
catalog, generator version, mode and boot context. Apply regenerates under lock.
Disconnect, edits, cancel, Stop/logout and context changes invalidate UI review;
unknown save acknowledgment requires reload before retry. A prior review cannot
reapply after a publication. No permission/replay ledger is introduced.

Limits: 128 KiB structured draft/import, 64 devices, 512 KiB generated text,
4 MiB feature footprint including temporary publication space, and 32 directory
entries including abandoned temps. Both allocated blocks and sparse expansion are
counted. Existing Store copy allowance and shared reserve are retained. Current
Budget is used when present; historical Store uses its existing copy/reserve API
with a feature-local projected-write check. Corrupt/unknown schema originals are
preserved; unsupported stored schema is available through status for diagnosis.
The initial group-writable workspace ancestry failure is retained in the original
handoff. Current Store/Budget and historical Store now run under the assigned safe
fixture ancestry without bypassing that guard. Small disposable fixtures use explicit
zero state reserve and 8MiB copy allowance through the existing Budget constructor;
production defaults remain unchanged. Low block/inode capacity is injected only
through statvfs results for fault tests, with actual state files and publication code.
The production768MiB floor is independently asserted to refuse165MiB capacity.

`stage_printer_ui.py` defaults to dry-run against a reviewed root and exact supplied
hash/mode/uid/gid file and directory closure. Imports are traced with Python AST
through the actual existing Store, so current Budget is required only when that
Store imports it. No imported helper is refreshed. It adds only the new package/catalog/helper and the one navigation
line, preserving existing Shell and helper closure. Its restoration checks all
afterimages before restoring. Use it after host/core staging on a fresh root, or
against the captured historical installed closure for an overlay. It does not
install or activate. Recovery/diagnostic assemblies gain nothing automatically.
`stage_admin_ui.py` permits only the additional named Cockpit package; its existing
core checks remain. Coordinator installation must verify the captured uid/gid and directory-mode
inventory against the deployed target and measure physical root/data capacity.
4 MiB per configured generation fits within existing factory 8GB state allocations;
it is not a new reservation, nor proof of installed free space.

## Local evidence and remaining checks

Focused catalog, validation, current and historical Store CAS/current/previous,
killed-writer, low-block/low-inode capacity, corrupt/schema refusal, privilege,
import, independent-process CAS and boot-context tests pass without skips. Both
Store APIs have actual disposable generation-copy/rollback evidence. Exact
additive/fresh staging and restoration tests include before/after mode and uid/gid
checks, directory tampering, missing dependency and preimage refusals.

Pinned dual-MCU file-output parsing passed for sensor and full fixtures; generated
bytes remain identical to the original passing parse fixtures. A further full
fixture composed once with the separately owned print-controls include also
passes. Only its fixed gcodes path was substituted for that disposable parse.
Generated full machine sections intentionally retain separate controls ownership:
before H06, include the accepted controls file once after the persistent gcodes
directory exists. No control section, macro, service or activation is reinvented.
Fixture motor ratings and limits are explicit test values and make no physical claim.

`tests/test_printer_browser_fixture.py` runs a loopback Cockpit transport/session
shim with actual Store/Budget storage under a safe private root.
`tests/printer_browser.mjs` uses the existing CDP WebSocket shim and supplied
Chromium with an explicit no-sandbox flag and a closed-loopback proxy for nonlocal
traffic. Journeys at1024x600 and1440x900 cover incomplete save/reopen, connector/pin
and factory preset forms, keyboard Escape/default cancel, touch reload, import
before/after and discard/save, review/apply inactive, exports, prior restoration,
lost acknowledgment reconciliation, board-change clearing, Stop/disconnect/logout,
no localStorage and unchanged live configuration. Screenshots were inspected for
layout and horizontal overflow. The shim is excluded from production payload.

The exact selected Cockpit337 `packages.py` and `superuser.py` hashes match the
package lock. The actual packaged Packages/Manifest/Package classes loaded both
packages and served both HTML paths under their CSP. The packaged manpage defines
Shell as a relative URL to a top-level component. The ordinary relative link
resolves from the host package to the printer package; no Shell replacement is
needed. Both manifests retain identical existing sudo bridge declarations, with
no new authentication policy. This establishes offline package/source behavior,
not a real authenticated Cockpit337 or installed ARM64 journey.

Remaining acceptance is independent high delivery verification and the
coordinator's reviewed named-host installation/authenticated ARM64 journey,
including root restored read-only, unchanged masks/live configuration and physical
root/data capacity. No hardware operation, printing or compatibility claim follows.
The catalog intentionally exposes only audited source channels: no complete
connector/electrical inventory is asserted and unavailable pins cannot be assigned.
