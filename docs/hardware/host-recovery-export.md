# Recovery user-data export

2026-09-11. Offline library, native GTK and real filesystem evidence. No printer,
physical USB medium, MCU or eMMC was accessed. This implements the archive/export
portion of [decision 0010](../decisions/0010-host-administration-and-recovery-ui.md).

The [2026-09-12 media provider](host-recovery-media.md) subsequently connects the
installed entry to verified pre-mounted admission. Its stronger real fixture checks
filesystem-superblock and whole-medium read-only state; the earlier read-only bind
fixture below alone does not establish those conditions.

The [single-pass readback improvement](host-recovery-readback.md) also retains
member verification while matching every byte against the write-time digest and
completed size. It removes the separate digest scan; measured logical read volume
falls by approximately 50% on the approved fixture.

## Implemented workflow

The recovery controller can now connect **Save user data** to
[the export adapter](../../runtime/sv08_export.py). The user chooses a listed
medium and reviews its label, estimated required space, entry count and the fact
that the archive contains private configuration/credentials. The source registry
may be missing or damaged: export does not require parsing it successfully.

The adapter accepts a source and destination map only from its caller, plus a
mandatory admission context. That context must identify the running recovery
system, verify a quiescent/read-only source, verify the selected removable mount,
and hold exclusive media/export admission throughout each operation. There is
no default permission, guessed device, mounting command, formatting operation or
raw device argument accepted from the UI. The subsequent pre-mounted provider now
supplies bounded offline-tested admission; production image/premount integration
and USB discovery remain outstanding. The installed screen enables export only
when that provider verifies explicitly prepared trust inputs and media.

Review binds the source/destination directory identities, source inventory and
size budget into a fingerprint. Apply repeats preflight and rechecks before
writing. Component-by-component descriptor-relative opens reject symbolic links;
links, special files, filesystem crossings, overlapping source/destination and
changed inventory are refused. Unreadable/unsupported files fail the export rather
than producing an apparently complete archive with silent omissions.

Data streams into a uniquely named `.partial` file. An uncompressed PAX tar stores
regular files/directories with mode, UID/GID and modification time, plus a manifest
of file sizes and SHA-256 checksums. Payload is streamed in bounded chunks; it is
not loaded into RAM as one image. Inventory/manifest bookkeeping is bounded to
100,000 entries. Sparse-file expansion, PAX headers, manifest and record padding
are included in admission, with 32 MiB of free-space reserve by default.

A complete readback checks members, file-content hashes and the whole-file digest
and size recorded during writing. Only afterward does
Linux `renameat2(RENAME_NOREPLACE)` publish the archive, followed by directory fsync.
There is no overwrite fallback on unsupported filesystems. Existing destination
files remain untouched. An ordinary failure removes only this operation's partial
file; a process/power interruption can leave an explicitly incomplete `.partial`.
Failure after rename but before directory fsync is not reported as success. The
provider integration attempts to remove its newly published output on a detected
failure; physical removal or power loss may prevent cleanup. Keep any surviving
completed-looking file for explicit inspection. Source files are never repaired,
deleted or rewritten by export.

The default archive limit is conservatively below FAT's 4 GiB file limit. The
verified media provider may configure another reviewed limit for a different
filesystem. FAT reports zero total inodes, so its admission uses byte availability;
filesystems with inode accounting must also have spare inodes.

## Evidence

- Unit tests create/read actual archives, verify manifest content, preserve a
  damaged registry, reject changed source/destination identities, reject links and
  FIFOs, reject insufficient space/file-size limits, and prevent publication after
  failed readback. Long Unicode paths and sparse expansion fit the admitted budget.
- A SQLite fixture archives a database and its committed WAL while the writer is
  quiescent. Reading the exported pair in a fresh directory recovers the committed
  value. This is not permission to copy an actively changing database.
- A real no-replace rename test retains a pre-existing destination file. A
  forced filename collision also preserves an older interrupted partial file.
- `tests/recovery_export_gtk.py` drives the actual GTK destination chooser and
  confirmation into a real archive, using disposable directories and an explicit
  fixture admission context. This extends the earlier callback-only UI test.
- `tests/recovery_export_mounts.py` binds a disposable source read-only and exports
  to a loop-mounted FAT32 image. Verification and no-replace publication pass;
  the damaged source registry remains unchanged. Mounts are removed afterward.
  This is workstation filesystem evidence, not physical hot-unplug/power-cut proof.

Run the filesystem fixture only in a private mount namespace; it defaults to
inspection and refuses an existing work directory:

```sh
sudo unshare --mount --propagation private \
  python3 tests/recovery_export_mounts.py \
  --work build/recovery-export-new --execute
xvfb-run -a /usr/bin/python3 tests/recovery_export_gtk.py
python3 -m unittest discover -s tests -p 'test_export.py'
```

The retained private filesystem result is `build/recovery-export-fat-v2/result.json`.
[Public evidence](host-recovery-export-20260911.json) records scope and output hash.
No archive containing user data is committed.

## Remaining integration and limits

Integrate the verified pre-mounted provider and trusted preparer into the independent
recovery image; finish USB discovery/removal reporting, progress/cancellation and
safe ejection. Test realistic
8 GB occupancy, larger exports, physical input, unplugging and power loss on the
named profile. The existing UI staging step includes the export helper and refuses
mismatched runtime sources. No service has been enabled on the printer.

This is a user-data archive, not an OS/MCU image or automatic restore package. It
does not preserve extended attributes/ACLs or hard-link relationships. It does
not attempt damaged-filesystem salvage or silently skip unreadable content. A
future restore operation must validate archive paths, metadata and target identity
before extracting; the exporter never extracts arbitrary archives onto the OS.
Readback through the filesystem does not establish storage-controller power-loss
behavior. Keep the factory eMMC and the private MCU backups separately.

The implementation is original project coordination around standard Python and
Linux facilities. Retire it when an upstream recovery/export service provides the
same guarded selection, preservation and verification semantics. Primary sources,
accessed 2026-09-11: [Python tarfile/PAX documentation](https://docs.python.org/3.13/library/tarfile.html)
and [Linux no-replace rename semantics and filesystem support](https://man7.org/linux/man-pages/man2/renameat2.2.html).
