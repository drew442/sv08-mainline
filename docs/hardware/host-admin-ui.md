# Host administration and recovery UI implementation

2026-09-10. Workstation browser/GTK and disposable-state tests only. No printer
connection, live deployment, storage write or physical display validation.
[Decision 0010](../decisions/0010-host-administration-and-recovery-ui.md) records
the owner requirement, upstream choices and release acceptance criteria.

## Interfaces

The browser's **SV08 host** page provides Overview, OS images & updates,
Additional software, Host configuration and Recovery. It lives inside the
Cockpit authenticated administration console. There is no production HTTP server
or test bridge in the UI assets. The host's printer UI and OS administration have
different purposes; ordinary OS administration must not require a terminal.

The local **SV08 Recovery** screen uses large native GTK buttons. Tab and
Shift+Tab move focus, Enter/Space activate a focused button, and Escape cancels a
review. Touch and mouse activate the same controls. Restore/export selections
use lists from the verified backend, not typed device names. Failed status reads
leave diagnostics visible. The recovery controller can inspect a missing or
corrupt registry without creating it, requiring it to be writable, or borrowing a
running host's slot identity.

## Implemented and outstanding behavior

| Operation | Current implementation | Remaining release work |
| --- | --- | --- |
| Status and A/B state | Real state registry, running/requested modes, customization, journal, free space | Assembled target validation and job progress |
| Automatic update policy | Review/apply with strict booleans and stale-state checks | Scheduler and authenticated owner provisioning |
| Immutable/writable selection | Persistent requested mode; rejects a staged/pending update | Controlled idle reboot and assembled mode/config races |
| Host name | Validated single DNS label saved for next boot; current connection unchanged | Target networking and naming tests |
| Stage/arm/cancel image | Adapter calls existing signed/private staging + transaction + device backend | Reviewed board inputs; [authenticated browser upload](host-admin-upload.md) implemented offline; [durable offline jobs](host-admin-image-jobs.md) implemented |
| Additional software | Catalog selection and reviewed-operation UI contract | Reviewed catalog, dependency/space preview, actual APT adapter and customization reconciliation |
| Network/access configuration | Scope and unavailable-state explanation | Owner onboarding, persistent credentials/certificates, network forms and rollback |
| Recovery state inspection | Read-only, including missing/corrupt registry; no initialization | Physical block/filesystem diagnosis adapter |
| Recovery boot/restore/export | Native selection/review/apply; [archive exporter](host-recovery-export.md) and [verified pre-mounted export admission](host-recovery-media.md) with actual GTK/FAT tests | Trusted premount integration with the independent image, USB discovery, signed restore and physical export tests |

Unavailable operations are disabled and explain the gap; they do not silently
succeed. **This is not yet a complete no-command administration release.** In
particular, the current GTK screen cannot restore a real printer until the
independent recovery backend and board image composition are validated.

A requested mode or host-name change does not mutate the currently mounted root
or restart the printer. Automatic-update opt-out does not cancel an already armed
release. The UI presents cancellation as a separate reviewed action. Package and
storage operations cannot obtain arbitrary shell or device arguments from a form.

## Build integration

[UI dependency inputs](../../configs/host-os/admin-ui.json) keep host Cockpit and
recovery GTK dependencies separate. Cockpit `337-1+deb13u2` resolves from the
existing `20260901T000000Z` Debian security snapshot. GTK/input packages already
appear in the ordinary host baseline; recovery must contain an independent copy.
The [actual Cockpit integration](host-admin-cockpit.md) pins and measures the host
delta and exercises real isolated login and elevation. The [independent recovery
image](host-recovery-image.md) now pins its own complete closure, fits 512 MiB and
boots actual ARM64 GTK diagnostics with virtual input and accessibility; its
production media operations remain unavailable.

Run [UI staging](../../scripts/stage_admin_ui.py) after the matching core runtime
has been copied by the image builder. It defaults to inspection, accepts only a
build workspace, refuses mismatched runtime sources/existing UI output, and does
not install packages or enable a service:

```sh
python3 scripts/stage_admin_ui.py --work build/my-host --context host
python3 scripts/stage_admin_ui.py --work build/my-recovery --context recovery
```

