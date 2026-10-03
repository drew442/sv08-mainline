# Commissioning overlay software contract

This implements the [approved scope](proposal.md) and the six constraints in
[the accepted decision](record.json). It is an initial diagnostic A-only helper,
not a production backend, deployment tool or printer readiness gate. Retire the
helper when a production composition replaces this baseline. The custom gap is
initial-generation eligibility: upstream mark-good replenishes counters without
this project's state/identity restrictions. No bootloader policy is changed.

## Explicit installation and identity

The coordinator supplies `/etc/sv08/commissioning-target.json`, a regular,
root-owned 0600 file on the read-only root, bounded to 64 KiB. Its exact top-level
keys are `format_version` (1), `release`, `generation`, `disk`,
`fw_config_sha256`, `tools` and `dependencies`. No public device defaults ship.

`disk` has exactly `path` (canonical whole block-device path), `major_minor`,
`sysfs` (resolved `/sys/dev/block/<major_minor>`), `physical_bytes` (actual media capacity),
`image_bytes` (reviewed GPT image footprint),
`disk_guid`, and `partition_records`. The latter is the exact six-record result of
`sv08_gpt.inspect`: each record contains `number`, `name`, `partuuid`,
`offset_bytes`, `size_bytes`. The helper checks both GPT headers/arrays and their
CRCs, reserved SPL/environment regions, whole-disk sysfs size/identity, and root-A,
paired boot-A and data PARTUUIDs, partition numbers, starts and sizes on that disk.
The physical size and GPT footprint are distinct: a larger spare may carry the
factory-layout GPT backup at the original image end. Require positive integers
with image_bytes <= physical_bytes; compare sysfs size to physical_bytes and pass
image_bytes to the existing read-only GPT inspector. Never move/rewrite GPT to
force those quantities equal. The exact historical inspector validates both
headers' GUID agreement but does not return `disk_guid`. After its complete audit,
the helper reads the primary header's little-endian GUID locally, rechecking its
signature, length and CRC before comparing the reviewed binding. The historical
GPT module and its both-header/array CRC, collision and partition checks remain
unchanged. It checks the actual mounts: root and boot read-only, data writable. Synthetic
records are examples only; they must never be substituted for measured target facts.

`tools` has exactly `package` (`libubootenv-tool`), `version` (`0.3.5-0.1+b2`) and
`files` (absolute path to SHA-256 mapping). Both `/usr/bin/fw_printenv` and
`/usr/bin/fw_setenv` must hash to
`29d6d7b52afa4144a7f40bb9ca852c8058c0b68388904983ab076ac53d467ea0`.
Include the selected libubootenv `.so.0` lookup and `.so.0.3.5` implementation,
libc, zlib, YAML and ARM64 loader; all are required. The installed tool's symlink
and dependency lookup chain must be independently checked by the coordinator.
Version agreement and hashes are checked again on read-only files before mutation.
`dependencies` is the complete staged Python closure's absolute path/hash mapping,
including the new helper. Staging derives 18 modules through imports using the
historical APIs; missing/different modules refuse copied-target preflight.

The private `/etc/sv08/commissioning-fw_env.config` is also regular/root-owned
0600. Its bytes must match the reviewed hash and exactly these two lines, using
the configured canonical disk path (here **synthetic** `/dev/mmcblk9`):

```text
/dev/mmcblk9 0x400000 0x10000
/dev/mmcblk9 0x800000 0x10000
```

The helper has no user-supplied writer arguments, raw writer, hardware discovery,
RAUC configuration creation, authentication change, activation or reboot command.
Only the coordinator installs/enables the separately staged oneshot.
General integration may ship the inert Python module. The default integration
fixture proves it does not install the commissioning unit/private configs or an
enablement link. The service is outside `configs/host-os/systemd/*.service`;
only explicit reviewed overlay installation/configuration can execute the hook.

## Admission, health and mutation

The Store lock (nonblocking), existing `boot_admission`, and `Service.writer`
are acquired in that order and held through health, final revalidation, the single
write and readback. The standard `/var/lock/fw_printenv.lock` is left to each
selected tool invocation; pre-acquiring it around a subprocess would deadlock.
Supported writers share the project writer exclusion. This adds no new permission,
RNG or replay framework and does not promise exclusion against arbitrary raw writers.

