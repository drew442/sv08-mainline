# Interrupted update transaction ordering

2026-09-10. Integration library with failure tests; production backend, idle
admission and health criteria remain required before enabling it on a printer.

[The transaction library](../../runtime/sv08_transaction.py) coordinates the gaps
between RAUC slot writes, persistent state generations and boot selection. It
requires explicit backend, admission and health callbacks. There is no permissive
default that assumes a printer is idle or healthy, and no hardware command-line
entry point is installed.

The durable sequence is:

1. Hold the state lock and admission lease; validate the running release, immutable
   mode, both slots' customization records and source boot selection. Reject an
   existing transaction or a release already represented by a state generation.
2. Record `installing` before the backend writes either inactive image. Require
   the authenticated exact bundle, verified paired hashes, preserved source
   devices and `activate-installed=false`. Record `staged` only after the target
   remains bad and the source remains primary. No application state is copied.
3. Record `arming`, then publish the pending state trial durably before selecting
   the target in the bootloader. Record `armed` afterward. Repeating an already
   completed arm never replenishes attempts. Resume an interrupted arm only in
   the original staging boot; after reboot, reconcile against the running slot.
4. At a target boot, normal early preparation copies the latest source state.
   Confirmation requires the matching prepared trial and explicit successful
   health callback. Record `confirming`, mark the target good, clear pending state,
   then record `complete`. Only afterward may the caller release the trial gate.
5. To cancel from the preserved source, mark the target bad and verify disarming
   before clearing pending state. After normal fallback preparation, retain the
   failed trial/generation and record `failed`. Interrupted cancellation can retry.

An interrupted installation remains inspectable as `installing`; it cannot be
silently reclassified as successful. Cancel/disarm it before restaging. Customized
inactive slots are protected too. Reusing an existing release ID is rejected
because it could otherwise reuse an old generation instead of copying late state.
The source and target release identities remain explicit throughout.

## Validation

`tests/test_transaction.py` injects failures during installation, after boot
selection, during confirmation publication and while disarming. It checks durable
pending-before-selection ordering, idempotent activation, same-boot resumption,
failed-health refusal, cancellation/fallback and customization protection. These
are filesystem/state tests with a bootloader double, not power-cut evidence.

The existing native RAUC file fixture can additionally exercise the transaction
library with its real private service:

```sh
sudo unshare --mount --propagation private python3 tests/rauc_file_install.py \
  --rauc build/rauc-native-v2/rauc \
  --bundle build/rauc-bundle-metadata-v1/paired.raucb \
  --keyring build/rauc-bundle-v1/keys/test.cert \
  --work build/rauc-transaction-new \
  --transaction-policy build/rauc-bundle-metadata-v1/policy.json --execute
```

The real RAUC run passed under `build/rauc-transaction-v2/`: installation preserved
A and verified B's paired hashes, activation published pending state before
selection, and the simulated B trial completed confirmation through RAUC. The
[public result](host-transactions-20260910.json) labels the test callbacks. An
initial run correctly rejected the custom test chooser's selected-but-bad state;
its set-primary fixture now also marks that slot bootable, matching the separately
tested U-Boot activation behavior.

The backend must validate the actual running slot and selected configuration,
verify exact signed inputs and output hashes, and keep selection separate from
installation. This fixture supplies those checks for regular files only. Its
admission and health callbacks are test stubs: they establish method ordering,
not printer idleness or Linux/application health. U-Boot backend and Linux boot
behavior have [separate](host-environment-build.md) [tests](host-rollback-build.md).

The subsequent [RAUC/device backend](host-rauc-backend.md) and
[shared service admission](host-update-admission.md) now pass integrated VM tests.
Before release, finish board configuration, automatic idle staging/next-boot policy,
reconciliation at boot and bounded health/recovery behavior. Do not wire the test callbacks into production.
The [early-boot failure unit](host-boot-failure.md) now reboots on errors/timeouts
in QEMU; a board-integrated fallback and watchdog remain on the [task list](host-os-tasks.md).

This is original project coordination around upstream RAUC and the state module;
no upstream source is modified. It extends [decision 0006](../decisions/0006-host-state-integration.md).
Retire it if upstream integration provides the same generation/customization and
crash-ordering semantics, keeping the failure tests as acceptance evidence.

## State-copy capacity admission

Staging now checks the source generation before journaling/installing and requires
free space for the entire configured 256 MiB late-copy allowance plus the 512 MiB
operating reserve. The uploaded bundle already consumes disk space at that point.
This keeps a small current configuration from admitting an update with no room
for its permitted growth before reboot. Trial preparation independently rechecks
actual destination space and inodes immediately before copying.

The shared check counts directory blocks, rounds regular files to filesystem
blocks, counts sparse files at expanded destination size, rejects special files
and links, and retains 128 spare inodes. It uses space available to ordinary users,
so ext4's reserved blocks are not part of the update budget. Tests cover sparse
expansion, byte/inode exhaustion, the full staging allowance and refusal before
any installer call or new journal. This is a preflight check, not a quota: later
user writes can consume space, in which case trial preparation fails and retains
the source generation. Owned upload staging, quotas/cleanup policy and physical
full-storage rollback testing remain separate work.

## Interrupted boot reconciliation

`Transaction.reconcile()` now classifies a prepared boot without marking a slot
or inferring health. It distinguishes staged work in the original boot, an armed
image awaiting reboot, interrupted installation requiring cancellation, fallback
requiring cancellation, and a running trial requiring health confirmation.
A source reboot never silently rearms the target or replenishes its counters.

If power fails after bootloader activation but before the journal changes from
`arming` to `armed`, the exact target can already be running. With matching
announced release, transaction ID and prepared trial generation, reconciliation
repairs that journal phase and still requires the independent health check.
Orphan pending state, mismatched transactions and unannounced target boots are
refused. The application trial gate stays closed until confirmation completes.
Unit tests inject that activation/journal interruption, repeat reconciliation,
reject failed health, and exercise source reboot and actual state-registry
fallback. The coordinator still must call reconciliation and execute its returned
next step; these new cases have offline library evidence, not physical power-cut
or assembled boot-service evidence.
