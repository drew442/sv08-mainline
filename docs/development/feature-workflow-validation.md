# Offline workflow validation

Date: 2026-09-12. Scope: workstation coordination and separate live review.
Product-pilot implementation and physical acceptance are recorded separately in
the [media export](../features/recovery-media-export/proposal.md) and
[readback improvement](../features/recovery-export-readback/proposal.md) records.
Both offline tasks are complete; the [pilot report](feature-workflow-pilot.md)
records delivery review, measured results and successful validation from a fresh
clone. Physical acceptance remains open.

## Deterministic checks and independent review

The 27 focused tests passed using disposable Git repositories, worktrees and real
file locks. A separate `workflow_review` session reproduced them and reviewed the
complete dispatcher, schemas and operating instructions. Review found and drove
corrections to approval scope, whole-change verification, integration history,
untracked-file admission and interruption ownership before pilot execution.

The final checks reject missing/stale proposal, requirement and task-scope
approval; self-verification; incorrect evidence environments; cycles and missing
dependencies; competing ownership; obsolete worktree bases; and incomplete or
uncommitted delivery. Verification covers the full clean implementation commit,
including files outside the explicit evidence hash map. Integration must preserve
that commit in history and its complete tree, apart from queue bookkeeping.
Changing an approved proposal, requirement or constraint invalidates its old
verification. Completed evidence remains verifiable after a normal clone and
after later legitimate source changes.

Worktree reads use the primary queue, while source hashing uses the requested
checkout. Worktree queue mutations are refused. Recovery requires the exact run
identifier and an explicit stopped-session attestation and preserves existing
files. A blocked physical task does not prevent independent ready offline work.

JSON Schema syntax, role TOML parsing, local Markdown targets, whitespace and all
seven indexed gitlinks against `upstream-lock.json` passed. Role configuration
inherits the selected model; permission defaults alone are not proof of isolation.

## Live proposal cases

The separate reviewer evaluated all five supplied proposals and returned
[sanitized results](feature-workflow-review-cases-20260912.json):

| Case | Decision | Reason |
| --- | --- | --- |
| Useful improvement | Approved | Reproducible redundant archive reads, bounded change and preservation checks. |
| Duplicate | Rejected | Another permanent GUI duplicates existing controls without demonstrated value. |
| Hardware assumption | Rejected; owner decision required | Unverified identity/clock assumptions and hardware authority cannot be inferred. |
| Owner conflict | Rejected; owner decision required | Existing 8 GB and writable-mode requirements remain authoritative. |
| Offline work despite a physical dependency | Approved | Independent offline regression work can continue while physical acceptance stays open. |

The reviewer independently reproduced the improvement baseline: a 9,123,840-byte
archive requires 18,242,915 logical read bytes across the existing two passes.
This is a small regression evaluation, not a statistical model-quality benchmark
or physical-storage speed measurement.

## Execution limits

The original native `codex-cli 0.153.4` trial accepted strict configuration,
read-only sandbox selection, JSONL output and a structured-result request. Its
read sandbox failed to initialize and a child launch reported a missing thread.
It exited zero with `{"results":[]}`; the workflow rejected that incomplete
result. The bubblewrap installation prerequisite is now closed: on 2026-09-27,
`bubblewrap 0.9.0-1ubuntu0.3` and `codex-cli 0.157.1` were present, and the CLI
started an ephemeral read-only session and returned a simple response. The
separate runtime-isolation warning remains open. A shell write probe did not
reach the command: bubblewrap reported
`loopback: Failed RTM_NEWADDR: Operation not permitted`, and the probe file was
absent. Rechecking on 2026-09-27 showed `kernel.unprivileged_userns_clone=1`
and `user.max_user_namespaces=56568`, but
`kernel.apparmor_restrict_unprivileged_userns=1`; an unprivileged probe still
failed to set up the UID map, and the kernel audit log recorded AppArmor denials
for `setpcap`, `net_admin`, and writes to `/proc/.../uid_map`. Thus installing
bubblewrap fixed the missing-package condition but did not enable native shell
sandboxing, enforced filesystem write denial, or custom-agent execution. Do not
disable the system-wide AppArmor restriction merely to clear this result; a
narrow, reviewed host policy or a runner that supports the required namespaces
is still needed. A privileged `sudo bwrap` smoke test does not establish the
unprivileged Codex sandbox. Raw diagnostics remain in ignored
`local/feature-workflow/`.

The explicit separate-session collaboration fallback completed all five cases.
That client inherits its parent permissions, so read-only reviewer instructions
are not an enforced sandbox. The dispatcher launches no processes and grants no
additional isolation. No printer or private backup access was needed. Unattended
scheduling remains disabled; deployment requires a restricted runner whose actual
permissions are verified. The attended offline pilot completed using separate
implementer and reviewer sessions under these documented limits. Re-test the
native shell sandbox after the VM permits the required unprivileged namespace and
loopback setup; do not treat package installation or a privileged smoke test as
closure of that remaining isolation check.

Repeat the deterministic checks with:

```sh
python3 -m unittest discover -s tests -p 'test_feature_workflow.py'
python3 scripts/feature_workflow.py validate
python3 scripts/feature_workflow.py check-review-cases \
  --result docs/development/feature-workflow-review-cases-20260912.json
```
