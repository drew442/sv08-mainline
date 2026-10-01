# H616 claim startup implementation evidence — 2026-10-01

Status: implementation checks complete; **ready for independent delivery review**.
Independent feature verification has not run. The purpose regression now passes
with the repaired disposable fixture. Do not build a physical candidate before
the required independent review.
Baseline: `be043559bccf8bfa5449c078475240c721293c72`.

Scope follows the [approved proposal](../features/h616-claim-startup-readiness/proposal.md)
and all constraints in its [decision record](../features/h616-claim-startup-readiness/record.json).
Only the writer, new startup test and this document changed. No hardware profile
was exercised. Board revision and physical RNG errno remain unknown. EAGAIN is
an implemented failure mechanism, not an established cause of job C; TCP failure
remains an alternative. No claim service, job provisioning, remote connection,
media operation, physical image construction or full-write QEMU run occurred.

## Behavior and compiled tests

`random_challenge()` uses one CLOCK_MONOTONIC deadline 60 seconds from entry,
checks each acquisition and sleep retry and checks completion before encoding.
It retains exactly 32 bytes from getrandom(GRND_NONBLOCK). EAGAIN and EINTR
are paced with at most 100 ms sleep requests bounded by remaining time;
interrupted sleeps retain their remainder, with zero remainder ending the pause.
Clock/sleep errors, permanent RNG errors, zero reads and the exact deadline refuse.
Scheduler delays can delay process execution; no success is admitted at or after
the deadline. No alternate random source, seed, child helper or transport retry
was added. Signature verification, job timestamps, server expiry policy, marker,
target, finalizer, boot policy and default diagnostic remain unchanged.

Numeric stderr diagnostics identify CLAIM_RANDOM (including CLOCK, SLEEP and
TIMEOUT), SOCKET, CONNECT, SEND, RECV, RECEIPT and malformed REQUEST stages.
Socket timeout-option failure also refuses. Errno is captured before close;
zero-byte/protocol failures report zero. No diagnostic includes challenge,
request/response or key contents. The final REFUSED_OR_UNCERTAIN_CLAIM remains.

`tests/test_emmc_claim_startup.py` includes the production C translation unit,
injects syscalls/clock, and uses the checked-in public synthetic signing fixtures
with the unchanged real Monocypher verifier. Three unittest methods cover 42
scenario invocations: ten successes, twelve RNG failures through both claim_once
and production main, and eight transport/protocol failures. They check immediate,
EAGAIN, EINTR, partial/partial-EAGAIN acquisition, repeated interruption/timeouts,
clock failures at startup/retry/completion, zero/permanent error, sleep failure,
interrupted/zero-remainder sleep, exact and just-before deadline, remaining-budget
pacing, partial sends, one request, captured errno and absence of sensitive values.
Injected production-main refusals reach the final marker with no socket/connect/
send or downstream open. The main fixture uses synthetic commissioning mode;
physical preflight behavior is not claimed from that fixture.

Command (TMPDIR is assigned tmpfs; bytecode/cache creation disabled):

```sh
TMPDIR=/dev/shm/sv08-claim-startup-implementation-20261001 PYTHONDONTWRITEBYTECODE=1 timeout 180 python3 -m unittest -v tests.test_emmc_claim_startup
```

Final result: 3 methods / 42 scenarios passed in 1.098 seconds. Pytest was absent;
unittest avoids adding a dependency. Retained initial failures were a longjmp
clobber warning in the fixture and an overstrict prefix assertion after partial
send; each received its own diagnosed correction. Production logic was not
weakened to satisfy either assertion.

All 19 selected existing regressions now have passing evidence: reuse the 18
passes from the 9.377-second prior run and the single purpose-test pass from the
authorized continuation (0.018 seconds). This was not a fresh full-suite rerun.
Passing checks cover valid/forged/altered/wrong-key/wrong-job/stale/replayed and
malformed receipts; fresh/unavailable randomness; default diagnostic separation;
preflight transfer-import absence and rejected test bypasses; signed job expiry
and QEMU default guard; durable consumption, concurrency, fsync/interruption and
replay refusal. No socket-binding server tests ran under the no-network constraint.
Reuse unchanged [authenticated claim evidence](../hardware/host-network-emmc-authenticated-claim-qemu-20260927.md)
and [handoff evidence](../design/unattended-emmc-reimage-handoff.md) for historical
server/full/fault QEMU behavior; these are not reruns against this candidate.

