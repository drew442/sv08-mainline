# Installed-eMMC recovery staging: offline result and physical handoff

The running-host adapter in `scripts/live_h616_recovery_stage.py` is prepared for
the installed **spare** eMMC. Its default `inspect` operation opens the whole
device read-only and compares the signed policy with the current MMC controller,
one card's CID and type, exact capacity and device number, GPT, partition-five
PARTUUID and the mounted ext4 source. It reports a hash of the CID, not the CID.
The factory eMMC remains stored. No physical stage, environment change or
full-eMMC reimage has been performed by this feature.

`stage`, `arm` and `activate` are separate root-only `--execute` operations.
They require a private canonical 0600 target policy, signed job and verification
key, an artifact classified `h12-attended-candidate`, and a separate persistent
journal. Stage checks the reviewed artifact and original recovery-script hashes,
free space (FIT + original script + 16 MiB reserve) and live identity at file
write boundaries. A physical mutation first enters a private mount namespace,
so an external unmount/remount cannot redirect subsequent filesystem writes.
The signed NFS/claim source must name an address absent from the running host;
the running OS root may itself be on the target eMMC before the RAM handoff.
It preserves the original script before installing the FIT
and selector. Arm writes the redundant environment through a held block-device
descriptor, journals and syncs each write, and reads both copies back. Activate
rechecks the signed job, target, staged files and both environment copies before
publishing the one-shot marker. A partial journal cannot automatically retry.
The RAM writer and NFS source retain their independent admission and readback
checks described in [the handoff design](../design/unattended-emmc-reimage-handoff.md).

Offline tests used a disposable 32 GB sparse file with a loop block device,
synthetic sysfs identity and mounted ext4 partition-five loop. The success path
reached a marker only after both environment copies read back armed. Interruption
cases after original-script preservation, FIT copy, selector replacement, and
each redundant environment write left no marker; rearm and activation refused
the partial journals. Read-only inspection worked with a read-only ext4 mount;
mutation admission refused it. Wrong CID, MMC type, size, `dev_t`, PARTUUID,
mount source, GPT CRC, an ambiguous card and an unmounted recovery filesystem
were refused. These tests do **not** establish current printer identity, eMMC
durability, bootloader selector behavior or network availability.

Reproduce with `sudo unshare -m python3 tests/offline_h616_live_admission.py
--execute --work local/NEW-UNIQUE-NAME` (add `--fault` for each named fault below)
and `sudo unshare -m python3 tests/offline_h616_live_mount_isolation.py`.
The 2026-09-27 fixture results, each using a fresh loop target, were:
[The normalized six-run JSON](host-network-emmc-live-stage-offline-20260927-results.json)
has SHA-256 `500361647ede7f56de907f52433b0dd66bab83d84bad530eefdc322bfb17da82`.

| Injected stop | Last stage | Last arm | Marker | Admission refusals |
| --- | --- | --- | --- | ---: |
| none | wrapper durable | both copies verified | yes | 11 |
| after original | original preserved | none | no | 11 |
| after FIT | FIT durable | none | no | 11 |
| after wrapper | wrapper durable | none | no | 11 |
| after first environment write | wrapper durable | first write journaled | no | 11 |
| after second environment write | wrapper durable | second write journaled | no | 11 |

The separate mount test replaced the path's external mount after isolation;
the isolated process still read the original mount. These are offline fixture
results, not a physical eMMC mount-switch test.

The disposable success artifact used a 345,772-byte FIT (SHA-256
`dc38b91c0a1f1f2bd53cdcb24275f4fa0109791f5aae302a61e65abecea4e27a`)
and build manifest SHA-256
`74e92e88cd9b1d0a0255c83df8650677e736095f3cc948f2524e27f46e1e3581`.
Its source was synthetic `10.0.2.2:/srv/sv08-sd-nfs`; those hashes must never
authorize a physical write. The builder enforces a 64 MiB FIT cap, and staging
needs the actual FIT size plus the original script and a 16 MiB filesystem
reserve. The writer streams the 7,818,182,656-byte source rather than keeping
that image in RAM. H12 must measure the physical FIT and recovery free space;
the disposable FIT size is not a prediction for the real kernel/initrd.
The physical-candidate builder rejects the repository's synthetic job and
receipt verification keys, even if given a physical-shaped policy. A real
candidate still needs a fresh, privately recorded key and target review.

For H12, first restore printer Ethernet and record current power/USB-serial
state. Arm receive-only Beelink serial capture **before** connecting USB serial,
which powers the host. With the spare installed, run only read-only inspection
and record the private CID, controller, device numbers, GPT, mounted partition,
available staging space, original script hash, current boot policy and exact
artifact/source hashes. Check the NFS source independently of the eMMC; the
source must remain available in RAM-writer boot and cannot overlap the target.
The operator must then review the exact artifact, target and recovery action and
obtain immediate independent GPT-6 Sol high-consequence review under
[H12](coordinated-human-tasks.md). Run the separate stage, arm and activate
steps only after that review. First observe the fallback/FIT handoff without a
whole-device target write (`urh-04`); only a separately reviewed attended
full-image write/readback and next boot may satisfy `urh-05`. Stop on any
identity, source, policy, hash, space or boot result mismatch. Never retry a
partial journal automatically; use the independent SD rescue path as planned.

The custom adapter fills the current host updater's missing live recovery
staging gap. Retire it when a supported updater owns this transaction with
equivalent hardware evidence. The feature remains an offline candidate until
H12 physical checks pass.
