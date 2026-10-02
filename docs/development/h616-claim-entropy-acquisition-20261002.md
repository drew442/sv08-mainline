# H616 secure claim acquisition — 2026-10-02

Status: **offline implementation ready for independent review; coordinator
supplemental namespace PID 1 interruption evidence passed**. No delivery
verification or physical acceptance is claimed. Baseline
`108c148c20b32f02ef4c148846a9a424df0f9e63`, detached candidate. Scope and constraints:
[proposal](../features/h616-claim-entropy-acquisition/proposal.md),
[approval](../features/h616-claim-entropy-acquisition/record.json).

The coordinator-authorized separate-session fallback packet/runtime identifies
`project_implementer`, GPT-6.1 Sol, medium, `danger-full-access`, approval `never`,
session `01a0fb06-1ca7-73b0-9272-49a31aff69ef`. Native agent launch was unavailable;
this is not a native role-loading test. Only the three assigned implementation,
test and evidence paths changed; no commit or workflow-record edit was made.

## Behavior

Before: secure `getrandom(GRND_NONBLOCK)` polling with paced temporary failures.
After: exactly 32 bytes from blocking `getrandom(..., 0)`, retaining partial
progress and retrying EINTR against the **same** CLOCK_MONOTONIC deadline,
60 seconds from entry including setup and cleanup. No seed, weak fallback,
provider/kernel change, busy readiness polling or deadline extension. Unexpected
EAGAIN, zero reads and permanent errors refuse. Clock failure and completion at
or after the deadline refuse, including cleanup that crosses the deadline.

The single-threaded helper temporarily owns libc's `SIGRTMIN`. It blocks that
signal while saving the inherited mask, refuses an already pending notification,
installs a caught no-op handler with no SA_RESTART, and uses a CLOCK_MONOTONIC
SIGEV_SIGNAL timer. The first absolute expiry is the original deadline;
notifications repeat every 100 ms. If the first is delivered between the last
clock check and blocking syscall entry, the next notification can interrupt that
call; no fresh acquisition deadline is established. The waiting mask unblocks
only this signal while retaining unrelated mask bits. Inherited blocked/ignored
states do not silently disable cancellation.

Cleanup blocks the owned signal, disarms and deletes the timer, drains pending
notifications with zero-timeout sigtimedwait, then restores the saved disposition
and mask. Draining is capped at eight calls, including unrelated EINTR/flooding;
uncertainty refuses rather than spins. Every cleanup failure refuses before
transport and avoids restoring unsafe signal state where possible. No uncertain
cleanup authorizes a socket or downstream target open. Successful cleanup is
required before the final admission clock check. This is a trusted standalone
init helper, not a reusable multithreaded library or shared-signal reservation API.

Successful cleanup prevents an owned timer notification from affecting transport
or the unchanged finalizer. A cleanup-error refusal retains the caught/blocked
signal state where possible and uses the existing refusal finalizer, not a retry
or an alternative child-supervision design. Arbitrary simultaneous kernel API
failures are not proven recoverable; physical acceptance still requires review.

The 100 ms period is **not a hard real-time cancellation bound**: scheduler
latency, syscall/kernel responsiveness and process descheduling can delay refusal.
The local real-interruption fixture requires refusal within two seconds for its
one-second deadline (at most one second cancellation latency). Production never
admits late secure completion even if cancellation execution is delayed.

Diagnostics retain numeric errno and stage only: RANDOM, RANDOM_CLOCK,
RANDOM_TIMEOUT, RANDOM_SETUP and RANDOM_CLEANUP. No random/challenge/request,
response or signing material is logged; the final REFUSED_OR_UNCERTAIN_CLAIM
marker remains. Receipt verification, claim_once and every downstream byte are
unchanged from baseline (recorded extraction/hash comparison). Thus signed
purpose, expiry, identity/marker/unmount, one claim request, whole-target
admission, recovery, persistence, A/B policy and heater protections are unchanged.

