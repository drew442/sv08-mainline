# Agent routing observation

Copy to ignored `local/feature-workflow/model-routing/<task-id>.md`.
This is measurement metadata, not an approval, verification or hardware record.
Use `unknown` for unavailable observations, never zero or an invented estimate.
Retain private runtime excerpts locally; publish only sanitized aggregates.

## Task and baseline

- Task/feature and acceptance check IDs:
- Source/base revision and relevant input hashes:
- Task class and scope; default or pilot route; eligibility rationale:
- Existing approval/reference and comparison cohort:
- Execution allowance, escalation trigger and stop conditions:

## Attempts (repeat this section for every linked attempt)

- Attempt ID; parent/task ID; role; client/version:
- Requested model/effort; runtime-confirmed model/effort (or unknown):
- Evidence for effective settings; effective permissions and assigned resources:
- Billing mode: included subscription / Codex credits / API key / unknown:
- Speed/context tier; usage source and interval; observed versus estimated:
- Input total; cached input; output total; whether reasoning is included:
- Observed credits or API cost and currency (or unknown); rate date/source:
- Start/end; elapsed time; model work versus external build/wait time:
- Actual commands, status, evidence paths/hashes and limitations:
- Outcome; retry/escalation reason; next role; related attempt IDs:

## Outcome through independent acceptance

- Separate verifier/session and authoritative verification/evidence reference:
- First-pass acceptance; rework cycles; escalations; escaped defects:
- Final accepted / failed / blocked / abandoned status and source revision:
- Total observed cost including coordinator, all children, retries and reviews:
- Cost coverage gaps; avoid double-counting parent totals that include children:
- Acceptance regressions or safety concerns; suspend-pilot decision if needed:
- Comparison with similar default-route tasks; sample size and limitations:

Do not add these fields to hashed decision/verification records. See
`docs/development/codex-model-routing.md` in the repository for interpretation.
