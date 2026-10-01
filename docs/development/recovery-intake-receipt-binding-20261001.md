# Recovery intake receipt binding — implementation evidence

Date: 2026-10-01. Baseline: `bba38ebf8b94ff8765065bc59d50d1ee0905b7c7`. Local sources accessed
2026-10-01. This is author-produced offline implementation evidence; independent
delivery verification remains with the coordinator. Effective model/effort is not
exposed to this worker; the coordinator owns the actual Sol6.1/low observation.

Authorized by the [approved proposal](../features/recovery-intake-receipt-binding/proposal.md)
and its [record](../features/recovery-intake-receipt-binding/record.json), within
[ADR 0014](../decisions/0014-independent-compressed-recovery.md) and
[ADR 0010](../decisions/0010-host-administration-and-recovery-ui.md).
Planner source: parent `local/feature-workflow/probes/required-recovery-plan-20261001/plan.md`.
Accepted requirements, workflow records and pins were not edited.

`intake()` reads lock bytes once, hashes that buffer and parses the same buffer.
After archive size/hash verification it compares the current lock content digest
with the captured digest. Changed, deleted or unreadable completion input raises
an explicit refusal; success returns the captured digest in the existing receipt
shape. Verified partial archives may remain after continuity refusal; the existing
fresh-output check prevents silently reusing that directory.

Content identity applies at the completion comparison. Same-byte replacement can
pass. This does not exclude later pathname changes, detect A-to-B-to-A replacement,
authenticate provenance or prevent later archive tampering. No assembly, download
or path handling redesign was introduced. Everything outside `intake()` in the
production source is byte-identical to baseline, including assembly control/archive,
completion continuity and integration-input freshness gates. A changed builder
still requires fresh downstream assembly; historical receipts must not be rewritten.
Custom builder retirement remains ADR 0014's supported image-builder integration.

Before/after actual-intake comparison used a 12-byte archive in a mocked BytesIO
response. The response deterministically atomically replaced A with valid B during
consumption. Baseline succeeded naming B (`f251a533f4bd04a48977784d130de1255d256479ee70b9635fd95edcef1afbb2`)
although parsed A was `dcc8562d5b2ceca7b2da476ab803b561f30c87356979803752cfdf47b9821569`. Candidate
raised `Lock content changed during intake` with no returned success receipt.
Each case made one mocked urlopen call; no real network was used.
The durable baseline remains in git. The small comparison recipe is assigned scratch
`/dev/shm/sv08-intake-implementation-20261001/compare.py`; it loads baseline via
`git show HEAD:scripts/recovery_image.py` and candidate from the worktree, using the
same `IntakeTests` fixture and asserting the two distinct outcomes.

Commands and results:

- `TMPDIR=/dev/shm/sv08-intake-implementation-20261001 PYTHONDONTWRITEBYTECODE=1 timeout 20 python3 /dev/shm/sv08-intake-implementation-20261001/compare.py`: baseline false success, candidate explicit refusal.
- `TMPDIR=/dev/shm/sv08-intake-implementation-20261001 PYTHONDONTWRITEBYTECODE=1 timeout 45 python3 -m unittest discover -s tests -p test_recovery_image.py -v`: 23 tests passed, 0.602 seconds reported.
- `git diff --check` and `git diff --cached --check`: passed.
- `git submodule status`: eight uninitialized submodules; no source checkout required.
- Parsed `upstream-lock.json` and compared all indexed mode-160000 gitlinks: eight match.
- Exact baseline/candidate comparison outside the intake function: byte-identical.

Focused coverage includes stable exact-byte receipt, replacement immediately after
initial capture, during download and after completion comparison, deletion,
simulated PermissionError, same-byte replacement, inspection without output/network,
unprivileged/fresh-output refusal, actual-intake symlink/raw-target/overlap/outside-build
refusals, invalid identity, three-attempt size/hash/network exhaustion and partial
archive cleanup. Existing small assembly regressions check archive/control identity,
inspection and stale build inputs. Assembly execution/completion was not rebuilt
or newly exercised; its unchanged implementation is preserved, not newly certified.
Existing VM-harness refusal tests run Python argument checks only, with a sparse
512 MiB logical file (negligible allocated data), and never start QEMU.

Fixture REPO/build storage and integration-input constants are temporarily redirected
in affected tests, retaining production guards and original source-input fingerprints.
All temporary directories use assigned TMPDIR during these commands. All archive
payloads are tiny; bytecode is disabled. No hardware profile was exercised, and no
hardware, credentials, services, full image build, VM boot, commit, publication or
agent launch occurred. Physical G4/H04/H07/H12 work remains open.

Source SHA-256:

- Baseline builder: `a96d60d7c3366ae73ccf7f131dc69116fccec8405282e0e4606eb0a4df6de156`.
- Candidate builder: `c89591d8661a05bd4cdb6ce28aee5dfcd4c983b7f66b5e7efb505b67dc731279`.
- Candidate tests: `5132a9d48038ea8736bbe331b0eb335015db69d8621935f5706b5a988507571c`.

Allowance: primary 360 seconds; tests 120 seconds, cumulative unittest reported
runtime 1.194 seconds (first 21-test run 0.592, final 23-test run 0.602).
Two bounded comparison invocations and an initial baseline invocation are primary
evidence work, each below 0.1 seconds process wall time; no auxiliary diagnostic
probes used (0/2, 0/120 seconds). Scratch cap 32 MiB allocated; no broad builds.
Session wall time is not independently measured by these process timers.
Small private `results.json` and `summary.md` are in the assigned parent
`local/feature-workflow/probes/recovery-intake-receipt-binding-20261001/implementation/`.
Coordinator must commit the reviewed candidate before verifier submission; this
worker neither commits nor independently accepts its own delivery.