The current canonical kernel boot UUID, prepared boot record, diagnostic
`deployable=false` release/schema, one uncustomized immutable A generation without
parent, no pending/trial, no failed-trial history and **no update.json of any phase**
are required. B registry presence, normal backend inputs, RAUC system config,
RAUC operation marker, active/transitioning RAUC, missing preparation, or loss of any
of the seven filesystem/command-line diagnostic masks refuses. History is never
removed to admit this helper. Existing production validators and masks are unchanged.

Health must remain exactly equal for five seconds, sampled at intervals no greater
than 0.5 seconds, followed by fresh final revalidation. A transient failure or
identity/environment change refuses rather than restarting the window. The helper
uses a 60-second deadline and signal timer; systemd has a separate 60-second start
limit, two-second termination grace, and no restart policy. Subprocesses have at
most three seconds or the remaining deadline, 32 KiB combined stdout/stderr and
no inherited environment/default config. Input JSON is bounded to 64 KiB.

Both 65,536-byte banks must have valid CRCs and terminated, unique ASCII variables.
All logical variables are parsed, not just the four policy variables. The full
tool dictionary must equal the selected raw bank dictionary, including
empty values, whitespace and embedded `=`. The previously saved eligible bank may
have different or missing non-counter variables; redundant banks are successive
snapshots. This corrects the earlier contract requirement that both banks agree
on every non-counter value. Only A order, B0 and A1/A2/A3 in **both** banks are eligible;
A0 refuses. Equal flags refuse as ambiguous. Incremental flag selection accounts
for 255→0 wrap and is checked against real tool-selected full output. For A3,
validation succeeds without invoking the writer or changing either bank, even
when the historical dictionary differs. For A1/A2, the only writer vector
is `/usr/bin/fw_setenv -c <reviewed config> BOOT_A_LEFT 3`. The target is fsynced,
then full health/identity, both CRCs and selected output are re-observed. The earlier
selected bank must be preserved byte-for-byte; the new selected bank must be A3,
with every other variable copied exactly from the pre-write selected dictionary.
The initially stale bank is the write destination; the original selected bank
becomes the preserved older bank. Readback requires both resulting non-counter
dictionaries to equal that pre-write selected baseline. An unexpected file/kernel
storage mode fails
closed; file tests do not establish physical MMC semantics or power-loss behavior.

## Interruption and storage limits

Under the locks, before health, a boot-bound record is atomically published and
fsynced under `/data/sv08/shared/logs/journal/commissioning-health/<boot_id>.json`.
Its fields are `format_version:1`, `boot_id`, `status`, and bounded `reason`.
Statuses are `checking`, `unknown-outcome`, `success`, `success-noop`, or
`failed-or-unknown`. Before invocation, `unknown-outcome` is durably published.
An existing record of any status refuses a same-boot restart. SIGKILL during health
or after mutation therefore cannot silently retry. Success resolves the unknown
status only after verified readback; no marker is deleted or printer-ready marker
created. If result publication fails, the earlier record remains authoritative.

Each record is at most 64 KiB; total retained files are at most 1 MiB. Admission
reserves 64 KiB of retained capacity and 128 KiB/two free inodes for atomic
publication; no prior history is rotated/deleted. Linked, oversized or unsupported
entries refuse. Full storage, lock admission or inability to retain the record
refuses without a writer invocation. Storage/lock failures before record creation
cannot retain evidence, but cannot reach the mutation either. Operator/coordinator
resolution of interrupted history is separate from this helper; it has no erase or
retry switch. Standard unit output is null to avoid unbounded duplicate logging.

## Exact overlay and preflight

[The staging tool](../../../scripts/stage_commissioning_host.py) defaults to a
nonmutating inventory. `--execute` writes only a new isolated output directory.
It never installs, enables, remounts, invokes the writer or refreshes administration.

