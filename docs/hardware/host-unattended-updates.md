# Unattended A/B OS release delivery

Status: offline implementation; **not enabled on the test printer**. This
implements [decision 0017](../decisions/0017-unattended-network-os-updates.md)
through the existing signed RAUC bundle, [transaction](host-rauc-backend.md),
idle-admission and boot-health code. H11 and deployable-board review remain
required before any physical inactive-slot write.

## What this path can update

The goal here is to update the installed eMMC without removing it from the
printer or connecting the USB writer. Once a supported host image is booted from
the eMMC, RAUC can write only the inactive boot/root pair, keep the running pair
as fallback, and arm the new pair for the next boot. The signed feed can perform
that sequence automatically when the user has enabled automatic updates and
the existing idle and image-integrity checks pass. No user command or physical
interaction is needed to stage or arm that routine update; it becomes active
at the next normal boot. The updater does not force a reboot.

This is an A/B operating-system update, not a whole-device reflash. It does not
replace the GPT, U-Boot/SPL, redundant boot environment, recovery partition,
persistent data or MCU firmware. Initial provisioning or recovery from a damaged
boot chain remains a separate operation and needs a supported recovery image.
The current SD/NFS diagnostic can enumerate the installed eMMC, but its H10
probe opens the device read-only, and Beelink serves its NFS root read-only; it
is not an eMMC writer. The current board image and release-signing configuration
are not deployable, so neither the diagnostic probe nor the offline feed code
can safely be used to write the printer today.

The image includes `sv08-feed.timer` and `sv08-feed.service`. The service is
conditioned on `/usr/lib/sv08/feed.json`; the current image has no feed file or
release-signing trust anchor, so the timer cannot fetch or stage an update.
Release composition must install a reviewed fixed configuration and certificates:

```json
{
  "format_version": 1,
  "url": "https://updates.example.invalid/sv08/stable/",
  "channel": "stable",
  "ca_file": "/usr/lib/sv08/feed-transport-ca.pem",
  "signer_ca_file": "/usr/lib/sv08/feed-signers.pem"
}
```

The URL must end in `/` and use HTTPS. TLS validates against the fixed transport
CA; redirects may stay on that HTTPS origin only. The separate signing CA checks
the detached DER CMS signature in `index.json.p7s` over the exact bytes of
`index.json`. The index contains only `format_version`, `channel`, `sequence`,
`issued`, `expires`, `compatible`, `release`, `bundle`, `bytes`, and `sha256`.
Times are Unix seconds. The channel, exact board compatibility, monotonic
sequence, thirty-day maximum validity, bundle name/size and SHA-256 are checked
before intake. This signed index does not replace the separate RAUC signature,
verity payload and image-layout checks; those remain in the existing backend.
The release-signing key is kept offline. Test signatures use disposable keys.

`/run/systemd/timesync/synchronized` is required before checking expiry. This
marker indicates the system clock was synchronized by systemd-timesyncd; it is
**not a cryptographic time attestation**. A missing marker, earlier wall clock,
future index or expired index stops the check. The highest accepted sequence,
index digest and last checked time are persisted under `/data/sv08`, outside
either OS slot. A missing or damaged sequence file after initialization stops
updates for recovery rather than resetting replay protection. A new sequence is
recorded after signature and policy validation, before bundle download; it does
not claim a slot write happened. A matching sequence and exact signed-index
digest can retry an interrupted download or resume a `staged` transaction.
Reusing a sequence with changed signed metadata is rejected even when the bundle
hash is unchanged. An `installing`, `arming` or otherwise uncertain journal
blocks timer replay pending reconciliation.

The feed uses a private `/data/sv08/feed-bundles` intake. It accepts one exact
declared bundle, checks free space with the existing 768 MiB staging reserve,
and leaves the existing 512 MiB state-copy reserve to the transaction. The
bundle size is bounded by both the signed index and RAUC policy; no second
full-size temporary copy is made. A previously published file is reverified
after interruption. A killed download can leave a managed `.partial-*` file,
or a fully published bundle before its journal is created. The next poll
reclaims only correctly named, private partials and unreferenced digest files
while holding the state and staging locks. It retains the current index bundle
and any bundle referenced by a staged journal. Unknown files, unsafe partials
and busy/armed transactions remain fail-closed for reconciliation. A retained
artifact is deleted only when its matching transaction is terminal, before
admitting a newer release. Manual browser
upload remains separate. The transaction rechecks immutable mode,
customization, automatic-update opt-in, boot identity, state, target and idle
admission at staging and arming; it never requests a reboot. The UI displays
the last feed check as advisory status, while the transaction journal and
bootloader remain authoritative.

Offline checks use a local HTTP fixture only through test injection; the
installed fetcher accepts HTTPS exclusively. The fixed service and timer do
not expose a browser-controlled URL, keyring, executable or device path. This
custom feed shim can be retired if upstream RAUC gains equivalent signed
discovery, anti-replay, printer-idle admission and A/B transaction semantics.

The first combined signed-feed QEMU run reached actual RAUC installation and
wrote the disposable inactive slot pair, then failed the staging invariant
because stock RAUC changed `BOOT_ORDER` before the separate arm. An initial
rerun with the custom handler failed earlier because the QEMU guest could not
start `rauc.service`. Both were harness/design failures, not passing evidence.
The independent review and owner-authorized pre-disarm revision are recorded in
the [RAUC staging review](host-unattended-update-rauc-stage-review-20260926.md).
The helper journals pre-disarm, keeps the live source selected, restores the
previous target policy only while the journal proves RAUC was never called, and
leaves the target disabled after an uncertain install start.

The joined six-boot signed-feed/RAUC/health/fallback QEMU run now passes. It
performed A-to-B, confirmed B healthy, performed B-to-A after disarming A,
rejected an intentionally unhealthy A trial through all configured attempts,
and returned to B with the failed trial canceled. It verified the disposable
inactive pairs, environment-copy integrity and exact arm deltas, unchanged
primary/backup GPT and recovery partition, and a persistent user-data sentinel.
Its [machine-readable result and boot-log hashes](host-unattended-update-qemu-evidence-20260926.json)
record the exact assertions and limits. The harness models attempt consumption
using the real redundant environment but supplies each slot on QEMU's kernel
command line; it does not prove H616 SPL/U-Boot selection or physical behavior.
The existing independent
[trial-health QEMU evidence](host-unattended-update-qemu-health-support-20260926.json)
remains supporting-only. The board image is still non-deployable. A separate
deployable image, release trust anchors, full 8 GB image-budget check,
high-consequence review and physical H11 validation remain required. This does
not establish a whole-device eMMC reflasher; the SD/NFS diagnostic remains
read-only.
