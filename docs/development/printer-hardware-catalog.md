# Printer hardware catalog and inactive candidates

Independent software and installed delivery verification passed on test-sv08-01;
see the [installed evidence](../features/printer-component-configuration/installed-evidence.md).
The workflow creates inactive candidates. No board combination is certified compatible.
The internal `sv08-printer` asset/helper package uses the selected Cockpit 337 base1
API. Its panel is composed into the shared host shell with one sidebar, header and
authorization session; section navigation retains local drafts. The old separate URL
redirects into this shell. See [shared-panel design](printer-cockpit-panel.md) and
[installed integration evidence](../features/printer-cockpit-integration/installed-evidence.md).

Choose board references, enter each private MCU transport identity, acknowledge
its provisional status, then choose a human-readable **Documented component**.
Preview its defaults and exact source lines before **Use provisional reference
defaults**. This adds unsaved typed settings with suitable generator names, such as
“X axis motor / TMC2209” → `stepper_x`; raw section names are unnecessary for
reference choices. Custom device forms remain available. Saved cards expose the
available documented defaults and origins; edited settings remain explicit draft
selections and are not asserted to equal their reference.

SV08 choices cover factory bed/hotend sensors, bed/hotend assemblies, six mainboard
motors with TMC2209, part/exhaust fans, filament input and tool probe. Octopus
non-Pro and EBB v1.2 provide their exact supported sample components, including
commented sample inputs. Assemblies add their named sensor dependency together.
Duplicate names, occupied pins and existing sensor dependencies refuse the entire
addition without overwriting any user setting. To combine with an existing sensor,
use the custom forms and choose its association explicitly. Board changes still
confirm and clear only the affected board's devices and private identity.

Reference polarity is the configured pin marker (`!` / `^`, or its absence),
**not physically measured polarity**. Reference thermal bounds, PID gains,
rotation distances, current, microsteps, UART addresses and sense resistance are
source-configured software values or explicitly named pinned parser defaults.
SV08 Z references preserve upstream `gear_ratio: 80:12` alongside the documented
rotation distance; no new effective-distance calibration is created. Vendor
sensorless X/Y virtual endstops and actions are not translated into guessed GPIO
endstops. Probe z offset and motor RMS ratings are not preset; missing values keep
the full draft incomplete. Physical circuit/resistor identity, safe electrical
limits and firmware clocks/offsets remain unknown. Factory curves retain the vendor
point sets, not new calibration. The curve dropdown retains common pinned Klipper
options; the separate pull-up/bounds button is an explicit reference selection.

All generated drivers are TMC2209. `run_current` must be positive and at most
**2.000 A**, as required by pinned `tmc2209.TMCCurrentHelper` →
`tmc2130.MAX_CURRENT`, and must not exceed the explicit owner motor RMS rating.
This software maximum never certifies a physically safe current. Missing ratings
stay unknown and block full generation; incomplete drafts can still be saved.

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
structured data and the revision actually loaded in that tab. A stale tab must
reload before importing; it cannot adopt a newer unseen revision. A successful
import shows that exact saved/imported comparison field by field, replaces the visible
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

For an existing device kind, extend a board's declarative `presets` array without
runtime/UI changes. Each preset has a unique lowercase `id`, a human-readable
`label`, bounded uncertainty `notes`, and a `devices` bundle. Each device supplies
`name`, existing `kind`, typed `settings`, and a `sources` entry for every setting.
Sources inherit board path/revision/access-date/hash unless explicitly overridden;
each field records exact `line`, `section`, `option`, original source `value`, and
its finite `transform` (`number`, `pin`, `invert`, `pullup`, `curve`, `text`,
`connector`, `association`, or `software-default`). These labels describe provenance,
not executable transformations. Runtime copies only typed settings; no template,
include, code or plugin is evaluated. `association` names a sensor in the same
bundle. Source defaults from upstream parser code carry their own path/revision.
Do not supply `current_rating_rms`, calibrated probe `z_offset`, unknown ratings,
firmware facts or newly fitted curves as defaults.