Installed runtime and UI captures are checked against
`6064628ff06261a604aa13c52e17407b33f9f503` (`8c6f24f^`). Only the accepted TLS
state-directory/boot-permission deltas are taken from
`8c6f24f5a565cd08e43001414f643f55d5b1bb8b`; old Store semantics are retained. The state preimage and replacement retain
0755 for the existing /usr/bin/sv08-state executable symlink; boot retains 0644.
The absent pure-stdlib `sv08_rauc_bootloader.py` is staged unchanged from assigned
edit-start `1d1855719169f024b3d36f7e9bbe1fb4d5f28894`, without its service/backend.
The fixed admin context is exactly `{"format_version":1,"context":"host"}`.
Existing app.js, manifest, Cockpit shell config and Python dependencies are retained
and included as unchanged identity inputs. Historical HTML receives only the
wordmark/title delta; CSS gets the same palette as current-source staging.
Staging validates historical CSS against the immutable BASE revision, never
HEAD's current unthemed state, so committing the theme cannot invalidate the guard.
Current source retains its history controls. No feed timer is added to this overlay.

The artifact manifest contains file bytes/hash/mode/uid/gid, directory modes,
link targets/hash, preimages, unchanged inputs, dependency closure, revisions and
runtime bounds. Copied-target `check_target(root, manifest)` checks exact preimages
and unchanged files before an independently reviewed installation. The required `--deployment-preimages` input supplies exact coordinator-captured
stock Debian branding hash/mode or observed absence. Missing/unsupported captures
refuse staging. Captured unchanged runtime modules are required at staging too,
not assumed present; the coordinator supplied the complete historical whitelist. The cert-link preimage is a real empty 0755 directory; any content
or link conflicts. Coordinator must measure that assumption before installation,
preserve beforeimages, initialize the accepted real root-owned 0700 data certificate
directory, flush/hash installed artifacts and restore root read-only before health.
No certificate contents or credential material are part of the source inventory.

The synthetic artifact is 75,382 bytes, with at least 39,024 bytes of known
beforeimages. The isolated capacity report reserves rounded payload/beforeimages
plus the 1 MiB diagnostic allowance and reports free bytes/inodes. Actual target
capacity and retained beforeimage allocation must be remeasured; this is not a
factory storage/admission waiver. No image build or package installation is needed.

## Branding and evidence limits

Local navy/slate CSS, teal accents and an SVG/text SV08 Mainline badge use
`/usr/share/cockpit/branding/debian`, preserving os-release, PAM, sudo and behavior.
Provenance: [Cockpit 337 branding documentation](https://raw.githubusercontent.com/cockpit-project/cockpit/337/doc/branding.md),
pinned by the approved proposal, accessed there on 2026-10-03. No new network access
was used by implementation. No frameworks, external assets or layout redesign.

Real Chromium rendered both historical-overlay and current-source host HTML/CSS
at 1024×600 and 1440×900, including keyboard-visible focus, errors, disabled actions
and native confirmation with Cancel focused and Escape cancellation. Script routes
were intentionally blank and display state injected: these are **unauthenticated
visual fixtures**, not protocol/authenticated administration evidence. The continuation used the selected Cockpit 337 packaged login HTML/CSS/JS/fonts
from the coordinator-assigned board-host-refresh root. A localhost fixture injects
a synthetic environment and returns unauthenticated 401 without WWW-Authenticate
Basic, avoiding the browser's unrelated built-in auth prompt. Both sizes render
PF6 form, badge, branding, footer, errors, keyboard focus and disabled action;
measured normal-text contrast exceeds 4.5:1. These are static login assets served
by the fixture, not actual installed Cockpit lookup/authentication proof. Independent high delivery review and all named
physical boot/access/sensor checks remain coordinator-owned.


Ordinary tests are clean-checkout fixtures: test-owned temporary historical sources
are generated from immutable Git BASE using git ls-tree/show, and stock branding
metadata is synthetic. They do not require captured installed files or private
paths. Actual captured source/preimage agreement remains separate coordinator
proof. The real ARM64 test requires explicit SV08_SELECTED_TOOL_TEST=1 and an
absolute existing SV08_SELECTED_TOOL_ROOT; without opt-in it performs no tool-root
read, sudo or download. When enabled, point it to the assigned selected root; its
binary hash check still binds the selected implementation before invocation.
