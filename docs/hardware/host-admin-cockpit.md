# Actual Cockpit host console integration

The selected Debian Cockpit `337-1+deb13u2` login, PAM session and sudo bridge run
in a disposable ARM64 QEMU guest. This is offline authentication and finite-helper
integration evidence. Its synthetic Store/boot context runs on a writable guest
root without A/B devices or update adapters; it does not prove immutable mounts
or raw slot operations. It does not activate a printer, provision an owner, validate
production TLS/LAN access, or certify an assembled image or factory-capacity fit.
The accepted [UI decision](../decisions/0010-host-administration-and-recovery-ui.md)
and [release checklist](host-os-tasks.md) retain those requirements.

## Integration and authorization

[UI staging](../../scripts/stage_admin_ui.py) writes Cockpit's supported
`[WebService] Shell=/sv08-host/index.html` configuration and the
[SV08 package manifest](../../ui/host/manifest.json). It refuses existing
configuration, existing output, symlink destinations and unexpected Cockpit
packages before writing. It does not install/enable services or change sudo grants.
Only the ws/bridge packages and their dependencies are selected; stock shell,
terminal, storage, system, and PackageKit pages are excluded. An administrator's
existing OS powers are unchanged by this appliance navigation.

The manifest reuses the selected upstream shell's sudo declaration:
`sudo -k -A cockpit-bridge --privileged`, with packaged `cockpit-askpass`.
The baseline's sudo executable must retain its root ownership/setuid mode and
Debian PAM/policy. There is no production NOPASSWD rule or credential fixture.

[Session controls](../../ui/host/session.js) use the selected internal
`cockpit.Superuser` proxy at `/superuser`: Current/Bridges, Start/Answer/Stop,
and Prompt. This API is version-sensitive; expected methods/properties and the
sudo bridge must be present or the page refuses administration with a diagnostic.
Authorization is explicit. Password fields and prompt text are cleared after
answer/cancel/failure; passwords are not stored. Stop immediately closes local
operation authority while waiting for the real bridge to stop. A Stop failure
keeps local authority closed and tells the owner to log out.

Authorization changes discard pending reviews. Delayed review/status responses
cannot revive an earlier authority state, and a submitted apply keeps its own
reviewed arguments while awaiting its result. Authentication never confirms or
replays a review. The helper still uses Cockpit's required privileged spawn;
UI flags are not an authorization boundary. The server-side helper also checks
its effective uid and fixed installed context.

## Package and source provenance

The [package lock](../../configs/host-os/cockpit-packages.json) records the
`20260901T000000Z` Debian and Debian-security snapshot URLs, all nine new archive
hashes, versions, download sizes and declared Installed-Size values. The APT
simulation against the selected baseline reports nine new packages and no
upgrades. The delta is 2,633,920 downloaded bytes and 10,872 KiB of declared
installed payload. Neither figure is an assembled slot or recovery fit result.
The [derived runtime closure](host-cockpit-closure-20260912.json) retains 121
packages and 357 dependency edges with no unresolved dependency. It follows
Depends/Pre-Depends, includes all installed satisfying alternatives/providers, and
excludes Recommends/Suggests. Each package has exact archive metadata from the
pinned indexes. [The derivation tool](../../tests/cockpit_closure.py) reproduces
it from the existing baseline status/indexes and hash-checked delta archives.
The preparer retains the complete resulting installed-package inventory and
measures actual root file bytes and content/ownership/mode fingerprints.

Sudo `1.9.16p2-3+deb13u2` is already in the baseline. Its exact snapshot archive,
dependencies, hash and installed sudo executable, sudoers.so plugin and sudo PAM comparisons are included in the
lock. The corresponding baseline inventory is tied to
[baseline build evidence](host-ab-build.md). `cockpit-askpass` is part of the
selected bridge package; no stock cockpit-system package is installed.

Primary packaged sources, accessed 2026-09-12, are recorded by path and SHA-256
in the lock: cockpit-system's `usr/share/cockpit/shell/manifest.json` and
`shell.js.gz` (including decompressed source hash), cockpit-bridge's
`cockpit/superuser.py`, `cockpit/packages.py`, `usr/lib/cockpit/cockpit-askpass`,
and cockpit-ws's `etc/pam.d/cockpit`. Cockpit-system is extracted solely as
provenance. The selected cockpit-ws `usr/share/man/man5/cockpit.conf.5.gz`
documents the Shell option. Package units remain unmodified.

## Reproduce without a printer

Use an already prepared selected ARM64 baseline and the exact downloaded delta
archives named by the lock. Preparation runs a pinned offline APT simulation; no network download or floating
update occurs. Root is required only for private mounts, synthetic guest
ownership and namespace creation; nothing installs into the workstation root.
A fresh output directory is mandatory. The fixture uses approximately 1.3 GiB of
allocated storage for a sparse 2 GiB ext4 filesystem plus its private overlay.