Explicit `--execute` copies reviewed assets into those isolated roots. Host staging
adds `/usr/share/cockpit/sv08-host`, a conflict-checked Cockpit shell configuration,
the selected sudo bridge declaration and the fixed administration context. Recovery
staging adds a desktop session and an X11 launcher service, conditioned on a
recovery-image marker. The recovery builder must supply that marker and explicitly
enable the service only in the recovery root. No root, marker or service is added
to the current printer. The display launcher disables X11 TCP listening.

The native entry uses `/usr/lib/sv08/sv08_recovery_ui.py`. The host helper uses fixed
`/data/sv08`, `/run/sv08/boot.json` and `/usr/lib/sv08/admin-context.json` paths.
When reviewed release, update-policy, layout and environment inputs are present,
it constructs the existing device backend and upload adapter. That backend still
refuses non-deployable manifests and unidentified hardware. Recovery never enables
this host adapter as a workaround.

## Offline checks

- Python tests cover policy persistence, no writes on review, stale/edited review
  refusal, staged-update mode conflict, input rejection, absent backend, host-name
  validation and missing/corrupt recovery state without file creation.
- Image-controller tests use real private staging files/locks with a bootloader
  double: review → stage → arm → cancel; active/source state preservation;
  customization/non-deployable rejection; state recheck inside the transaction lock.
  These are not additional real-RAUC or hardware tests.
- Chromium tests use the real controller and a disposable state directory behind
  an explicit test-only Cockpit bridge shim. Keyboard navigation, Escape cancellation,
  policy persistence, cancellation after a previously confirmed dialog,
  requested/running-mode separation, touch navigation, disabled
  unsupported actions and a narrow viewport pass with zero uncaught exceptions.
- The recovery display systemd unit passes `systemd-analyze verify` inside the
  selected Debian ARM64 baseline using a disposable private overlay. No display
  service is started by that check.
- GTK under Xvfb renders at 800×480. Focus traversal, native confirmation/cancel
  callbacks and damaged-state presentation pass. Apply callbacks in that GTK test
  are explicit doubles; no bootloader is present. The workstation reported an
  absent AT-SPI bus; accessibility-service and assistive-technology validation
  remain required in the assembled recovery image.

Developer fixture commands (never a LAN service or printer installer):

```sh
python3 scripts/preview_admin_ui.py --work build/admin-ui-new --execute
xvfb-run -a /usr/bin/python3 tests/recovery_gtk.py
python3 -m unittest discover -s tests -p 'test_admin*.py'
```

The preview prints an ephemeral loopback URL. Its marked test bridge writes only
the new disposable state directory. Browser regression runner:
`tests/admin_browser.mjs CHROMIUM_BINARY FIXTURE_DIRECTORY FRESH_RESULT_DIRECTORY`.
Use the selected Node 22 runtime. The test needs a fresh preview because it changes
its policy. Close the fixture server when done. Screenshots/logs stay ignored under
`build/admin-ui-browser-v6/` and `build/admin-ui-preview-v3/`.

The 2026-09-10 UI staging reported 47,229 bytes for host assets/helpers and 29,670 bytes for
recovery assets/helpers before the export backend was added. Those figures exclude Python,
GTK, X11, Cockpit, fonts, kernel and firmware; they are not rootfs fit results.
Host-name publication preserves existing aliases in the staged hosts file before
changing the name, so an interruption leaves the old name resolvable. An injected
failure between those publications passes; physical reboot/network checks remain.

The [public evidence record](host-admin-ui-20260910.json) records scope. Before
release, validate production owner/TLS integration and disconnected-browser
jobs, complete 8 GB release occupancy, named-board recovery boot and attended HDMI touch,
keyboard-only, mouse, USB export and signed restore tests on the named profile.

The [2026-09-11 export work](host-recovery-export.md) adds a real archive backend.
[2026-09-12 media admission](host-recovery-media.md) connects the installed GTK
entry to an explicitly configured pre-mounted provider and preserves diagnostic-only
behavior without valid trust inputs. Production image/premounter integration and
physical USB tests remain required; boot/restore are still separate work.

[Image job evidence](host-admin-image-jobs.md) now records durable receipts, separate
worker supervision and browser reconnection. [Actual Cockpit tests](host-admin-cockpit.md)
now cover isolated authenticated helper sessions; production and physical
validation remain outstanding.

The image-job polling correction [preserves unfinished edits and selections](host-admin-image-jobs.md#independent-review-correction-preserve-unfinished-edits);
its independent-review history and browser dwell evidence are recorded separately.
