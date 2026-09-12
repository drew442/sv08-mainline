# Recovery archive readback improvement

2026-09-12. Offline evidence for the approved
[readback improvement](../features/recovery-export-readback/proposal.md).
The printer remained offline. No physical medium, eMMC or MCU was accessed.

## Result

The [export adapter](../../runtime/sv08_export.py) now hashes bytes while writing
and combines archive-member verification and whole-file readback into one forward
pass. The uncompressed PAX format and manifest are unchanged. The completed
readback must match both the write-time SHA-256 and byte count, including headers,
terminators and final padding, before publication is allowed.

The [reproducible fixture](../../tests/measure_export_readback.py) uses the exact
approved 9,123,840-byte archive. Its SHA-256 is
`0767efa76615052ca0c1506ec6c76bbdeee2ce989c44dfa5aff434872102aa72`.
The retained baseline is commit `f7a3d53e09f3d12641639808f2cb3277d13cb6cc`;
the script checks its source hash before loading it from local Git history.

| Logical verification reads | Before | After |
| --- | ---: | ---: |
| Separate complete digest scan | 9,123,840 | 0 |
| Semantic verification and any complete-byte readback | 9,119,075 | 9,123,840 |
| Total bytes returned by underlying reads | 18,242,915 | 9,123,840 |

This removes 9,119,075 logical read bytes, approximately 50%. The measurement counts
actual returned bytes, including stream read-ahead and the final EOF drain. It uses
an in-memory fixture to make the count repeatable, and matched on workstation
Python 3.12.3 and selected Debian ARM64 Python 3.13.5 under QEMU user emulation.
It does not measure elapsed time, physical USB throughput or exact peak memory.
Hashing during writes adds CPU work to that phase. Filesystem readback may use
cache and does not prove storage-controller power-loss durability.

## Integrity and resource bounds

`HashWriter` observes every tar write, including padding, and refuses a short
write. After file flush/fsync, `verify_stream` uses the supported `r|` streaming
mode. Its underlying reader hashes each returned byte once and never seeks.
Payload reads are bounded to 1 MiB and tar buffering is set to 10,240 bytes.
Member iteration can finish before physical EOF; a final drain consumes any bytes
not already read by tarfile. Buffered bytes are not hashed a second time.

Tarfile may treat a malformed late header as end-of-archive. Member hashes alone
would also miss changed valid metadata or padding. Matching the completed byte
count and the writer's full digest detects these changes. Duplicate, unexpected,
missing and special members remain failures, as do payload/manifest mismatches.

The writer records its largest complete serialized header length, **H**, including
PAX metadata/padding and the manifest header. A subclass of the documented
`TarInfo.fromtarfile` hook limits cumulative underlying metadata reads to
**H + 10,240** bytes per outer header parse; nested PAX parsing cannot reset it.
There can additionally be up to 10,240 bytes buffered before parsing starts, so
**H + 20,480** is a conservative parser-input allowance, not a process RSS bound.
This permits the writer's valid long Unicode/PAX names while bounding oversized
PAX declarations, nested metadata and GNU sparse-map input.

Parsed sparse encodings and negative or larger-than-archive member sizes are
refused before extraction. Sparse source files still expand into ordinary regular
members, with their full size admitted beforehand. Independent review identified
why the separate sparse rejection matters: a 10,240-byte archive could otherwise
request 16 MiB of synthetic zero payload before its checksum failed. A real PAX
regression now asserts rejection before `extractfile` is called.

The held destination descriptor, source inventory/identity checks and
[media provider](host-recovery-media.md) remain in force. Its operation lease is
held through verification, no-replace rename and directory fsync. Failure does
not report success; cleanup touches only this operation's output. Physical
removal or power loss can still prevent cleanup, as documented in the
[export contract](host-recovery-export.md).

## Validation and reproduction

[Sanitized results](host-recovery-readback-20260912.json) record the measurement,
runtime tests, staging sizes and real filesystem/GTK result. No user archive is
committed. The final implementation passed:

