# Codex model routing: evaluation and rollout

Evaluation date: 2026-09-30 (Australia/Sydney).
Baseline: `98808f125e1036e800794526d5f139ed1365d65f`.
Scope: project agent configuration, guidance and offline policy tests only.
This is a proposed rollout, not a record of completed model trials or independent
acceptance. No hardware, feature approvals, historical evidence, dispatcher logic,
user-global settings, billing account or unattended schedule is changed.

## Evaluation of the initial recommendation

Retain the existing Luna roles, independent review and measurement of accepted
outcomes. Test the proposed Sol upgrade without treating benchmark claims or
per-token prices as proof of project-specific quality or savings.

| Initial suggestion | Refined decision |
| --- | --- |
| Replace GPT-6 Sol with GPT-6.1 Sol | Propose `gpt-6.1-sol` for the five existing Sol profiles, retaining medium effort. Confirm the exact identifier and access in the target client before merge. |
| Make low effort the normal implementation/integration setting | Keep complex recovery, image and integration work at medium. Add an opt-in `project_routine_implementer` for settled, low-risk implementation. |
| Add a cheap test agent | Prefer an existing deterministic script with no child agent. Use optional `project_test_runner` only when a supplied recipe needs delegated observation; leave diagnosis with `project_integration`. |
| Escalate by requesting higher effort | A custom profile's model/effort overrides spawn-time values. Provide an explicit `high_consequence_reviewer_high`; verify effective settings for every escalation. |
| Treat API token ratios as savings | Distinguish API billing, purchased Codex credits and included subscription limits. Compare total cost through independent acceptance, not worker price alone. |
| Exploit cached project context | Keep necessary context compact and stable, but measure actual cached usage. Referencing a path does not itself prove a cache hit; never enlarge prompts just to seek a discount. |
| Remove redundant stages | Keep triage optional and reuse valid approval. Do not skip required independent verification, execution evidence or immediate high-consequence review. |

