# Unattended A/B OS release delivery

Status: offline implementation; **not enabled on the test printer**. This
implements [decision 0017](../decisions/0017-unattended-network-os-updates.md)
through the existing signed RAUC bundle, [transaction](host-rauc-backend.md),
idle-admission and boot-health code. H11 and deployable-board review remain
required before any physical inactive-slot write.

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

Remaining release work: install an actual signed feed and trust anchors, verify
the complete 8 GB image budget and real RAUC installed-service journey in a
disposable ARM64 VM, then obtain the independent high-consequence review and
physical H11 evidence. The current diagnostic image remains non-deployable.