```sh
sudo unshare --mount --pid --fork --net python3 tests/cockpit_fixture.py prepare \
  --baseline "$PWD/build/host-ab-baseline-v1/rootfs" \
  --intake "$PWD/build/cockpit-intake-337" \
  --work "$PWD/local/cockpit-proof" --execute
sudo unshare --net --pid --fork python3 tests/cockpit_fixture.py boot \
  --work "$PWD/local/cockpit-proof" --execute
```

Preparation defaults to inspection without `--execute`. It verifies archive
hashes, creates a private overlay, installs only the fixed delta with service
activation inhibited, stages matching production runtime/UI, and creates private
synthetic users. It retains unmodified packaged PAM and sudo policy, adding only
the synthetic administrator to the guest's existing sudo group. Private runtime,
proc and device mounts are unmounted before copying the root into ext4. It rejects source/output overlap and provisioned baseline users before executing
chroot commands, checks all three required namespaces, and checks the source
baseline fingerprint again after unmounting.

The guest uses the baseline's exact distro kernel **and baseline initrd**; the
separate A/B QEMU initrd contains a persistent-partition hook and is unsuitable
for this single-root fixture. First boot verifies the prepared image hash and
requires a private, owned, regular, single-link image with the expected size.
Reprepare after a guest has modified the image; this utility has no unreviewed
resume or block-device target mode. QEMU runs inside private PID/network
namespaces with `restrict=on` and only namespace-loopback port 19090 forwarded.

In another terminal, join that namespace with a local Node 22 runtime and Chromium:

```sh
fixture_pid=$(sudo cat local/cockpit-proof/namespace-pid)
sudo nsenter -t "$fixture_pid" -n /path/to/node tests/cockpit_browser.mjs \
  "$PWD/local/cockpit-proof" /path/to/chromium
```

Wait for the guest's console login prompt before starting the browser check.
Stop the boot command after testing; its signal handler terminates QEMU and
removes the namespace pid file. It records equality checks for workstation identity
files and Cockpit unit state without publishing their private contents or hashes. The fixtures are private ignored files: retain
sanitized reports and remove synthetic credentials/browser profiles and generated
images after use. No source root or existing generated image is an output target.

## Evidence and limitations

The [2026-09-12 execution record](host-admin-cockpit-20260912.json) records
ordinary uid 1001, unelevated administrator uid 1000 and elevated uid 0; all
actual authentication/helper cases pass. Six private log/evidence files, the
guest journal and captured browser console/errors contain no synthetic password
or Basic-credential encoding. Password inputs/prompt state and browser storage
checks pass. Guest cleanup preserves workstation identity files and Cockpit unit
state, stops QEMU and removes its namespace pid file.

The measured fixture delta is 11,428,664 regular-file bytes over the current
source baseline, including staged runtime/UI and fixture-only changes. This
per-path logical measure includes boot and APT indexes and may count hardlink
aliases more than once. It is distinct from the older baseline report's `du`
measurement and is not a filesystem-capacity certificate. Controller/image-job
checks (37), staging checks (8), fixture target checks (4), all three existing
browser suites, and the full actual Cockpit suite pass. The source baseline's
full content/mode/ownership fingerprint agrees before and after preparation.


The [browser suite](../../tests/cockpit_browser.mjs) exercises real bad/ordinary/
administrator login, wrong sudo password, cancellation, uid proof, Stop denial,
status/review/jobs, cancelled/stale/confirmed helper operations, delayed authority
transitions, excluded direct URLs/package discovery, logout cookie invalidation,
and authenticated reconnect to persisted policy. API-absence and failed-Stop
cases are explicitly controlled browser faults, separate from real auth evidence.

Selected-root `systemd-analyze verify --man=no` checks packaged unit validity;
`--man=no` skips unavailable manual rendering, not service checks. Actual full
QEMU systemd executes packaged Cockpit socket/session/web-service units and
unchanged PAM. User-mode ARM64 chroot was not used as authentication evidence:
its host binfmt POF flags cannot faithfully preserve setuid sudo credentials, and
its session attempt stalled. No host binfmt or PAM changes were made to bypass it.

Custom code fills the missing bounded appliance shell/session integration and
isolated test harness. It does not replace Cockpit authentication. Retire or
update the version-sensitive proxy integration when an upstream supported API
provides the same explicit authority lifecycle; retain these regression cases.
Production account persistence, reset/onboarding, TLS identity, LAN policy,
independent recovery closure, actual uploads, hardware and release acceptance
remain open in the existing checklist.
