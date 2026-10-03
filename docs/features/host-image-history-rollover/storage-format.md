# Finite image receipt history, format 2

Implementation contract, 2026-10-03. Current record.json approval governs.
This custom integration fills RAUC's missing browser retry identity retention;
retire it only when upstream supplies equivalent durable semantics.

`jobs.json` alone commits the view. Legacy is a validated list of at most 128
original receipts. Format 2 has exactly `format_version` (integer 2), `generation`
(integer 1..2^63-1), `parent_revision` (null at generation 1, otherwise lowercase
SHA-256), `active`, `archives`, and `maintenance`. A descriptor has exactly
`name`, `sha256`, `bytes`, `count`: name is `snapshot-<sha256>.json`, digest binds
its exact bytes, bytes is 1..2752512, count is 0..128. Archives are ordered oldest
first, at most eight, each exactly 128 settled receipts. Active may be empty.
All snapshots use the original bounded receipt/disposition list schema. Validate
all objects and global identity uniqueness before lookup. Original fields and
evidence are preserved. Revision is SHA-256 of canonical JSON of the complete
manifest (canonical complete list for legacy). Duplicate JSON keys refuse.
Manifest encoding is at most 65536 bytes, inside the 1 MiB metadata ceiling.
Maintenance is null or `{plan, archive_sha256}`; plan has exactly kind
`history-maintenance-v2`, operation `migrate` or `rollover`, revision and the ordered
active IDs. It is an acknowledgement token, never an executable image plan.
Ordinary saves retain it, so lost acknowledgements remain recognizable.

The directory is owned by the administrator, exactly 0700. Files are regular,
owned, exactly 0600, single-link, opened through held directory descriptors with
no symlink traversal. The sole exception is the persistent ledger exclusion inode:
`ledger.lock` and `history-format-v2.lock` are exactly two names for the same
inode/device, nlink exactly two. Validate the held descriptor and both aliases
**after flock**. No lock is rotated or removed. Version 2 requires the valid pair.
A missing manifest with the pair, any snapshot or temporary refuses. No orphan
reconstruction is permitted. Fenced valid legacy is an interrupted migration;
new observation is allowed, explicit newly reviewed resume is required.

Migration/apply excludes worker then ledger. Review binds the complete revision
and exact IDs; rollover requires all 128 active rows terminal or explicitly
retained unknown, and a free archive slot. No polling/retry migration. Fence
creation uses directory-relative link to the original held inode, validates the
pair, fsyncs the inode, directory and parent **before** format publication. Fence
is monotonic, including publication failure. An admitted old waiter still uses
that inode: after a complete publication its list reader refuses; before it,
legacy writes are possible and a new resume must revalidate their revision.
Unchanged old public paths reject the pair by their single-link lock check.
Bare old internal load on absent jobs.json still returns []; direct internal
load/save and privileged removal of compatibility metadata are unsupported.
Neither rollback boot nor signed policy changes.

Under ledger then nonblocking allocation exclusion, validate current view,
fsync its objects/manifest/directory/parent to settle previous uncertainty, then
reclaim only validated owned unreferenced publication debris. Never clean through
corrupt history. Preflight complete peak: existing allocation plus candidate,
legacy preservation, temporary manifest, directory/lock growth, at most sixteen
batch-sized objects, 64 namespace entries, 1 MiB metadata, 64 MiB allocated.
Write unique object temporary, flush, fsync; rename-no-replace to hash name, fsync
directory. Existing digest objects may be reused only after exact validation.
Preserve legacy bytes as a hash snapshot before replacing legacy manifest.
Write/flush/fsync unique manifest temporary; atomically replace jobs.json, fsync
directory and parent. This replace never unlinks the authoritative name. No
success acknowledgement or worker launch precedes durable publication. After
rename/fsync failure return uncertainty, never restore stale data; subsequent
validated durability synchronization precedes cleanup. Failed cleanup refuses the
next allocation. Repeated attempts reclaim debris first, keeping peaks bounded.

Active saves require the observed revision and active-only rows. Settled rows and
dispositions are immutable; all original identity/plan/boot/queue fields remain
fixed. An interrupted fenced legacy view refuses new identities until explicitly
reviewed resume, while existing retries and observation remain available. Archived IDs
cannot be modified. All-history lookup precedes capacity/current-state admission;
workers select active rows only before constructing their controller. Unknown
stays unknown even when disposition makes rollover eligible. Upload gates retain
raw phase and all historical artifact dependencies; review includes history revision.

Shared `/data/sv08/allocation.lock` is a persistent private single-link leaf lock,
included conservatively in history metadata and namespace accounting. Configured
nondefault participants must use a common Budget whose floor is the maximum of
all configured reserves; installed defaults select the same persistent inode.
Order: worker -> state -> RAUC writer -> ledger -> allocation; upload ledger ->
nonblocking state -> upload -> allocation, then stream keeps only upload/allocation;
state-copy state -> allocation. Never acquire higher locks under allocation or
hold ledger over service/device waits. F=max(configured state reserve+copy limit,
configured staging reserve), defaults 768 MiB. H=two rounded maximum snapshots+
1 MiB rounded metadata, plus 64 inodes, protects future receipt results. New
identity/maintenance preserves F+peak+H; existing running/result/disposition saves
may use H but preserve F+actual peak. State copy/upload additionally retain their
original admission floors. Cooperative allocators are history, upload receive and
state generation creation/copy. Registry/journal/feed writes and unrelated
application/log/package/privileged writers retain their existing failure semantics;
this is admission under exclusion, not a quota against those writers.

