# Recovery export composition integration evidence

This document records the offline integration run for `host-recovery-export-composition`.
It is evidence for the approved six-check task, not a claim of physical-printer
compatibility. The corrected candidate was built from the recovery preparer at
feature commit `efc01cd`; the later harness-only media-settle fix is `06760ca`.
The guest is ARM64 QEMU with the reviewed 512 MiB recovery image and disposable
regular-file media fixture.

## Acceptance checks

- **profile-and-trust — pass.** The candidate authenticates immutable envelope and
  provider bindings, compares the complete measured media inventory, and rejects the
  wrong-provider binding. The corrected wrong-provider run failed preparation, wrote
  no destination archive, and preserved all media hashes.
- **preserve-before-mount — pass.** Keyboard, touch, mixed-input, and read-only-source
  runs record whole-medium and partition read-only events before the first source
  mount, use `ro,noload,nosuid,nodev,noexec`, and preserve recovery, source, and
  protected hashes. The destination uses read-only-first FAT mounting followed by
  identity revalidation before the writable remount.
- **compressed-chain — pass.** Positive boot reports show an immutable read-only ext4
  root and exactly one read-only SquashFS `/usr` loop, with the preparation service
  active and no failed units. Corrected candidate image SHA256 is
  `a4f61ea2635e4c4c203f284e4064b4f0051212f9f6f807d09825782e28ce0d41`.
- **independent-gtk-export — pass.** The installed ARM64 GTK service and production
  provider completed keyboard, touch, and keyboard-plus-mouse review/cancel/apply
  journeys. Archives preserved the damaged registry, configuration, SQLite database
  and WAL, Unicode data, and an older archive.
- **lease-and-change — pass for exercised production paths.** Corrected wrong-provider,
  settled destination-removal, and no-space runs refused preparation/export, retained
  prior archives, and preserved source/protected/recovery media. Focused unit tests
  also cover shared-lock, stale-context, archive-integrity, and operation-owned
  cleanup paths. Those four unit-level paths are not separate long-running UI runs.
- **composition-and-bounds — pass offline.** The corrected candidate is a
  536870912-byte image with 327692288 allocated bytes, a 241356800-byte SquashFS,
  56355 free ext4 blocks, 31045 free inodes, and peak QEMU RSS of 2035699712 bytes.
  No physical write, restore, slot selection, or network authority is asserted.

## Reproducible checks

From the feature worktree:

```text
python3 -m unittest tests.test_recovery_prepare tests.test_recovery_media tests.test_recovery_image
python3 -m py_compile runtime/sv08_recovery_prepare.py runtime/sv08_recovery.py tests/recovery_export_vm.py
python3 -m unittest tests.test_recovery_export_vm
```

The focused preparation/media/image/export tests pass (57 tests), syntax compilation
passes, and the harness tests pass. The historical full recovery discovery suite still
contains two unrelated stale board-test failures.

Retained local evidence directories:

- `recovery-composition-candidate-1dca3f7`
- `recovery-composition-keyboard-1dca3f7`
- `recovery-composition-touch-1dca3f7`
- `recovery-composition-keyboard-mouse-1dca3f7`
- `recovery-composition-source-readonly-1dca3f7`
- `recovery-composition-remove-destination-1dca3f7`
- `recovery-composition-wrong-provider-1dca3f7`
- `recovery-composition-no-space-1dca3f7`

The candidate contains corrected preparer SHA256
`7a15b186078d2f2722b09d6c68e3082c4cb6e3e12e64436cec19b5b88706ab82`. Physical media,
board identity, hardware display/input, and factory-image behavior remain unverified.
