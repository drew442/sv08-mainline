# 0013 — Bounded browser bundle intake and managed cleanup

Status: implemented under the delegated [approved proposal](../features/host-admin-bundle-upload/proposal.md), pending independent delivery verification.
Date: 2026-09-12. Requirement: [ADR 0010](0010-host-administration-and-recovery-ui.md).

The authenticated Cockpit page reviews a retained File object and streams binary
stdin to the fixed installed `sv08_admin_upload.py` helper. A bounded JSON header
contains display name, declared size and reviewed state/policy identities. The
helper admits only the installed host policy/keyring; browser requests cannot
choose an executable, destination, verifier, keyring, device or URL.

Cockpit's selected 337 `process.input` returns immediately. One 64 KiB File slice
is sent per server acknowledgement; the next slice is not loaded until the prior
byte count is acknowledged. EOF is required after the declared bytes. A manifest
signature and whole-file digest permit atomic private publication but explicitly
leave `full_payload_verified=false`. Installation reauthenticates its lease and
retains RAUC payload verification and existing current-state/customization/idle
admission. Upload itself is allowed in writable mode.

Lock order is ledger → state → upload. Intake review, admission and exact-object
cleanup coordinate against pending/ambiguous image work. Cleanup retains all
three locks through revision/object revalidation and unlink. Long intake releases
ledger/state and retains only upload through receipt, authentication, hashing and
publication; it never reacquires higher locks. Status probes the upload lease
without waiting. Jobs.submit holds ledger while planning and refuses busy intake
before writing any receipt. Its worker retains its existing worker → ledger
ordering, releases ledger before transaction work, and reacquires ledger only
after transaction locks are released. No state → ledger path is introduced.
The already leased internal transaction admission skips only the external busy
probe; it preserves all other checks and the existing exclusive install lease.

Linux `renameat2(RENAME_NOREPLACE)` publishes without overwriting and without a
two-hardlink crash window. Unsupported atomic publication fails closed. Graceful
failure removes only the current unpublished partial. Process death can retain a
partial or completed file; reconnect only observes state, and no transfer or image
job is replayed. A missing completion acknowledgement does not imply publication.

RAUC stdout/stderr and duration are bounded. A separate subreaper supervises its
process group and watches a helper-lifetime pipe. It inherits the same upload lock
open-file description and holds exclusion until verifier descendants are killed
and reaped, including after helper SIGKILL. A kernel-stalled child can therefore
leave storage truthfully busy; cleanup cannot bypass that retained lease.

Cleanup binds managed name, device/inode, size, mode, timestamps and state/policy
revision. Linked/nonmanaged/replaced files are refused. Active/ambiguous jobs,
pending trials and failed/uncertain journal references preserve diagnostic bytes.
Coherent complete/cancelled transactions permit removal after current boot/state
and backend postconditions are checked, retaining the real immutable-root/device
requirement and a ten-second subprocess observation deadline; historical terminal receipts and journal
are retained unchanged. Cleanup does not reconcile jobs or alter boot selection.

This original code fills ADR 0010's browser-to-private-intake gap. Retire it when
an upstream supported intake provides equivalent bounded transport, policy,
review and lease-preserving cleanup. Evidence and limits are in the
[browser upload record](../hardware/host-admin-upload.md); no physical deployment
or release acceptance follows from these offline tests.