The initially incomplete check was
`PhysicalPreflightTests.test_signed_job_format_is_a_purpose_boundary`.
Redirecting its temporary files to the assigned tmpfs triggered the real builder's
worktree-local input guard at its final negative build assertion (earlier signed
purpose assertions completed). The first bounded repair supplied an isolated
scratch project root but lacked `configs/images/host-ab.json`. Both failed
attempts and the original blocked handoff remain retained.

The coordinator authorized 180 additional seconds in the same lineage. The
continuation copied the unchanged checked-in host-ab.json into scratch/configs/images
and redirected only the test module and builder REPO constants to scratch. The
actual existing test created regular 0600 inputs under scratch/local using only
checked-in public synthetic signing fixtures. Production private_file and
safe_output_root validation, signatures, and every existing assertion remained
unchanged. The test passed on its first continuation run, including both signed
purpose admissions, cross-purpose refusals and negative builder calls; no candidate
output was built. Source/test/configuration hashes matched the prior evidence.
No production or tracked test edits were made during this continuation.

The single-test command was:

```sh
TMPDIR=/dev/shm/sv08-claim-startup-implementation-20261001 PYTHONDONTWRITEBYTECODE=1 timeout 120 python3 /dev/shm/sv08-claim-startup-implementation-20261001/purpose-continuation.py
```

The exact runner, output and result are retained as purpose-continuation.py,
purpose-continuation.log and purpose-continuation-results.json in the private
evidence directory. Fresh independent feature_verifier_high is the next step;
these are implementation test results, not independent acceptance.

## ARM64 build and resource accounting

Offline, static compile only: writer and preflight modes, trusted initramfs,
recovery handoff and existing v2 boot snapshot flags. No candidate output,
FIT, initramfs or physical signing material was provisioned. Existing build flags
were reused with public test key, synthetic hashes/times and compile-only identity
inputs; synthetic bypass flags were absent. The ELF purpose section distinguishes
signed-reimage-v1 from signed-preflight-v1. These ELFs are inert test inputs.

Compiler: `aarch64-linux-gnu-gcc (Ubuntu 13.3.0-6ubuntu2~24.04.1) 13.3.0`; native compiler same GCC
13.3.0 distribution. Configuration: `-static -Os -D_FORTIFY_SOURCE=2 -Wall
-Wextra -Werror -ffunction-sections -fdata-sections -Wl,--gc-sections`, existing
preflight unused-symbol exclusions and runtime_compile_flags. Exact argv,
synthetic definitions, input hashes and purpose bytes are in build-results.json.
Monocypher 4.0.3 remains pinned at
`ab2b16dd619ad5f6979a4fbe69cfa324a6fcc35f`, unchanged source/license hashes recorded
there. `verify_claim_receipt()` is unchanged byte for byte.

| ELF | Bytes | SHA-256 |
| --- | ---: | --- |
| before-writer | 781304 | `36a81db4c891fc79f3cc13ae1096bc1c0d2171971e734fb2a2ad476e27ee4049` |
| after-writer | 781704 | `9005cddd3c9faa41d6c88f720e7f69e5c94b8cd77867b60a4562726b8d965b6b` |
| before-preflight | 780088 | `f73cf7d6959d169dfcf0efba11fcc3084191e735dd320216f328cb1393e45ccf` |
| after-preflight | 780496 | `c9238b3ddbdb3819a9b54c8b92a5d6499114e3b1ca6595f79a7f4f7d03bef44e` |

Deltas are +400 bytes writer and +408 bytes preflight with matched build inputs.
The supplied prior job-C figures are FIT 48,902,464 bytes, compressed initrd
15,447,617 bytes and writer 780,104 bytes; they were not remeasured here and are
not identical to the synthetic baseline. Conservatively reserve the entire larger
new ELF plus 64 KiB (847,240 bytes), without subtracting the old ELF:
projected FIT <= 49,749,704, initrd <= 16,294,857; remaining
64 MiB FIT allowance 17,359,160 bytes. This is deliberately coarse
size accounting, not a new compressed artifact measurement or a general gzip bound.