## Evidence levels and results

All checks are offline. No hardware profile was exercised.

1. **Deterministic compiled production helper:** three unittest methods / 80
   scenario invocations pass: ten successes, 31 refusals exercised through both
   claim_once and production main, eight transport/protocol refusals. Coverage
   includes partial/EINTR progress, repeated unrelated EINTR, unavailable/zero/
   permanent/EAGAIN results, exact and just-before deadlines, expiry during setup
   and cleanup, pre-syscall delivery, pending expiry/completion, inherited mask/
   disposition/pending state, clock/setup/cleanup failures and bounded drain
   errors/flooding. Successful transport requires 32 timely bytes plus complete
   cleanup; refusals assert no socket/connect/send or downstream target opens.
   Existing earlier read-only identity/marker handling is not reclassified.
2. **Real ordinary-process interruption:** static x86_64 glibc fixture includes
   the actual helper and uses real timers, handlers, masks and cleanup. Only
   getrandom is substituted with a genuinely blocked pipe read; its write end
   remains open. The initial clock observation alone is shifted by 59 seconds,
   leaving the production 60-second arithmetic and absolute timer unchanged but
   creating a one-second fixture wait. Inherited caught/SA_RESTART and ignored
   dispositions, an inherited blocked mask, and first expiry delivered before
   blocked syscall entry are exercised. Results: 1.000062105 s caught,
   1.000055508 s ignored, 1.100052764 s lost-wake; each blocked read returned
   EINTR. Restored mask/disposition are checked, followed by 250 ms unmasked
   observation with a handler that fails on a late notification.
   This is **not an actual unready-getrandom experiment**.
3. **Initial unprivileged namespace PID 1:** unavailable. `unshare --user --map-root-user --pid --fork`
   failed before executing the fixture with
   `write failed /proc/self/uid_map: Operation not permitted`. Initial failures
   and JSON evidence are retained. One bounded harness correction recognizes
   this precise namespace-startup failure as unavailable and stops the mode loop;
   it does not convert helper failures to skips or waive physical acceptance.
   Final unittest result: five methods in 5.971 s, four pass / one unavailable
   skip. Kernel `7.0.0-31-generic`, architecture x86_64, static native glibc
   `2.39-0ubuntu8.9`. Neither namespace PID 1 nor global init was exercised.
   No privilege escalation, sandbox wrapper, service change or QEMU run occurred.
4. **Actual-source secure randomness/receipt:** two existing tests passed in
   2.628 s: real ready getrandom produced distinct 32-byte challenges; injected
   no-random refused; valid receipt and forged/altered/wrong-key/wrong-job/
   wrong-descriptor/stale/replay/malformed framing checks passed. Their source
   and fixture keys are unchanged; temporary paths alone were redirected to
   assigned scratch.
5. **Reused unchanged evidence:** retain the historical 42-scenario startup and
   19 selected receipt/default-diagnostic/purpose/durable-state results in the
   [October 1 evidence](h616-claim-startup-readiness-20261001.md). The old polling
   acquisition cases are historical, not proof of the new wait. Changed
   acquisition/cleanup and unchanged transport assertions have fresh coverage
   above; purpose/default/finalizer and durable server evidence were not rerun.
   Receipt implementation and existing regression-file hashes match that record.
   Reuse the [authenticated claim QEMU evidence](../hardware/host-network-emmc-authenticated-claim-qemu-20260927.md)
   and [handoff evidence](../design/unattended-emmc-reimage-handoff.md) for unchanged
   full/fault/abrupt/server behavior, not as reruns against this candidate.

Commands (all temporary files/caches directed to the assigned packet directory;
Python bytecode disabled for test/build runs):

```sh
# S = local/feature-workflow/probes/h12-preflight-renew-20261002b/implement-entropy
TMPDIR="$S/tmp" SV08_ENTROPY_EVIDENCE_DIR="$S" PYTHONDONTWRITEBYTECODE=1 timeout 90 python3 -m unittest -v tests.test_emmc_claim_startup
TMPDIR="$S/tmp" PYTHONDONTWRITEBYTECODE=1 timeout 150 python3 "$S/build-checks.py"
```