- 53 workstation tests covering export/readback, media admission, admin adapters,
  UI staging and host integration; 34 export/readback/media tests also passed on
  the selected ARM64 Python 3.13.5 interpreter and libraries under QEMU.
- Actual corrupt headers, valid changed metadata, payload/manifest corruption,
  malformed late headers, damaged padding, truncation and appended data. These
  prevent publication and preserve source and older destination files. Final-drain
  read errors, short writes and fsync failure also refuse completion.
- Existing Unicode/PAX, directories, sparse-source budgets, SQLite/WAL,
  no-replace publication and operation-owned cleanup regressions.
- Native GTK chooser/review/apply with a real archive, then the approved provider's
  actual GTK workflow using read-only ext4 source/recovery images and a FAT32
  destination. Both cancellation points, shared exclusion through publication
  and fsync, source aliases/submounts/namespaces, whole-medium read-only checks,
  mid-operation removal and device-number reuse passed. Whole source/recovery
  images, damaged registry and existing destination data stayed unchanged.

The GTK directory fixture reported the existing unavailable accessibility-bus
warning on this workstation. This test does not validate the final image's
accessibility package closure or physical touch input.

Run the deterministic measurement and focused tests from a full checkout retaining
the baseline commit:

```sh
python3 tests/measure_export_readback.py
python3 -m unittest discover -s tests -p 'test_export*.py'
python3 -m unittest discover -s tests -p 'test_recovery_media.py'
xvfb-run -a /usr/bin/python3 tests/recovery_export_gtk.py
```

The privileged fixture creates only disposable media in a private mount/PID
namespace. It defaults to inspection, refuses an existing work directory, requires
352 MiB free space and removes its successful disposable images. Use a fresh work
directory; its result JSON remains available afterward:

```sh
mkdir -p build
sudo unshare --mount --pid --fork --propagation private \
  /usr/bin/python3 tests/recovery_media_mounts.py \
  --work build/recovery-readback-new --execute
```

For the target-runtime checks, use the selected root's dynamic loader and library
path under QEMU with `PYTHONHOME` pointing to that root's `/usr`. Keep QEMU's `-L /`
so filesystem operations and descriptor-relative opens see the same workstation
temporary directory. `-L <target-root>` alone mixes translated absolute paths
with host-created temporary directories. Test only `test_export.py`,
`test_export_readback.py` and `test_recovery_media.py` with `-S`; other workstation
build tests may require dependencies intentionally absent from the target runtime.
These checks do not boot or alter that root.

Fresh matching UI/runtime staging changed host payload from 84,562 to 88,309 bytes
and recovery payload from 67,003 to 70,750 bytes: 3,747 additional bytes each, with
no new runtime dependency. Package closure, the complete 512 MiB recovery image,
factory 8 GB occupancy, physical input/media and power-interruption acceptance
remain on the [canonical task list](host-os-tasks.md#human-and-powered-printer-tasks).

## Provenance and retirement

This is original project coordination around public Python tarfile APIs, within
[decision 0010](../decisions/0010-host-administration-and-recovery-ui.md). No Python
source or upstream submodule was modified. Retire these wrappers when an upstream
recovery/export facility supplies equivalent bounded, complete-byte verification
and the existing guarded publication contract; retain the corruption regressions.

Primary sources, accessed 2026-09-12: Python 3.13 documentation for
[stream modes and buffering](https://docs.python.org/3.13/library/tarfile.html#tarfile.open),
[the supported TarInfo subclass argument](https://docs.python.org/3.13/library/tarfile.html#tarfile.TarFile),
and [TarInfo.fromtarfile](https://docs.python.org/3.13/library/tarfile.html#tarfile.TarInfo.fromtarfile).
Buffering/resource conclusions above are implementation analysis and measured
regressions, not an upstream guarantee of a fixed process memory limit.
