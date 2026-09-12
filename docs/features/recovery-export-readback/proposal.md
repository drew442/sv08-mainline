# One complete readback pass for recovery archives

Kind: improvement. Author: pilot_suggester. Date: 2026-09-12.

## Problem and baseline

`runtime/sv08_export.py` first reads an entire exported archive for SHA-256, then
`verify_archive` rereads its payload for semantic/member checks. The suggestion
role reproduced the read volume in memory against baseline `2444ede`: a 9,123,840
byte PAX archive caused 9,123,840 digest bytes plus 9,119,075 semantic bytes to be
read, totaling 18,242,915 logical bytes. This measures reads, not elapsed time or
physical storage performance.

The fixture is one `data/fixture.bin` tar member containing
`b'offline-readback-measure\n' * 364722`, with default `TarInfo` metadata and PAX
format. Its SHA-256 is
`0767efa76615052ca0c1506ec6c76bbdeee2ce989c44dfa5aff434872102aa72`.
Reproduce and retain the measurement before claiming the improvement.

## Intended outcome

Validate archive members/content while computing the whole-archive digest through
one bounded streaming reader. Drain through EOF, including headers and trailing
padding, so the returned digest equals an independent whole-file digest. Remove
the separate complete digest scan. Target exactly 9,123,840 logical bytes read for
the baseline fixture, preserving every integrity and publication guard.

This reduces redundant recovery-media reads within the export behavior required
by [decision 0010](../../decisions/0010-host-administration-and-recovery-ui.md).
It introduces no storage format, dependency or hardware assumption and follows
the configured media export task so its complete fixture can test the change.

## Scope, alternatives and acceptance

Keep Python tarfile and SHA-256, the archive format, bounded buffering and the
existing no-replace publication path. A broader archive/compression redesign has
no demonstrated need. Retire this coordination if an upstream exporter supplies
the same complete verification and publication guarantees.

- `single-pass`: reproduce baseline and after-change logical read volume; compare
  the returned digest with an independent SHA-256, including trailing padding.
- `integrity`: preserve member/content validation and no publication after corrupt,
  truncated or failed reads; retain long Unicode names, directories, manifests,
  source preservation, GTK and real FAT fixture behavior.

Both checks are offline. Required physical media/power-loss validation stays in
[the canonical human checklist](../../hardware/host-os-tasks.md#human-and-powered-printer-tasks)
and the parent recovery feature. This result cannot establish a printing release,
physical device throughput or power-loss guarantees.
