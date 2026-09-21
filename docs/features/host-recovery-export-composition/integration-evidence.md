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
  `4b8b4869d5059d424379c32fb3d9b10b15558fedb8b966966d6fdaf797080c52`.
- **independent-gtk-export — pass.** The installed ARM64 GTK service and production
  provider completed keyboard, touch, and keyboard-plus-mouse review/cancel/apply
  journeys. Archives preserved the damaged registry, configuration, SQLite database
  and WAL, Unicode data, and an older archive.
- **lease-and-change — pass.** Corrected
  wrong-provider, settled destination-removal, no-space, stale-context, and
  destination-replacement runs refused preparation/export, retained prior archives,
  and preserved source/protected/recovery media. The lock-contention run used the
  ordinary candidate with a temporary systemd debug shell enabled only by the QEMU
  command line; a real guest `flock` holder was started before Apply. The UI refused
  export and preserved the prior destination file. The replacement run also retained
  the replacement medium's older file and published no archive; its before/after
  backing hashes are recorded in `result.json`. The archive-corruption journey exposed a publication-path race: the watcher replaced the partial pathname with a directory while the exporter held the original inode, and the UI reported success without a regular archive. That run is rejected and retained only as negative evidence. The runtime now revalidates the partial pathname inode/type before publication, and the harness rejects malformed `.tar` paths. A corrected-candidate rerun observed both guest watcher markers, showed the visible `Export readback verification failed` result, published no regular or malformed archive, preserved the older file, and preserved all protected media hashes. The operation-owned cleanup-failure rerun then observed both cleanup markers, showed the visible `Errno 16 Device or resource busy` diagnostic, retained the owned partial, published no regular or malformed archive, and preserved the older file and all protected media hashes.
- **composition-and-bounds — pass offline.** The corrected candidate is a
  536870912-byte image with 327692288 allocated bytes, a 241356800-byte SquashFS,
  49081 free ext4 blocks, 30017 free inodes, and peak QEMU RSS of 2136940544 bytes.
  The build source inventory is 20,451 files / 899,801,608 bytes. The staged
  recovery-specific delta is 18 tracked files, 2,898 added lines before the final
  cleanup/evidence revisions, 0 new Debian packages, and 0 new kernel modules; the
  runtime preparer is 347 lines and the harness is 926 lines. The candidate build
  workspace peaked at 1,638,000,000 bytes and the largest export workspace was
  224,000,000 bytes. The source-backed factory layout is 7,818,182,656 bytes and
  the recovery partition remains exactly 512 MiB. No physical write, restore, slot
  selection, or network authority is asserted.

## Six-check evidence binding

The six acceptance checks above are bound to the corrected candidate image SHA256
`4b8b4869d5059d424379c32fb3d9b10b15558fedb8b966966d6fdaf797080c52`, candidate
build record SHA256 `363fda0dea64a8ca4d3268ce17c18e2f9228b17423fb8e04670c5d079b762595`,
and harness source SHA256 `6bab388bc663be994a430cb883a09a53b1a1846b57da5395a0c44cc303af1803`.
The lease-and-change fault evidence is retained in the archive-corruption result
`dddc052ad5ea4c86a12f77926af8776966060661d43863e872da89c1292f2d55` and the
operation-owned cleanup-failure result
`bdf8baea2c38e51dab6c9613e9d42510299b1d5421e80606a2b91c632ffe7c42`; both
results preserve the older destination and protected media hashes.

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
- `recovery-composition-archive-corruption-observed-1dca3f7` (rejected negative evidence; malformed publication race)
- `recovery-composition-archive-corruption-qualified-1dca3f7` (corrected-candidate refusal; result JSON `dddc052ad5ea4c86a12f77926af8776966060661d43863e872da89c1292f2d55`)
- `recovery-composition-cleanup-failure-bind-1dca3f7` (operation-owned cleanup refusal; result JSON `bdf8baea2c38e51dab6c9613e9d42510299b1d5421e80606a2b91c632ffe7c42`; independent review qualifies the retained partial and visible `Errno 16 Device or resource busy` diagnostic)

The candidate build record SHA256 is
`363fda0dea64a8ca4d3268ce17c18e2f9228b17423fb8e04670c5d079b762595`. Result JSON
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
The observed archive-corruption result JSON is
`77fa47ca92c83c81012544bc42923c5be7d5d6bc8881c2a41473544de32c5b71`; it is
rejected because it reports success while leaving a directory named `*.tar`.

The candidate contains corrected preparer SHA256
`7a15b186078d2f2722b09d6c68e3082c4cb6e3e12e64436cec19b5b88706ab82`. Physical media,
board identity, hardware display/input, and factory-image behavior remain unverified.

## Current source correction and completed cleanup check

Commit `bf6c98f` records the written partial's device, inode, mode and link count
and rejects publication when the destination pathname no longer names that exact
single-link regular file. Its cleanup path leaves a foreign replacement directory
untouched, and the regression test reproduces the replacement race. The focused
offline suite passes 58 tests on the current feature branch. The retained VM
candidate predates this runtime hash, so it is not evidence for the correction;
the operation-owned cleanup-failure journey remains open. The locally rebuilt
candidate carries the new `runtime/sv08_export.py`
hash (`0f4530bcd0b1286ad1a875b72b37ba9f902b892b1cbda86df06a40e06306f17e`),
the regression source hash (`f2f1640b720feb413d5e2d266c5360198ec4eb203dced902b6e9a85aeab9ea47`),
and the archive-corruption journey now shows visible refusal with no new or
malformed archive. The cleanup-failure journey uses an operation-owned bind mount
to force `EBUSY`; it shows the visible diagnostic, retains the corrupted partial,
publishes no regular or malformed archive, and preserves the older file.

A locally regenerated candidate carrying that runtime hash booted and passed a
keyboard-only positive export with a coherent build record (`result.json` SHA256
`e28cfaf76c518c62bd6da1c0248a4270b6992af03cd7cfbb6b5be4aa5a48464f`; recovery
image SHA256 `4b8b4869d5059d424379c32fb3d9b10b15558fedb8b966966d6fdaf797080c52`).
Its archive-corruption attempt did not observe a partial and is not acceptance
evidence. The harness then moved fault setup to a serial debug shell, masked the
serial getty, and used QEMU's `mon:stdio` input (`8644869`, `3799f97`). The
corrected `smoke` journeys observed both watcher marker pairs and produced the
qualified archive-corruption and cleanup-failure refusals recorded above. The
current harness source hash is `6bab388bc663be994a430cb883a09a53b1a1846b57da5395a0c44cc303af1803`;
the candidate build record hash is `363fda0dea64a8ca4d3268ce17c18e2f9228b17423fb8e04670c5d079b762595`,
and the cleanup-failure result hash is `bdf8baea2c38e51dab6c9613e9d42510299b1d5421e80606a2b91c632ffe7c42`.
