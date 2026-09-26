# RAUC staging environment review

Date: 2026-09-26. Status: constrained offline design approval; implementation
and joined QEMU verification remain in progress. No printer storage was written.

## QEMU finding

The first signed-feed QEMU integration reached the actual RAUC installation
path and wrote the disposable inactive boot/root pair. Its acceptance check
then failed because the stock RAUC U-Boot handler changed `BOOT_ORDER` from
`A B` to `A` during staging, before the separate transaction arm. No automatic
primary activation occurred. This is a failed QEMU acceptance run, not passing
evidence for unattended updates.

The distinction is important: RAUC's `activate-installed=false` prevents
automatic activation, but the stock U-Boot handler still marks a target bad by
removing it from `BOOT_ORDER` and setting its attempt counter to zero before
writing. This behavior is visible in the pinned source at
[`src/bootloaders/uboot.c` (RAUC 1.15.2 commit
4fb7c798)](https://github.com/rauc/rauc/blob/4fb7c798d6ae412344fb8f8d310d773046af3441/src/bootloaders/uboot.c).

## Reviewed custom-handler constraint

An independent delegated review approved offline use of RAUC's documented
custom bootloader interface, subject to the following checks. The interface
and argument contract are documented in the [RAUC 1.12 integration manual,
Custom Bootloader Backend](https://rauc.readthedocs.io/en/v1.12/integration.html#custom).
Both sources were accessed 2026-09-26. Review session:
`rauc-env-preservation-review-20260926`; approved proposal SHA-256
`c6bcfa54d6d5a383575e56473649ee32aa1d477e03f9913d552203639d139436`.

- During an install, `set-state <target> bad` may be an exact no-op only after
  it verifies that the target is absent from `BOOT_ORDER`, its counter is zero,
  the running source remains selected, and both redundant environment copies
  have valid CRCs and the reviewed layout. Otherwise it must fail before any
  slot write.
- Exercise the actual signed RAUC installation through the custom handler.
  Hash both environment copies before and after staging, prove only the
  inactive boot/root pair changed, and verify arm performs only the separately
  reviewed boot-selection delta. Cover handler error, interruption and
  repeated calls.
- Preserve the RAUC primary/state operations for explicit arm, health
  confirmation, cancel and fallback. Record the stock-backend deviation, the
  pinned RAUC interface provenance and the condition for retiring the helper.

The newly implemented handler is fail-closed when an install target is still
bootable and uses transaction operation markers for explicit environment
mutations. The joined QEMU rerun later verified those properties during the
signed A-to-B and B-to-A staging sequence; see the evidence record below.

## Owner-authorized repeated-update policy

The measured H10 environment initially selects A and excludes B, so the first
A-to-B stage can satisfy the no-op condition. After B is confirmed healthy, A
may remain bootable as the fallback. A subsequent B-to-A stage requires A to be
explicitly disarmed before overwriting it. On 2026-09-26 the owner authorized
that bounded policy change (“Allow pre-disarm”). This supersedes the previous
unchanged-policy restriction for the inactive target only; the currently
running source must remain selected and bootable throughout.

The revised sequence is:

1. Authenticate and fully inspect the exact signed bundle, acquire the existing
   state/upload/admission/writer locks, and verify the running source and target.
2. Durably journal `preparing`, including the exact source, target, boot ID and
   prior recognized boot environment values, before the boot-policy write.
3. Disarm only the inactive target, then verify source remains primary and
   bootable, target is absent from `BOOT_ORDER` with attempts zero, and both
   redundant environment copies remain CRC-valid. Record `installing` durably
   before invoking RAUC.
4. During RAUC's install callback, accept its `set-state target bad` only as a
   verified no-op. Hash both environment copies across staging and require
   byte-identical copies; verify only the inactive boot/root pair changed.
5. Arm the target in a separate journaled operation after the existing checks.
   On B-to-A, B remains the selected known-good source while prior fallback A
   is disarmed and overwritten. A is not rearmed until the later activation.

The independent proposal review approved this exact acceptance revision
(`561f96597efd0249003108c85d3accc42b2271ab3b9c5d1a9ea23b3840d354d1`), subject
to these fail-closed recovery details:

- A `preparing` journal may restore policy only when the same recorded source
  and boot identity remain active, and the environment is byte-for-byte either
  the recorded prior policy or the exact expected post-disarm policy. Any
  changed attempt count/order, invalid environment copy, or unknown mutation
  keeps the target disabled and requires reconciliation.
- Before RAUC is called, verify the exact disarm delta, preserve every source
  setting, and validate both environment-copy CRCs. Fsync the `preparing`
  journal before environment writes and fsync `installing` before calling
  RAUC. Exercise A-to-B-to-A and injected failures at each durable boundary;
  never restore the target after installation may have begun.

This approval covers the offline bounded proposal only. It is not a code
review, artifact approval, release decision, or authorization for physical
boot-policy/eMMC/MCU writes. The reviewer must independently inspect the final
diff and QEMU evidence before delivery is marked verified.

Crash handling is phase-specific. A crash in `preparing` proves RAUC was not
called: reconcile may restore the journaled prior policy, with the original
source selected, then terminate the transaction. A crash after durable
`installing` is uncertain even if no slot bytes appear changed; never restore
the old target policy, leave the source selected and target disabled, and
require explicit reconciliation/cancel. A partially written target is never
reintroduced as bootable. Tests must inject failures on both sides of the
disarm, journal transition and first slot write, then complete repeated A-to-B
and B-to-A cycles.

This revised acceptance is approved for offline implementation under the
constraints above. It does not authorize physical boot-policy writes. A
separate high-consequence review and deployable-board evidence remain required
before physical testing.

An initial joined-QEMU attempt reached A-to-B install but failed the B health
probe because the fixture's generated `/etc/fw_env.config` bind mount was
writable, which the real RAUC service-identity check correctly rejects. The
fixture now remounts that test-only file read-only. The final joined six-boot
QEMU run passed A-to-B, health-confirmed B, B-to-A using the approved
pre-disarm, three bounded failures of the deliberately unhealthy A trial, and
fallback to B with the failed transaction canceled. It also checked environment
copy integrity and staging/arm deltas, active-source preservation, unchanged
GPT and recovery partition, and a persistent user-data sentinel. Full output and
per-boot hashes are recorded in
[the QEMU evidence record](host-unattended-update-qemu-evidence-20260926.json).
This is disposable ARM64 QEMU evidence only; the host test selected each slot
and passed it on the kernel command line. It does not prove automatic H616
SPL/U-Boot selection or physical behavior, and it does not establish a
full-device eMMC image writer. The existing SD/NFS diagnostic remains
read-only.
