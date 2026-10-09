# Cockpit software management evidence — 2026-10-09

## Delivered behavior and source

Source implementation commits ca27f544d760989afdd9673d4a59312d33014f9a and
e01c253b8810af6204a010583b797e9c22092093 and
96da0a2e5a7c4d5a13fde41467bc1f4e1de60f8a provide the dedicated Software page,
fixed Nano/htop/tmux/vnStat catalog, trusted APT dependency/download/storage
preview, reviewed durable systemd jobs, explicit vnStat service settings and
private customization compatibility report/export. Writable boot mode, pending
image state, package locks, reserve space and atomic printer idle admission gate
package/service changes. Removal preserves conffiles and user artifacts. Reports
retain customization blocking; they are not restoration bundles or validated
derived images. This meets the first reconciliation allowance in ADR 0004.

## Native and browser checks

From the candidate worktree:

- `python3 -m unittest discover -s tests -p test_software_admin.py`: 26 passed
  (4.244 seconds). Reviews bind state/inventory/source hashes; immutable admission,
  changed inputs, durable/idempotent jobs, finite history, service intent, policy
  preservation, unknown acknowledgment, report protection and storage rejection
  are covered. A real child process ignoring TERM is killed before admission
  restoration. The injected partial fresh-install failure creates the actual unit
  path and asserts disable runs while the lease is held, before admission exits;
  the job remains unknown/customized without replay. Legacy installed Store
  compatibility uses the same shared Budget reserve/lock and passes a metadata
  job without replacing the state module.
- `python3 -m unittest discover -s tests -p test_software_ui.py`: actual disposable
  Chromium fixture, one test passed (0.769 seconds), covering loading/authority,
  dependencies/space review, cancel/apply, failure/lost response, resume, service
  effects, export, stale navigation/authority and 390/1024-pixel layouts. Cockpit
  transport is mocked in this fixture.
- `test_host_integration.py`: 3 passed; `test_stage_admin_ui.py`: 18 passed. Catalog,
  runtime and worker staging are included. Package-policy (2), service-admission
  (4) and data-budget (2) targeted checks also passed during implementation.
- `node --check ui/host/software.js`, Python compilation and `git diff --check`
  passed. No gitlink/submodule, lockfile or executable-mode changes.

The independent targeted reviewer reproduced a timeout descendant defect and
confirmed its correction with the real Apt.run/Admission path. Package children
must exit before printer services can resume. The reviewer also identified and
assessed service enablement/stop and partial-postinst failure corrections. This
is targeted evidence; workflow completion uses the self-validation route.

## Actual ARM package evidence

Disposable Debian 13 ARM64 QEMU (kernel 6.12.107+deb13-arm64, APT 3.0.3,
systemd 257.13-1~deb13u1) executed five reviewed vnStat 2.13-1 jobs through the
actual production systemd template: install inactive/disabled, enable active,
disable inactive, enable active again, then remove while active. All five worker
results were success/ExecMainStatus 0; daemon absence, exact policy bytes/mode
0750, conffile/user-artifact hashes, absent leases, private 0600 jobs/exports and
preserved customized/activation-blocked state passed. Guest JOURNEY_PASS,
fixture shell status 0 and QEMU exit 0 were observed; no VM remains active.

The actual tested backend SHA-256 is
`4fd38c993c9770ab28f0365e1e4f45c77479beeaba8c12b95d612cbd5a8bc045`,
captured with all fixture inputs. This is not silently relabelled as the final
source: the later failure-only service cleanup and legacy Store/Budget fallback
have separate native checks and source assessment. The final fallback preserves
the existing Budget object for the current Store used in the ARM journey.
The separately fetched public Debian vnstat_2.13-1_arm64.deb (118248 bytes,
SHA-256 `56b329824f3c85287fd1a494c82b1c09b828ceb0c25ccedd07c1b9e7291c5842`)
confirms `/usr/lib/systemd/system/vnstat.service`; its hash is not a measurement
of the guest's cached archive.

Final integration receipt SHA-256:
`52d2c2396751462bc96a200b99fd764408bf8374285662b67223013b25f10265`.
The successful run took 978.99 seconds. The same-lineage cumulative conservative
runtime is 1664.43/2400 seconds; generated data is 606035968/805306368 bytes,
including retained prior attempts and temporary data allowances. Earlier limited
attempts exposed oversized APT caches and too-short emulated waits; failed or
unfinished receipts are not passing evidence. Cache files are now disabled for
preview commands; no limits were reset by new overlays or cleanup. A transient
host-side diagnostic tail edit was restored before execution; final input hashes
match, and the integration receipt discloses it.


## Installed controls and actual Cockpit evidence

The exact bounded eight-asset installation and later one-backend compatibility
repair were independently assessed before execution. The original assessment
input hash is `27d0092fbb91c26cc00ea0a46c034223220dbf45fd6242cae06bf8d686424385`;
repair input hash is `a2775ef01b5d2798bbe67361f8fba9fe93f8a726b5c8d79bd19efc2badd9bcdf`.
Both installers returned success, preservation true, package_change false and
service_restart false. Root/boot read-only, existing boot/config, network,
identity/access and diagnostic service masks were checked. The initial installed
browser failure identified a deployed Store version predating its budget property;
the compatibility correction preserves the installed state module and explicitly
uses the same shared allocation lock/reserve. Failed browser receipts are retained
separately; the final fresh journey is the passing result.

Actual Cockpit HTTPS with the existing persistent CA/IP SAN, PAM and sudo passed:
four-item catalog, real immutable install dependency preview with Apply disabled
and cancel, actual systemd metadata report completion/download, unchanged catalog,
requested mode/customized flag, repeated navigation/resume, usable Network and
preserved managed Mainsail No login. No real printer package/service change,
network/name/reboot mutation or output activation occurred. Compatibility reports
are private metadata; credentials, raw override contents and private identities
were neither exposed nor published.

Final installed postcheck verified all eight final asset hashes and all 46
original preservation hashes, unchanged boot/config/network/masks, root/boot
read-only, immutable mode, loaded worker and completed report. The one-asset
repair also preserved the other seven control hashes (53 checks total).

Final backend SHA-256: `160d2f2ac1f77efff8d2e21b5b7848f4f6d9d599d8c74c80c18afd15812e84cc`.


## Boundaries

No printing, heating/motion, MCU session, physical power-loss test or flashable
release acceptance is claimed. The printer remains in its existing immutable
diagnostic state; real package/service changes were tested only in disposable
Linux. The catalog uses configured trusted metadata, not arbitrary user package
commands or repository changes. Image activation remains blocked for customized
slots pending a validated derived image. APT is not an atomic filesystem transaction;
uncertain operations remain visible and are not silently retried.

Private receipt SHA-256 references (raw private artifacts are not published):

- `installed.json`: `1dbebf16b2d0f08dbdf22f9fd195a085295cbc910ea5b8f85b53cad98c1af07a`
- `repair-execution.json`: `0add4774d474c70d30d3af0f712d423145ebaf2339c6a220fd36e01c44d50943`
- `browser-result-final.json`: `c4aeba24baab8853edb3508c8aa937fbc775c53d8c70b2ef538b998767bc1cc2`
- `tls-proof.json`: `515fac7c86ec8a5ed4275383eb88c8806f5ffd037d24af266fb97b0ccfcde54b`
- `installed-state.json`: `8fe800c145030fbe458e1ee33d1108a53b118fb7509ff20f4baa61099a8dc406`
