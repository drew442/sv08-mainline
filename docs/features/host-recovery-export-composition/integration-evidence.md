# Recovery export composition integration evidence

This document records the offline integration run for `host-recovery-export-composition`.
It is evidence for the approved six-check task, not a claim of physical-printer
compatibility. The candidate was built from feature commit `638817c` and run as an
ARM64 QEMU guest with the reviewed 512 MiB recovery image and disposable regular-file
media fixture.

## Acceptance checks

- **profile-and-trust — pass.** The candidate authenticates the immutable envelope and
  provider bindings, compares the complete measured media inventory, and rejects the
  wrong-provider binding. The wrong-provider run ended with the preparation unit
  failed and no destination archive; the pre-existing archive and all media hashes
  were unchanged.
- **preserve-before-mount — pass.** The successful runs recorded whole-medium and
  partition read-only events before the first source mount, mounted ext4 with
  `ro,noload,nosuid,nodev,noexec`, and preserved recovery, source, and protected
  media hashes. The source-read-only control used a separately read-only backing
  source. The implementation holds validated descriptors and revalidates the
  destination after a read-only-first FAT mount before remounting it writable.
- **compressed-chain — pass.** The boot reports show the immutable ext4 root mounted
  read-only and exactly one read-only SquashFS `/usr` loop, with the production
  preparation service active and no failed units in positive runs. Candidate image
  SHA256 is `7774a36185a0e54f1b7e424c24f8557e6c991859a3a95176b28956e30fc0a8cf`.
- **independent-gtk-export — pass.** The installed ARM64 GTK recovery service and
  production provider completed independent keyboard, touch, and keyboard-plus-mouse
  review/cancel/apply journeys. The exported archive preserved the damaged registry
  as data, configuration, SQLite database and WAL, Unicode data, and an older archive.
- **lease-and-change — pass for exercised refusal paths.** Wrong provider and removed
  destination runs refused preparation/export, retained prior archives, and preserved
  source/protected/recovery media. The harness also exercises shared-lock and stale
  context paths through the recovery unit tests. The no-space run was prepared but
  could not complete because the host filesystem exhausted its remaining workspace;
  no candidate or fixture was changed by that failed harness invocation. A production
  no-space result remains required before physical deployment.
- **composition-and-bounds — pass offline.** The candidate build record reports a
  536870912-byte image, 297635840 allocated bytes, 224448512 SquashFS bytes, and
  peak QEMU RSS of approximately 2.0 GiB. Positive and refusal runs used only the
  staged candidate runtime and selected pinned inputs. No physical write, restore,
  slot selection, or network authority is asserted here.

## Reproducible checks

From the feature worktree:

```text
python3 -m unittest tests.test_recovery_prepare tests.test_recovery_media tests.test_recovery_image
python3 -m py_compile runtime/sv08_recovery_prepare.py runtime/sv08_recovery.py tests/recovery_export_vm.py
python3 -m unittest tests.test_recovery_export_vm
```

The first command ran 41 tests successfully. Syntax compilation and the export-harness
unit tests passed. The full historical recovery discovery suite still contains two
unrelated stale board-test failures; those are not hidden by this feature evidence.

The retained VM result directories are disposable local evidence under
`local/feature-workflow/worktrees/host-recovery-export-composition/build/`:

- `recovery-composition-keyboard-c408f3e-v2`
- `recovery-composition-touch-c408f3e`
- `recovery-composition-keyboard-mouse-c408f3e-v6`
- `recovery-composition-source-readonly-c408f3e`
- `recovery-composition-remove-destination-c408f3e`
- `recovery-composition-wrong-provider-c408f3e-v2`

The independent verifier must inspect these results and this document before the task
can be marked complete. Physical media, board identity, hardware display/input, and
factory-image behavior remain unverified.