The first build invocation compiled all four ARM64 binaries, then failed only
while serializing purpose bytes as JSON. Its log/resources remain retained. One
bounded repair added bytes serialization and reused those unchanged successful
binaries rather than recompiling; it also ran the two selected regression tests.
Its timeout was 90 seconds. No production code was changed for this repair.

## ARM64 builds, hashes and headroom

Matched before/after static `-Os -D_FORTIFY_SOURCE=2 -Wall -Wextra -Werror`,
function/data sections and gc-sections. Both ordinary write and preflight modes
include trusted initramfs, recovery handoff and existing v2 snapshot flags, with
compile-only synthetic values/public fixture verifier and expired job times.
No synthetic runtime bypass, real job, physical candidate, initramfs or FIT was
built. Purpose sections remain signed-reimage-v1 versus signed-preflight-v1.
Compiler: GCC 13.3.0 (`Ubuntu 13.3.0-6ubuntu2~24.04.1`); ARM64 static libc package
`2.39-0ubuntu8cross1`. Exact argv, flags, sources, libc hashes, purposes and ELF
identification are retained in build-results.json. Crypto uses
scripts/ed25519_build.py inputs, unchanged Monocypher 4.0.3 pin
`ab2b16dd619ad5f6979a4fbe69cfa324a6fcc35f`; no dependency/source/license update.
The timer APIs pull additional existing static libc code, not an installed
runtime dependency or a production child/thread supervisor.

| ELF | Bytes | SHA-256 |
| --- | ---: | --- |
| before-writer | 781696 | `36f7ccaba126c88912848db473baa07bfcd68d9f3e18a69162c56463a540c3e4` |
| after-writer | 865976 | `5b4fe0813768122c7efe401ed453f6683af3dbefa4f64b64572f7b122b8da424` |
| before-preflight | 780480 | `a6948d14e46256b4284188b4a404cef83ae994394e0222d1d81a5315630a65d1` |
| after-preflight | 864744 | `94a24b0df0cc6cb85a557fa856ac265c44ac4ffc21fd45da77ff43f4180e414c` |

Matched growth: 84,280 / 84,264 bytes. Conservative projection reserves the
entire larger ELF plus 64 KiB (931,512 bytes), without subtracting the old ELF.
Using retained job-C FIT 48,902,464 and initrd 15,447,617 bytes gives projected
FIT 49,833,976 and initrd 16,379,129; 64 MiB FIT headroom is 17,274,888 bytes.
These are static allowances, not measured compressed-artifact bounds.
Existing selector_intervals accepts the projection and full FIT reserve
[0x48000000,0x4c000000), kernel [0x40080000,0x4205ba00), marker 0x4f800000,
environment buffers [0x4f900000,0x4f920000), selector
[0x4fc00000,0x4fd00000), original script [0x4fd00000,0x4fe00000) without overlap.
Adding twice that reserve to retained conservative memory 565,644,272 gives
567,507,296 bytes, leaving 506,234,528 of 1 GiB. Physical bootm relocation,
allocation/reliability and entropy availability remain unverified. The
7,818,182,656-byte image and factory 8 GB layout are unchanged.

Source hashes:

- writer: `83a7c1d4d385109afa79521f2bab059443cc4c7e1e1b7168856aadf3147540cb`
- startup tests: `b9f6e1697cc66d59d13253a4ca8e6aa17e7977f9a2de17a73bab39a79bb599e2`
- deterministic native fixture ELF: `25ef857601d71b2dac4563bb7449595ed3ba99fe1227d93be3a23a213044e8b4`
- real interruption fixture ELF: `19b8d3728ea483a095a152aa6cfd96f5a554fa324e03a728225e7f48986b1c80`