OpenAI's [Work and Codex help article](https://help-lb.openai.com/en/articles/20001275-chatgpt-work-and-codex)
confirms GPT-6.1 Sol is rolling out, with access depending on the account, plan and
workspace. The [model launch resources](https://academy.openai.com/en/pages/chatgpt-5-6-champion-launch-resources-tzoyyc)
recommend checking access and comparing familiar work. These support evaluating
this migration, not claiming every client/account can already run these profiles.
The configured identifier is a proposed setting pending the pre-merge runtime check.

The initial conversation's exact benchmark deltas, token prices, cached-input
reductions and price ratios were not substantiated by the official pages retrieved
for this review. They are not used as acceptance evidence or reproduced as verified
rates here. No measured SV08 outcome establishes that low effort can replace medium
for complex work. Availability and quality remain separate questions.

The [subagent documentation](https://learn.chatgpt.com/docs/agent-configuration/subagents)
describes standalone project TOML files, model/effort precedence and parent runtime
permission overrides. The profile files select behavior; they do not prove enforced
isolation. The high-effort variant deliberately shares the medium review's full
instructions, with an offline test guarding against policy divergence.

## Routing without a mandatory agent chain

The authoritative role table and handoff rules are in the
[agent guide](../../.codex/agent-guide.md). Choose one suitable execution route,
not every cheaper tier in sequence. Keep one implementation active and at most
two children; the existing [.codex/config.toml](../../.codex/config.toml) is unchanged.

| Task class | Execution and review |
| --- | --- |
| Tiny correction to documented behavior | Existing Luna narrow implementer or local edit; short record and normal coordinator review. |
| Settled, low-risk implementation | Opt-in Sol/low routine pilot, otherwise existing Sol/medium implementer; required separate verification remains. |
| Boot/recovery, A/B, writers, data migration, credentials, hardware constants, heater/motion or release-related work | Existing Sol/medium complex role directly; excluded from the low-effort pilot even for small/offline changes. |
| Fully prescribed offline test | Run the script directly, or use the optional Luna test runner with exact commands, fixtures, expected observations and stop conditions. |
| Unexpected QEMU/package/UI behavior or incomplete test recipe | Sol/medium integration role; do not ask the test runner to invent diagnosis or repairs. |
| New substantive proposal | Separate approver before implementation; reuse valid existing approvals without repeating product approval. |
| Substantive delivery | Separate verifier checks the complete stable diff and acceptance evidence; implementers and evidence producers cannot verify themselves. |
| High-consequence action | Immediate independent medium review, or the explicit high profile for material uncertainty; owner authorization and observed execution evidence remain separate. |

If material uncertainty is already known, choose the high review directly rather
than paying for medium first. If discovered in a medium review, transfer that
evidence to the high reviewer before action. Unresolved physical facts remain
blockers at any effort. This does not bypass the constraints in [AGENTS.md](../../AGENTS.md).

## Cost accounting, not savings promises

Use the applicable [Codex pricing](https://learn.chatgpt.com/docs/pricing),
[API pricing](https://developers.openai.com/api/docs/pricing) and account usage
surface at the time of a trial. Record the billing route, rate source/date and
speed/context tier. This document deliberately does not pin unverified model rates.
A dollar price, a purchased-credit rate and included subscription usage are not
interchangeable measurements. Do not infer weekly allowance from an API price ratio.

For a metered estimate, separate uncached input, cached input and output using the
actual billing definitions. If reported total input includes cached input, subtract
cached input before pricing the uncached part. Do not count reasoning twice if it
is included in total output. Distinguish estimated cost from observed billing and
record any other applicable charges. Missing usage or rates remain unknown, not zero.
Do not mix API and Codex credit rates or attribute a parent total to each child.
No API-key migration, credit purchase or Fast/Ultrafast setting is introduced.

Count coordinator work, all children, retries, escalation, rework, integration and
independent verification through acceptance. Track tool/build waiting separately
from model work; waiting on the same build is not a reason for another agent run.
A failed or abandoned trial still contributes cost and failure data. Never exclude
expensive escalations from the pilot cohort. A cheaper invocation that causes more
rework may have a higher total cost per accepted result.

## Pre-merge checks and reversible pilot

Keep this change in draft until an independent reviewer inspects it and a fresh
target Codex client loads the proposed branch in an authorized source-only fixture.
Confirm the exact model identifier, available effort levels and intended role names,
and record client version plus runtime-confirmed model, effort and permissions.
Check that the high variant actually runs at high effort. Neither parsed TOML nor
a model's assertion about itself proves these settings. Do not use hardware commands
or grant extra permissions to make this check pass. If unavailable, leave the PR
pending or revise the candidate setting explicitly; do not merge broken defaults.

After those checks and independent review:

1. Start a baseline cohort on the upgraded medium defaults; keep existing Luna
   work as-is. For later low-risk trials, the coordinator explicitly records why
   the routine implementer or test runner is eligible. Keep reviewers and
   acceptance checks fixed. Alternate comparable eligible tasks between default
   and pilot routes where practical; do not buy duplicate production work just
   to produce a benchmark.
2. Keep one [observation](../../.codex/templates/agent-task-observation.md) per task
   under ignored `local/feature-workflow/model-routing/`. Include all linked
   attempts through acceptance, runtime evidence and unknowns. Publish only
   sanitized aggregate findings. Do not extend or rewrite the existing hashed
   approval and verification JSON contracts with telemetry fields.
3. Inspect the first 10 eligible tasks as an early checkpoint, not statistical
   proof. Compare task classes, first-pass acceptance, rework/escalation, escaped
   defects, elapsed time and total observed cost per accepted result. Report
   sample size, missing measurements and failures. Promote a pilot only after
   independent review finds no material quality regression and credible net
   benefit across comparable work; retain medium where evidence is weak.

A repeated failure after the one bounded routine repair, architectural ambiguity,
resource conflict or scope growth ends the cheap attempt. Hand off exact evidence
instead of starting a broad retry loop. Any unsafe action, weakened acceptance,
fabricated observation or missed critical condition suspends the affected pilot
immediately. A higher model cannot authorize bypassing an existing gate.

For a model/access failure, stop that assignment and record an explicit supported
fallback at the same review/effort tier, such as the previous Sol medium/high
configuration. A fallback is not a 6.1 trial. If no suitable independent reviewer
is available, leave the review/action pending. Do not change a pinned role's
model/effort by a spawn argument that the file will override.

Rollback first stops new pilot assignments and routes eligible work back to the
unchanged medium or existing Luna defaults. Preserve observations and any active
worktree ownership. To undo the upgrade itself, revert the configuration PR after
coordinating active sessions; do not rewrite historical evidence or acceptance.

## Validation boundaries

Run the focused, standard-library-only policy checks from the repository root:

```sh
python3 -m unittest discover -s tests -p 'test_codex_agent_policy.py' -v
git diff --check
git diff --cached --check
```

These check TOML structure, explicit routing, read-only review defaults, shared
high-review instructions, guide/table consistency and local links in this new
rollout document. They do not launch Codex, establish isolation, measure savings,
prove review quality or run firmware, QEMU or hardware acceptance tests. Run the
normal feature-workflow checks in a full checkout before rollout as required by
the [workflow entry point](../../.codex/README.md).
