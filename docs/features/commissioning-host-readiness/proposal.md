# Commissioning host: dependable normal boot and usable administration

Kind: fix/improvement. Author: coordinator, informed by separate planner and
source researcher. Date: 2026-10-03. Owner requested creation and completion of
this goal, then a simple SV08 Mainline Cockpit theme.

## Problem and intended outcome

[Fresh installed intake](intake.md) demonstrates the exact gaps: the accepted
H12 diagnostic image boots A, but consumes attempts without ordinary-boot
confirmation; Cockpit TLS fails on read-only /etc, its fixed admin context is
missing, and password login is not configured. Host Klipper package integrity,
revision/helper and installed ARM64 sensor-only file-output parsing pass. Only one
MCU currently enumerates. Do not infer why or claim current paired readiness.

Deliver a bounded commissioning baseline: normal installed boots replenish only
this healthy initial A slot; owner SSH and authenticated themed Cockpit work and
persist across two reviewed restarts; both MCU identities/revisions are reconciled
and a private input-only configuration is prepared. Sensor accuracy, physical
input transitions, output commissioning and printing follow separately.

This is not a deployable release, signed update composition, complete A/B failure
qualification or proof of long-term DRAM reliability. H12 stays complete. No RAM
handoff, anti-forgery/replay permission mechanism, cold-capture work or deferred
automatic maintenance launch/return is reintroduced.

## Narrow normal-boot change

Add an explicitly staged, diagnostic commissioning oneshot, separate from the
accepted trial coordinator. Current `sv08_boot_health.run` only calls real health
and mark-good for a matching transaction trial; idle does neither. Its installed
entry also requires RAUC status/config absent here. Production backend validation
correctly rejects deployable=false. Preserve all these production contracts.

The new helper applies only to an explicitly configured initial immutable A-only
baseline: exact diagnostic release, deployable=false, current kernel boot ID,
prepared boot/registry/generation identity, A only with no parent generation,
no customized/writable state, no pending/trial, **no update journal of any phase**,
no last_failed_trial and no normal backend composition. It must retain all seven
diagnostic masks, inactive RAUC and no RAUC operation marker. Never delete state,
logs or history to make the baseline applicable. This scoped hook is removed or
becomes inapplicable when a later production/update composition replaces it.

Bind root, paired read-only boot and writable data to the reviewed six-partition
GPT and common actual disk; verify environment offsets fit the leading reservation.
Private device identifiers/configuration remain outside public defaults. Validate
both redundant environment copies and tool-selected values. Reuse existing state,
boot and RAUC writer exclusion in compatible order; hold exclusion through health,
final recheck, single write and readback. No new locking/permission framework.

For five stable seconds within a bounded deadline, check boot/state/mount identity,
prepare service, masks and environment. No MCU, Wi-Fi lease, printer.cfg or heating
is required for OS health. Require A-only order, B0, A1/2/3; refuse A0 rather than
revive an exhausted slot. If A3, validate and do not write. Otherwise use standard
libubootenv fw_setenv once to set only BOOT_A_LEFT=3; no raw environment writer,
order change, B reset, dispatch change or synthetic transaction marker.

Success requires tool-selected A3, both CRCs valid and all other logical variables
unchanged. The older valid bank may retain its previous counter. Failed/unknown
write, timeout, readback or flush outcome is not success; retain same-boot failure
so a service restart does not silently retry. No automatic reboot or fallback.
No ordinary printer os-health-ready marker is granted by this diagnostic helper.

The pinned U-Boot bootmeth decrements/saves before loading the slot; RAUC's U-Boot
mark-good similarly replenishes a named counter. Relevant selected sources:
U-Boot ece349ade2973e220f524ce59e59711cc919263f `boot/bootmeth_rauc.c`, RAUC
4fb7c798d6ae412344fb8f8d310d773046af3441 `src/bootloaders/uboot.c`, and
`runtime/sv08_rauc_bootloader.py`. Keep independent action review for actual writes.

## Existing repairs and simple theme

Reuse the accepted TLS correction at 8c6f24f: real root-owned 0700 certificate
storage under /data and the supported link from /etc/cockpit/ws-certs.d; preserve
existing nonempty/conflicting content by refusing replacement. Apply only the
necessary boot/state initialization delta to the exact installed base, without a
broad runtime refresh. Restore the fixed host admin-context.json using the accepted
schema and verify matching installed UI/helper behavior. Backend-only operations
remain unavailable where their required composition is absent.