Existing selector_intervals accepted this projection and full FIT reserve
[0x48000000,0x4c000000), kernel [0x40080000,0x4205ba00), marker at 0x4f800000,
environment buffers [0x4f900000,0x4f920000), selector [0x4fc00000,0x4fd00000),
and original script [0x4fd00000,0x4fe00000), without overlap inside the reviewed
1 GiB address range. The initrd and DTB remain within the FIT; bootm relocation
addresses remain unverified. Adding twice the growth reserve to the retained
565,644,272-byte conservative memory account gives 567,338,752 bytes,
leaving 506,403,072 of 1 GiB. Existing 7,818,182,656-byte image and
factory 8 GB layout are unchanged; no storage geometry or new runtime dependency
was introduced. These numbers cannot establish physical memory or boot reliability.

## Provenance, resources and handoff

Primary local sources accessed 2026-10-01: approved proposal/record above,
writer random_challenge/claim_once/verify_claim_receipt, ed25519_build.py source
pin, existing native tests, build_h616_reimage_candidate.py mode flags and
build_h616_recovery_handoff.py selector_intervals. Custom-code provenance and
retirement remain the [authenticated-claim proposal](../features/network-emmc-authenticated-claim/proposal.md):
retire this commissioning helper when a maintained upstream mechanism preserves
its complete contract. Rollback means withdrawing this candidate and keeping the
prior artifact, never rearming a consumed marker or claim.

Source and configuration SHA-256 values:

- `tests/fixtures/sd-network-root/emmc_image_writer.c`: `ea0167ee06ae8b5f6e38bd8416bdd926c2a183f560da2a4b5291f7022a6fc5ea`
- `tests/test_emmc_claim_startup.py`: `4dcf245e391cdda54b096464ce1d63f29e564cc8a8ce5947e93fc70dcc9e7fa9`
- `scripts/ed25519_build.py`: `bbf877cff8d8a24b5ef60e7b6faa986bd3090e03ee7897d7ac71caa1323e3bc3`
- `scripts/build_h616_reimage_candidate.py`: `ba9ec247df77e94c1f5481c400a8d03905cb3a330cb4e8285e35f425506ef5bd`
- `scripts/build_h616_recovery_handoff.py`: `eefc700b63dd69eacd75d2d92d1165e96548ac6ef112598b5a0ab36522c3af3f`
- `tests/test_h616_reimage_candidate.py`: `8561c580e620d010575917e19615cddd361e34a5c0be10cabe0bda7284367d74`
- `configs/images/host-ab.json`: `cb3a4844d03a3d8c7ae14aa0bd11daa0561a8cd9d34a3f4af0f5e7c7b401a599`
- `upstream-lock.json`: `1452835e9969d23aea61a0936806efc0e42a25b8a117206a984051c6a4beb440`

Private evidence directory (small JSON/logs and runner only):
`local/feature-workflow/probes/h12-sd-return-20261001b/fresh-preflight/claim-startup-implementation`
in the parent checkout. It retains build-results.json,
regression-results.json, per-check results.json, all failed and final logs,
checks.py, candidate.diff, implementation-summary.md and the three continuation
files above. Before-continuation snapshots retain the previous handoff, diff,
evidence document and results; the original regression-results.json is unchanged. Generated ELFs and
scratch stay in `/dev/shm/sv08-claim-startup-implementation-20261001`; measured
scratch is about 3.2 MB, below 32 MiB. No large files were placed on the root
filesystem. Primary allowance 600 seconds, each test/build command capped at
180 seconds (individual compiler calls 120 seconds); work began 11:58:49 UTC.
The first allowance was exhausted during handoff recording (at least 609 seconds).
The coordinator subsequently authorized 180 more seconds, without resetting prior
usage. Continuation started 12:12:57 UTC; results.json records its elapsed time
and the cumulative lower bound. Coordinator runtime accounting remains authoritative.
Actual runtime model/effort and billing are unavailable to the worker; coordinator
must record the requested temporary Astra/high exception's effective settings.
No agents, commits or shared-record edits were performed. Independent
feature_verifier_high and all physical H12 gates remain pending.
