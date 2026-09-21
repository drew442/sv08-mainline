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
- **lease-and-change — partial pending independent verification.** Corrected
  wrong-provider, settled destination-removal, no-space, stale-context, and
  destination-replacement runs refused preparation/export, retained prior archives,
  and preserved source/protected/recovery media. The lock-contention run used the
  ordinary candidate with a temporary systemd debug shell enabled only by the QEMU
  command line; a real guest `flock` holder was started before Apply. The UI refused
  export and preserved the prior destination file. The replacement run also retained
  the replacement medium's older file and published no archive; its before/after
  backing hashes are recorded in `result.json`. The attempted archive-corruption and
  cleanup-failure journeys are not counted: their retained screenshots did not prove
  entry into Apply or observation of an operation-owned partial. They remain open
  verifier tasks.
- **composition-and-bounds — pass offline.** The corrected candidate is a
  536870912-byte image with 327692288 allocated bytes, a 241356800-byte SquashFS,
  56355 free ext4 blocks, 31045 free inodes, and peak QEMU RSS of 2035699712 bytes.
  The build source inventory is 20,451 files / 899,801,608 bytes. The staged
  recovery-specific delta is 18 tracked files, 2,898 added lines before the final
  cleanup/evidence revisions, 0 new Debian packages, and 0 new kernel modules; the
  runtime preparer is 347 lines and the harness is 926 lines. The candidate build
  workspace peaked at 1,638,000,000 bytes and the largest export workspace was
  224,000,000 bytes. The source-backed factory layout is 7,818,182,656 bytes and
  the recovery partition remains exactly 512 MiB. No physical write, restore, slot
  selection, or network authority is asserted.

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
- `recovery-composition-stale-context-1dca3f7`
- `recovery-composition-replace-destination-1dca3f7`
- `recovery-composition-replace-destination-rerun-1dca3f7`
- `recovery-composition-lock-contention-rerun-1dca3f7`

The candidate build record SHA256 is
`e6db81f7cc20462d25ff752790186210df50496203623a2398227acb7556d906`. Result JSON
SHA256 values are: keyboard
`3418e34e72702a9836d4e0a5aa50e564bd0fb86ce434ae318a6c959864181a19`, touch
`dcee90d92dd5aafc1b18053218f8b987d217ec14551f046948c4c7fc94e87fc8`, mixed
`5547b7183411ea1ae41d697034bbf39184d8c2618ca40e3fecaf056fd233150f`, source
read-only `33e92be27d08b0ccdfa2f27c1bce318b75332c45bcba9d1d62b2490704a5c0dd`,
wrong-provider `cb2705355ebc62371f4ef3ccb39d9539ce4eca32b8565532b9243c147f6c4bcf`,
removal `5105fad2a4bf49e777244d6fda43447747afb6f972c129bb8c87d37134532af8`, and
no-space `5b2964234ea3b68c64dc5c13f165704e7d13d6cd6de04674df320a69dcb4ba8e`.
The stale-context and destination-replacement result JSON values are
`3ff7e89c0c31c5745cf23575e96d3038877f108980850ba5b1e4f647d43a85e6` and
the corrected replacement rerun is
`9753c8a0def33a2c89864c4344a46f501b7d265910fff053223eb67efa2dbddb`.
The lock-contention rerun result JSON is
`c83641faca236b816dc0dc8bdaa7ba7a2a0eda35e29b9660227d664ba5234b76`.

The candidate contains corrected preparer SHA256
`7a15b186078d2f2722b09d6c68e3082c4cb6e3e12e64436cec19b5b88706ab82`. Physical media,
board identity, hardware display/input, and factory-image behavior remain unverified.