Add restrained SV08 Mainline branding to the login page and existing host UI,
using local CSS/text/vector assets, clear focus/disabled/error states, adequate
contrast and responsive 1024x600 plus desktop layouts. Preserve action labels,
confirmations, default cancellation and all RPC behavior. No external fonts,
network assets, new JS dependency or replacement of upstream authentication.
Use Cockpit 337's actual supported branding lookup; do not assume later /etc
branding support. Reapply the theme deterministically in staging. Primary source:
[Cockpit 337 branding](https://raw.githubusercontent.com/cockpit-project/cockpit/337/doc/branding.md),
accessed 2026-10-03. Existing installed HTML gets only the reviewed branding delta;
do not mix new behavioral UI controls with its older helper. Current repo UI keeps
its accepted behavior and matching staging inventory.

The owner sets a password through a prepared private terminal step; do not request
or publish the password. Existing owner-key SSH and sudo/PAM policy are preserved.
Observe real authenticated page/status, elevation, Stop and logout/relogin without
applying a host operation. This is basic installed account access, not a new
onboarding/credential management product.

## Artifact, ownership and deployment

One implementer owns only these new paths and the narrow referenced edits:
`runtime/sv08_commissioning_health.py`,
`configs/host-os/commissioning/sv08-commissioning-health.service`,
`scripts/stage_commissioning_host.py`, `tests/test_commissioning_host.py`,
`configs/host-os/cockpit-branding/` (CSS/vector assets), `ui/host/style.css`,
branding-only `ui/host/index.html`, narrow branding staging/inventory changes to
`scripts/stage_admin_ui.py` and `tests/test_stage_admin_ui.py`.
Do not edit trial/backend/state/boot behavior; the overlay carries the already
accepted TLS delta applied to exact known installed inputs. If unavoidable new
runtime semantics or dependencies appear outside these paths, return the exact gap
for coordinator reconciliation, not an unreviewed broad refresh. The coordinator
owns feature records, deployment scripts/private bindings, all Git and hardware.

The isolated staging tool defaults to dry-run and produces a deterministic exact
file/link/mode/hash inventory, expected preimages and helper dependency closure.
Its inputs include reviewed existing installed non-secret source files and private
binding config. Never enable commissioning globally through existing runtime/unit
globs, change diagnostic builder/finalizer checks, mark the image deployable or
alter release/boot scripts/kernel/initramfs. A small explicit overlay is preferable
to another full reimage. No new daemon, package or scheduler is required.

After independent software verification, a fresh exact-operation review covers
identified eMMC, preimages, artifacts, recovery and root ro→rw→ro installation.
Install only reviewed owned paths, preserve beforeimages, flush and verify, restore
root read-only before helper execution. Leave B/recovery/boot/media, credentials
(except owner-set password), data generations and printer masks intact. Root source
changes are recorded as this commissioning overlay, not rewritten historical image
evidence or a supported immutable release. Stop on partial installation/unknown
outcome; SD is sufficient recovery. No automatic repeat/reboot.

## Acceptance and task split

### Software task (offline)

- `baseline`: A1/A2 stable initial baseline causes exactly one A3 write; A3 no-op;
  final selected readback and unchanged other environment/state/masks. Test wrong
  boot/release/generation/device/GPT/mount/config, CRC/selection errors, A0, B/order,
  writable/customized state, every journal phase, failed-trial history and mask loss:
  all refuse without writes. Include mid-window changes and actual lock contention.
- `uncertainty`: prepare/health/deadline failures and errors before/after write,
  timeout/readback/CRC failure preserve truthful unknown outcome and prevent silent
  same-boot retry. No reboot, no printer readiness marker, no production-backend
  relaxation. Existing transaction/boot-health/bootloader regressions pass.
- `overlay`: exact installed dependency closure, deterministic dry-run/staging,
  conflict/preimage checks, existing TLS initialization and preservation, fixed admin
  context; default diagnostic assemblies do not enable the new hook. Exercise real
  selected libubootenv redundant selection/write on disposable regular-file storage,
  including older-bank preservation; no hardware proof is inferred.
- `theme`: real browser renders login and host-page branding at desktop and 1024x600;
  keyboard focus, status/errors, disabled actions and confirmation remain visible.
  Source/staging inventories match. No behavioral/UI protocol change.
- `regression`: targeted affected suites, source/JSON/local Markdown/whitespace and
  indexed-gitlink/lock checks; full diff independently reviewed at high effort.

### Installed task (hardware)

- `boots`: exact reviewed initial helper operation then one normal restart and one
  HW-667 full-off/on, no automatic retry. Distinct boot IDs, A-only prepared initial
  state, expected attempt consumption/replenishment, selected A3/B0 and immutable
  root/data/masks after each. B/recovery unchanged. Finite trial policy untouched.
- `access`: authenticated SSH and owner-set browser login/elevation/status/Stop/
  logout/relogin work; public SSH/TLS fingerprints and harmless persistent data
  survive those same two transitions. Do not publish secret keys/passwords. A login
  screen/HTTP200 alone is insufficient. Record explicitly unavailable functions.
- `sensors`: exact current host package/helper match retained full MCU revision;
  reconcile both physical by-id devices and current firmware without flashing or
  outputs; private no-output temperature/input config passes installed file-output
  parsing and is prepared inactive for H05. No general printer service activation.

## Human dependencies and limits

Use H02/H04/H05 in the existing [coordinated queue](../../hardware/coordinated-human-tasks.md).
Owner provides current physical facts before resets/power-dependent MCU queries,
performs a private password step and real login, and makes the second MCU available
if required. Do not ask for cable removal; HW-667 owns authorized resets. Physical
sensor/circuit identity, reference temperatures, switch operation, heat/motion and
first print remain later commissioning. Continue software work while these wait.
No new spending, licensing, requirement waiver or MCU flash is proposed.
