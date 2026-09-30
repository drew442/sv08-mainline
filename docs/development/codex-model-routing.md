# Benchmark-grounded agent routing

Date: 2026-09-30. Base project revision: `98808f125e1036e800794526d5f139ed1365d65f`.
This supersedes the narrow low-effort pilot in PR #1's first draft. The owner has
accepted the supplied benchmark results as a sound basis for changing routing and
asked for role definitions to be reconsidered. Deployment still needs independent
review and a source-only runtime check; no live model results are claimed here.

## Evidence and interpretation

Source: owner-supplied Artificial Analysis Terminal-Bench 4.0 chart exports dated
29 Sep 2026, visually transcribed into [this CSV](terminalbench-20260929.csv).
The [original evaluation](https://artificialanalysis.ai/evaluations/terminalbench-4-0)
is the source site, not a claim that this revision downloaded a raw dataset.
Values are rounded chart labels. Empty times were not displayed, not zero.
`none` transcribes the chart's Non-reasoning label; it is not a supported Sol 6.1
setting. No compute-proxy inference or cost reconstruction from token rates is used.

| Configuration | Score | USD/task | Output tokens/task |
| --- | ---: | ---: | ---: |
| GPT-6.1 Sol low | 30.8% | $0.38 | 17k |
| GPT-6.1 Sol medium | 48.0% | $0.61 | 32k |
| GPT-6.1 Sol high | 51.5% | $0.83 | 44k |
| GPT-6.1 Sol xhigh | 54.0% | $1.03 | 57k |
| GPT-6.1 Sol max | 56.1% | $1.82 | 108k |
| GPT-6 Sol medium | 18.7% | $1.12 | 28k |
| GPT-6 Sol xhigh | 30.3% | $1.91 | 51k |
| GPT-6 Luna medium | 2.5% | $0.07 | 45k |
| GPT-6 Luna high | 4.5% | $0.12 | 74k |

From those displayed values, Sol 6.1 low gains 12.1 percentage points over old Sol
medium at 66.1% lower cost/task. Its observed score is close to old Sol xhigh, at
80.1% lower cost/task. Sol 6.1 medium buys another 17.2 points for $0.23/task.
That supports low for bounded engineering and medium for harder work, not equal
effort labels across generations. Luna high is not a default intermediate rung.

Cost/task divided by score-as-a-fraction gives aggregate spend per successful
benchmark outcome: about $1.23 for Sol 6.1 low, $1.27 for medium, $2.80 for Luna
medium and $2.67 for Luna high. This includes failed attempts in the workload; it
is not the expected cost of repeatedly retrying one task. It does not identify
which tasks different models solve or establish a cheap-first fallback strategy.
Scores do not give role-specific reviewer accuracy or statistical significance.
The similar 30.8%/30.3% values are not proof of one model's superiority.

Time is weighted average decode time, excluding time-to-first-token and overhead,
not end-to-end build/VM latency. Output counts include reasoning and answer tokens.
Benchmark USD is not the user's included Codex allowance or observed project cost.
Actual totals include coordinator work, children, rework, tools and review. Never
turn missing usage into zero or double-count reasoning already in output totals.
These charts justify defaults now; ordinary accepted-outcome measurements refine
them rather than an easy-task-only pilot blocking the improvement.

### Screenshot provenance

SHA-256 values identify the supplied exports, not files included in this repository.
Hashes alone do not make the images retrievable. The CSV and this attribution are
the public evidence snapshot; keep the original exports with the review evidence.

| Export filename | SHA-256 |
| --- | --- |
| Terminal-Bench 4-0 - Score (29 Sep '26).png | `2bd44bc404eab9240738318d500c49cf4402a672bbde6da305a6daaf23a90af2` |
| Terminal-Bench 4-0 - Cost per Task (29 Sep '26).png | `3dace4fb9f9bcb0dd22214e2a8d29967225bf84bcc9e14f227fc5986d8002638` |
| Terminal-Bench 4-0 - Output Tokens per Task (29 Sep '26).png | `aba7ce6197ebd4eda3201c87b590c04940be65dd98cae5c69cea936f5c65e559` |
| Terminal-Bench 4-0 - Time per Task (29 Sep '26).png | `bbfbc32b3927ac99955df44076bf848d49ac6ac95944c07cabe5f6c65176fd9a` |

## Definitions: responsibility is not effort

The [agent guide](../../.codex/agent-guide.md) is the authoritative role table.
Use native configuration, not a custom router, scheduler, model classifier or a
Cartesian product of every responsibility and every effort. Eleven selectable
profiles cover cheap utility work, analysis/planning, execution and independent
review. Different role names do not imply more simultaneous agents.

Replace cheap broad research with two contracts: Luna exact lookup and Sol causal
investigation. Replace feature suggestion with an optional medium planner that
can plan existing approved delivery as well as triage new work. The planner does
not approve its output. Remove the duplicate routine implementer: ordinary Sol
implementation starts at low and can request more effort for harder assignments.
Remove the test-runner role: a predetermined script needs no agent; bounded
integration judgment uses Sol low, complex diagnosis medium. Keep Luna mechanical
editing only where a supplied transformation makes verification straightforward.

For research, implementation and integration, pin the Sol model but deliberately
leave profile effort unset. [Project agent defaults](../../.codex/config.toml)
provide low, while a supported explicit spawn effort can select medium/high. This
uses the official [subagent precedence](https://learn.chatgpt.com/docs/agent-configuration/subagents)
and [configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference),
checked 2026-09-30. Planner, Luna and reviewers remain effort-pinned. Their explicit
high variants are necessary because spawn values cannot override pinned effort.
The [model reference](https://developers.openai.com/api/docs/models/gpt-6.1-sol)
lists low/medium/high/xhigh/max; availability in the target account still needs a
runtime check. No model's self-reported identity is evidence of effective settings.

A low-effort fixture patch in a storage module may be appropriate; deciding a new
write policy requires planning/approval, and physically writing storage requires
its own authorization and immediate action review. More effort grants no extra
permission. Review difficulty and cost of a missed defect justify medium/high
review independently of the worker's setting. A planner, author, approver or evidence
producer is not reused as the independent delivery verifier. No independent review
or hardware gate is removed. Medium/high review variants are alternatives, not
an automatic two-review sequence. Xhigh/max have no standing definitions: request
exceptional bounded work explicitly, and add a variant only if recurring need is shown.

Examples: exact symbol extraction goes to lookup or grep; a scoped boot-log code
trace to research/low; a tested recovery-parser bug fix with settled behavior to
implementer/low; unresolved A/B transition design to planner/medium and research at
an appropriate effort; fixed QEMU commands run directly, but an unexpected installed
user-journey failure goes to integration/low or medium according to complexity.
A physical write still needs the separate operation review and actual permission.

## Deployment and rollback

Keep the PR in draft for independent review and runtime loading checks, not for
proof of a large cost-saving pilot. In a fresh authorized source-only client check:
all active names; removed names no longer selected; generic child defaults Sol/low;
adjustable workers default low and actually accept medium/high spawn effort;
pinned reviewers resist lower-effort overrides; named high variants run at high;
permissions are enforced by the environment, not merely requested in TOML.
Do not run printer operations, open credentials or switch billing to make this pass.

If a client cannot apply the defaults/override, use a separate explicitly configured
session with the same contract and record the actual fallback. No silent model or
review downgrade is allowed. Unavailable independent review remains pending.
User-global/main-session model, billing account, speed mode, concurrency cap,
dispatcher, historical decisions/hashes, upstream pins and schedules are unchanged.
Only default spawned-agent model/effort is newly set at project level.

After those checks, use the normal routing immediately on representative authorized
work. Keep lightweight observations and detailed [samples](../../.codex/templates/agent-task-observation.md)
for escalations/failures. Compare total cost through acceptance, first-pass results,
rework, elapsed time and escaped defects by task class. Safety/authority violations
or unreliable evidence stop the affected workflow immediately. Do not optimize
review cost by hiding failures. A narrow task's results may justify Luna locally;
the broad benchmark does not establish its success rate for mechanical work.

Rollback coordinates active sessions/worktrees, reverts the routing change, reloads
clients and confirms effective settings. Preserve all observations and historical
acceptance. Do not rewrite old records to claim that a newer model ran.

## Offline checks

```sh
python3 -m unittest discover -s tests -p 'test_codex_agent_policy.py' -v
python3 -m unittest discover -s tests -p 'test_feature_workflow.py'
python3 scripts/feature_workflow.py validate
python3 scripts/feature_workflow.py next
git diff --check
git diff --cached --check
```

The focused policy tests check configuration contracts, default-versus-pinned
settings, matched review variants, role-table consistency, boundaries and benchmark
transcription invariants. They do not launch Codex or validate model capability,
permission enforcement, hardware or independent acceptance. Full workflow checks
need a complete checkout; report the actual environment and any checks not run.