Add positive default-selection and exact source-line fixtures, plus missing-origin,
unsupported-pin, dependency/name and collision negatives. The contributor fixture
adds a named EPCOS reference option using its exact pinned sample origin without
runtime/UI edits. For a new board, retain unique ID, exact role/variant, primary
path/revision/page/date/hash, sourced signals/capabilities and motor bundles,
connector labels, unknowns, reservations, counts and channel scope. Do not copy a
nearby board's capacities or electrical ratings. A new kind or sharing rule still
needs a bounded code change and independent approval/review.

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

Status returns a deterministic loaded identity binding the saved draft, revision,
current candidate, catalog revision, generator version and boot context (slot,
release, generation, operating mode and boot ID). Every subsequent finite helper
operation requires that identity from the tab's last successful status. Save,
restore, import and reference-default preparation additionally require integer
revision CAS. Under Store then feature exclusion, mismatch refuses before draft
publication, import comparison, preset preparation or candidate generation. Equal
revisions after generation copy/rollback do not permit writes from the old context.
Local edits and candidate-mode selection retain the loaded identity; they never
refresh or rebase it. Explicit reload obtains a new identity and permits explicit
edits. Review additionally binds its output mode; Apply retains that review check
and regenerates under lock.
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
Store imports it. No imported helper is refreshed. Fresh composition adds the package/catalog/helper
and compiles the printer panel into the existing Shell; historical overlays use exact
finite UI transformations while preserving helper closure. Supported staging and
restoration share root exclusion and check file/directory metadata and membership
before mutation. Its restoration checks all afterimages before restoring. Use it after host/core staging on a fresh root, or
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

Subsequent independent high software verification and the named-host authenticated
ARM64 journey passed, including read-only root, masks, inactive configuration and
capacity. The offline evidence below retains its original scope. No printing or
hardware compatibility claim follows.
The catalog intentionally exposes only audited source channels: no complete
connector/electrical inventory is asserted and unavailable pins cannot be assigned.


## Bounded F1–F3 repair evidence

Focused regressions cover two independent Store sessions and two actual Chromium
tabs: B changes 105→100; A imports its identical old 105 draft and is refused,
without revision promotion, overwrite or “No changes” comparison. After reload,
A sees the exact 100→105 comparison and may explicitly save; later writes still
invalidate Save CAS. Native browser forms exercise factory sensor defaults and
friendly X-motor/TMC2209 defaults, unknown motor rating, incomplete save/full
blockers and duplicate preset refusal. The Cockpit transport remains shimmed.

Pinned Klipper file-output parsing accepts the 2 A boundary with source Z gearing
and rejects deliberately supplied 3 A and 4 A configurations. Local validation
refuses these currents before generation. Original unchanged positive sensor/full
bytes retain their prior passing parser evidence. These are focused implementation
checks; later independent review and installed authentication passed as linked
above. Physical commissioning remains separate.

## Loaded-context F2 repair

Focused regressions reproduce the failed review's revision1 A→B copy and its
revision3 divergent A/B overwrite using actual current Store/Budget and historical
Store. Stale Save, restore, import, preset, review and apply refuse with unchanged
envelope bytes. Boot ID, operating mode, catalog, generator, saved draft and current
candidate changes also invalidate equal-revision requests. Explicit refresh and
subsequent edits/import/save remain possible; revision CAS remains mandatory.

The native Chromium journey switches the fixture's actual Store generation while
the tab retains its loaded status, exercises all stale preparation/write controls,
then refreshes and explicitly edits/saves/reviews/applies an inactive candidate.
The shim records that every operation carries the identity from its last successful
status. This is ordinary content/context consistency, with no nonce, permission
token or replay ledger. Existing publication, capacity, parser and staging code
retain their prior evidence; this repair does not establish independent acceptance
or authenticated installed Cockpit behavior.
