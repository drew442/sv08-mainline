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

Before release, implement the production RAUC/device backend, shared service-start
admission, automatic idle staging/next-boot policy, reconciliation at boot and
bounded health/recovery behavior. Do not wire the test callbacks into production.
The [early-boot failure unit](host-boot-failure.md) now reboots on errors/timeouts
in QEMU; a board-integrated fallback and watchdog remain on the [task list](host-os-tasks.md).

This is original project coordination around upstream RAUC and the state module;
no upstream source is modified. It extends [decision 0006](../decisions/0006-host-state-integration.md).
Retire it if upstream integration provides the same generation/customization and
crash-ordering semantics, keeping the failure tests as acceptance evidence.