Export validates source read-only, records the exact pair as a bounded explicit
relationship tied to history revision, and semantically verifies archive readback.
Isolated restore reconstructs the pair only with no live helpers or lock waiters;
never replace a live lock inode. Missing/corrupt history or changed source refuses
complete export. Export does not license receipt deletion. Shared history remains
outside generations across A/B rollback. Factory artifact fit and physical power
loss remain open; offline tests supply neither hardware nor release evidence.


Canonical encoding is UTF-8 JSON with sorted keys, compact separators,
ensure_ascii=true and one trailing newline. Snapshot hashes and committed-view
revisions use SHA-256 of these bytes. Descriptor bytes bind the actual snapshot
file; snapshots need not be regenerated to perform observation. Original receipt
limits are enforced by Jobs.validate_rows, including the complete 16 KiB bounded
disposition evidence; format 2 does not introduce a shortened receipt schema.
Object temporaries are `.history-object-<32 lowercase hex>` and manifest
temporaries `.history-manifest-<32 lowercase hex>`. Namespace accounting rejects
other names, counts the legacy list as a batch object, and conservatively counts
both ledger aliases plus the shared allocation lock. Migration publishes the
canonical complete legacy list as the active object, with generation 1 and null
parent; later publications increment generation and bind the prior revision.
Rollover references the former active object as the next archive and commits an
empty active object. It copies no combined all-history list back into active.

The export manifest remains format_version=1, kind
`user-data-export-not-os-image`, with `files` checksum records plus `history`.
Each fenced history relationship is exactly `{path, revision, alias, target}`:
path is its source-relative directory, revision the validated committed-view
revision, alias `history-format-v2.lock`, target `ledger.lock`. The alias is a tar
hardlink to the source-relative ledger name, represented in files as
`{path, hardlink}`; every other file retains `{path, bytes, sha256}`. Semantic
readback accepts only that exact expected relationship, with ordinary duplicate,
unsafe-path, sparse expansion and checksum protections still enforced.

`restore_history(archive_path, destination, exclusive)` is a narrow isolated
library path, not an exposed browser restore command. The caller supplies a lease
excluding helpers, workers and open lock waiters; destination must not exist.
Admission checks a safely opened owned parent, 64 MiB plus four filesystem blocks
and 68 free inodes. A private sibling temporary receives only one bounded history
namespace, with all payload files fsynced and export checksums checked. Recreate
only the recorded exact alias, validate the complete Jobs view and relationship
revision, fsync the directory and parent, then publish the directory with
rename-no-replace and fsync its parent. Failure cleans only the isolated temporary;
a post-publication durability failure is uncertainty, never live-lock replacement.
Flattened locks, missing manifest/alias or corrupt refs refuse. There is no general
OS restoration service integration claim; existing update/rollback paths keep
shared history in place.


## Independent-review repair, 2026-10-03

The shared allocation **root**, `/data/sv08`, retains the existing boot contract:
owned by the administrator and mode 0711, permitting application traversal while
preventing listing or writes. A private 0700 root is also valid. No boot chmod or
application permission policy changes. Both allocation preflight and exclusion
validate that exact pair of allowed modes and safe ancestry. `allocation.lock`
remains owned, regular, exactly 0600, single-link and bound to its held descriptor.
The history directory itself remains exactly 0700; the two ledger aliases retain
their sole exact hardlink exception.

Public identical submission/disposition acknowledgements and receipt-history
observation establish durability of the authoritative complete view under ledger
exclusion before returning it. This includes the second submit acquisition,
retained-disposition inspection before current-service/state gates, and the final
post-launch submission response. Revalidate the complete view/revision; fsync all
referenced snapshot files, jobs.json and the persistent ledger inode, then its
directory and parent. Failure refuses/remains uncertain, so the browser retains
its pending identity. This path creates no new identities, executes/launches no
backend action, restores no stale manifest and performs no debris cleanup. It
acquires no state/service/allocation lock. Publication's separately excluded
settlement/cleanup path retains its existing ordering and bounds. Read-only export
continues to use validated view reads without acknowledgement fsyncs or lock repair.

An existing exported history directory requires jobs.json; export never invents
a committed empty view from a missing manifest. Isolated restore requires
jobs.json even for legacy history. Its recorded history
namespace must equal the complete extracted regular files plus the exact alias;
missing recorded payloads, duplicate records, extra payloads, multiple history
inventories, bad checksums and missing/damaged versioned pairs refuse before final
destination publication. Valid legacy restores retain every receipt; valid fenced
restores retain the pair and refuse unchanged-old public admission. A missing
restore destination is never presented as an enabled restored history.

Restore tar decoding now uses the existing forward-only bounded ReadbackReader
and TarInfo metadata hook. A logical header chain has a fixed 65536-byte metadata
allowance plus the 10240-byte stream buffer; nested/global PAX, GNU long names/links
and GNU sparse-map metadata are bounded **before** decoding allocates their
claimed sizes. Underlying reads remain at most 1 MiB. Archive input must be a
regular file, 10240..4294967295 bytes, matching the existing default export ceiling;
held source identity and exact bytes-read size are rechecked. Member counts,
paths, ownership/modes, negative/excessive sizes, sparse expansion, payload and
namespace ceilings remain checked before extraction/publication. Export's ordinary
semantic readback retains its writer-derived header bound. No general restore
service, live-lock replacement, new retention policy or hardware authority is added.