Compile source hashes and remaining configuration/crypto/runtime provenance are
in the packet JSON files, bound to the writer hash above. Native temporary
fixture ELFs were cleaned normally after recording their hashes; ARM64 comparison
ELFs remain in assigned scratch.

## Resources, provenance and next action

Packet evidence: ignored parent-checkout
`local/feature-workflow/probes/h12-preflight-renew-20261002b/implement-entropy`.
Retained logs include acquisition-1.log, failed acquisition-2.log, final
acquisition-final.log, failed build.log and successful build-repair.log, with
per-mode JSON and build/resource records. No failed observation was overwritten.
Measured test/build process elapsed totals about 20.3 s across all attempts;
maximum measured RSS 61,036 KiB. Retained packet/scratch was 3.7 MiB with
419 MiB filesystem free after checks. Cumulative generated bytes are not exactly
instrumented for the first two runs; compiler outputs/temporary files, logs and
caches are conservatively accounted below 32 MiB, well below the 128 MiB cap.
Three small accidental Python bytecode files from the hash-comparison command
were identified and removed; no other's files were removed. No incidental
probes were used outside the primary tests/builds. Work began 05:11 UTC;
primary allowance 25 minutes, test/build allowance 600 seconds.

Primary local provenance accessed 2026-10-02: approved packet/proposal/record,
production writer, startup and candidate test sources, ed25519_build.py,
existing compile-mode and selector interval helpers. Upstream Linux
random.c/signal.c behavior is the source analysis retained in the approved
record, not newly measured board behavior. The October 2 physical ETIMEDOUT
observation does not prove individual EAGAINs, provider identity, entropy
readiness or preflight PASS on owner-reported H616_JC_6Z_V1.2. Do not infer
unknown hardware facts. Custom-code retirement remains the
[authenticated-claim proposal](../features/network-emmc-authenticated-claim/proposal.md):
withdraw this commissioning helper when a maintained mechanism preserves its
whole contract. Rollback withdraws the new candidate, retaining original failed
and historical artifacts; it never rearms a consumed claim/marker.

Smallest next action: coordinator obtains fresh independent delivery review of
the full diff/evidence and a bounded installed Linux PID 1 fixture where namespace
creation is supported. Missing PID 1 evidence blocks physical preparation, not
this offline candidate. Physical H12 still separately requires fresh authenticated
single consumption, preflight PASS, original recovery return and exact-operation
review/authorization. No hardware/network/credential/remote-host, global-config,
model, agent, service, media or boot-policy operation was performed.


## Coordinator supplemental PID 1 evidence

After the implementer preserved the user-namespace failure, the coordinator ran
its same static interruption fixture using existing passwordless local sudo and
`unshare --pid --fork`, without a user namespace. This is a Linux PID namespace
init test on x86_64 kernel `7.0.0-31-generic`, static glibc 2.39; global boot init
and ARM64 runtime were not exercised. The actual production writer hash matches
this candidate. No host setup, services, printer or media changed in this check.

Caught/SA_RESTART, ignored/blocked and lost-wake cases each exited zero with
`pid=1`, the expected refusal diagnostic and one genuinely blocked pipe read
interrupted by the real timer. Measured acquisition elapsed times were
1.000059868, 1.000057971 and 1.100059513 seconds; the fixture uses its original
one-second budget and a two-second refusal limit. Mask/disposition restoration
and the subsequent 250 ms absence of late notifications were checked. This
closes the missing namespace PID 1 evidence for this mechanism at the stated
scope; it does not demonstrate an unready secure getrandom call or hardware
entropy availability. Existing user-namespace failures remain preserved.

Private build/hash and per-case command/stdout/stderr/kernel evidence is under
`local/feature-workflow/probes/h12-preflight-renew-20261002b/coordinator-pid1/`.
Supplemental runtime was under ten seconds and one small temporary static binary;
there was no additional production-code change or test rerun by the implementer.
Independent delivery verification and fresh physical H12 acceptance remain open.
