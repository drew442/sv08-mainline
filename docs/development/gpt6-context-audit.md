# GPT-6 context and completion audit

Date: 2026-10-05. Baseline: `91a76352d560ec927729ecfc17a960f5725e7860`.
Scope: repository instructions and retrieval paths, not a new agent runtime.
The owner supplied eight OpenAI MHTML captures and requested a new PR. This audit
uses the current main branch, not the earlier routing-PR draft. Model defaults,
full-access execution, incidental allowances and acceptance boundaries are preserved.

## Finding: reduce mandatory reads, not the evidence library

GitHub code search reported 605 indexed files under `docs/`, one root AGENTS.md
and no SKILL.md at the baseline (complete search results). These are indexed counts,
not proof of the full tracked inventory or what a running model actually consumed.
The [official discovery rules](https://learn.chatgpt.com/docs/agent-configuration/agents-md)
load applicable AGENTS files along the root-to-working-directory chain; merely
having a large docs directory does not load every document. Global/client-added
context and actual child inheritance were not observable in this review.

There is nevertheless concrete instruction-level overhead:

- Root AGENTS required README.md, project.md, roadmap.md and the applicable hardware
  profile before changing behavior. The first three total 29,887 UTF-8 bytes
  (8,268 + 4,484 + 17,135), before any profile. Relevant requirements must still be
  inspected, but every scoped fix does not need this broad orientation/history stack.
- Every named role required the 16,602-byte agent guide. Planner and formal delivery
  review also required the 4,683-byte workflow entry, whose links encouraged reading
  the full design, validation and completed pilot for current contracts.
- The workflow entry's session-start queue commands did not clearly distinguish
  the coordinator from a child already holding a specific assignment.
- Current README/roadmap mix current status and older phase evidence. Current goals
  already have separate history files; deleting or rewriting those would damage
  provenance rather than improve retrieval.

The fix is a small task entry and conditional source navigation. Workers apply root
rules, their role and relevant task evidence; the coordinator guide is loaded for
routing/exceptions. Existing matching instructions need not be fetched again.
The new [context map](../context-map.md) is optional when paths are unclear, not
another required guide. The full docs, old decisions, accepted benchmark data and
historical evidence are retained. No retrieval service or skill-description catalog
is added to the prompt. Add a skill later only for a demonstrated reusable capability,
with a narrow trigger and supporting material loaded on demand.

## Static before/after comparison

Count UTF-8 source bytes in the named root/role/guide files once each. Include
whole TOML files consistently (not just developer instructions). This measures the
explicit entry-text obligation, not tokens, API requests, inherited conversation,
cache hits, actual agent reads, wall-clock time or billing. Task-specific sources,
acceptance evidence and optional troubleshooting reads are excluded from both sides.
For planner/verifier the old entry includes .codex/README.md; all old child entries
include AGENTS.md and agent-guide.md. New child entries include AGENTS.md and the
selected profile. Coordinator entries include the three root/guide/workflow texts.

| Entry | Before bytes | After bytes | Reduction |
| --- | ---: | ---: | ---: |
| Implementer | 27,368 | 10,354 | 62.2% |
| Lookup | 26,238 | 9,051 | 65.5% |
| Delivery verifier | 32,162 | 10,238 | 68.2% |
| Planner | 31,886 | 9,998 | 68.6% |
| Coordinator entry | 29,246 | 21,860 | 25.3% |

Individual files now measure: AGENTS.md 7,354; agent-guide.md 12,591;
.codex/README.md 1,915 bytes. Some role prompts grow slightly to make completion
and conditional retrieval explicit; the main saving comes from no longer requiring
the large coordinator guide in every worker. There is no claim of a proportionate
credit, token or latency reduction. A client that inherits an already-large parent
context may realize less benefit; confirm its actual traces before quantifying savings.

## Applying the new OpenAI guidance

The supplied model/skills guides favor clear outcomes, relevant context, progressive
loading and explicit safe-work boundaries. They also favor completing the change,
running it, inspecting results and correcting failures, rather than stopping at the
first patch. Conversely, repeated/broader tests after adequate checks need a reason.
The repository now states both sides without weakening required acceptance checks.

The accepted [benchmark routing](codex-model-routing.md) remains appropriate for
bounded Sol-low engineering, medium planning/complex work, and medium/high independent
review. The new model-selection guide is a starting point, not a command to reset
all efforts to its examples. Its general Sol-medium recommendation covers complex
technical work; choose that directly when the handoff has that difficulty. Do not
infer unseen interactive selections from the saved page or transfer Astra-specific
behavior to Sol/Luna without observing it. No new model, billing route, speed mode,
review stage, worker count or model-effort classifier is introduced.

The existing two-experiment/300-second/256-MiB allowance is for incidental questions,
not the primary implementation or full acceptance suite. The same-failure repair
limit does not forbid fixing distinct defects within an assigned primary budget.
Coordinators can grant bounded continuations under standing consent; workers cannot
self-escalate or reset accounting. Role independence and real hardware authorization
remain separate from model capability. Approval/verification JSON is unchanged.

| Guidance reviewed | Repository application / boundary |
| --- | --- |
| Stable relevant prefixes and bounded outputs | Reuse unchanged policy/evidence; return short findings and artifact references, not complete transcripts. Do not inflate input to improve cache-hit percentage. |
| Prompt-cache diagnostics | Actual cached/cache-write token fields are measurements when exposed. A diagnostic comparison ID neither loads previous context nor improves caching. No diagnostic request fields are added to Codex config. |
| Compaction | Keep goal, scope, revision, ownership, decisions, evidence, failed approaches, budgets and active handles in durable local handoffs. Use supported client features; no custom compaction engine or context truncation. |
| Async tools | Do independent authorized work while existing jobs run; await results before dependent actions. The API's async flag requires application execution/registry support and is not enabled by this PR. |
| Mid-turn steering | Changed intent does not undo prior effects or cancel running tools. Reconcile actual state and pending results instead of replaying work; no WebSocket client is introduced. |
| Delegation | Keep bounded independent tasks off the main thread, with concise evidence-backed returns. Keep two-child/single-implementation limits and fresh independent review. More roles are not a mandatory team. |

The linked API transport, SDK event and application job-registry specifications are
outside this source-instruction change: no such implementation or compatibility
claim is made. The three latest captures close the previously reported gaps relevant
to this audit. Live pages with older GPT-5.6 examples are not substituted for the
provided GPT-6 captures. General AGENTS/subagent configuration and caching/compaction/
cost/latency guidance were reviewed separately; model-specific conclusions use the
supplied versions. No inaccessible linked page is assumed to say something it does not.

## Source record

The eight owner-supplied files below were MIME-decoded locally; article/main content
and links were inspected. Links identify original sources, not a claim that each live
page was reachable. SHA-256 identifies the supplied bytes, not publicly retrievable
repository attachments. The MHTMLs are not committed because they may contain browser
state and unrelated assets. Keep the originals with review evidence. API samples in
these sources are explanatory, not code introduced into the project.

| Supplied capture / original source | SHA-256 |
| --- | --- |
| [A model guide for the GPT-6 family _ OpenAI.mhtml](https://openai.com/index/practical-guide-building-gpt-6/) | `bc9f599609e2d94bb05cefc2bfc5231ebefda97c036a54989ed84f7efd13331c` |
| [Async tool calling _ OpenAI API.mhtml](https://developers.openai.com/api/docs/guides/async-tool-calling) | `5bd223244075c91b0d17b4a7b662b89f907e380a786a6f7078ff2599eb69d163` |
| [GPT-6.1 Sol Model _ OpenAI API.mhtml](https://developers.openai.com/api/docs/models/gpt-6.1-sol) | `77dff9ac6045598a62cea4e8bd519f28ac26ae5635b774d5c354dfcc85d89378` |
| [Mid-turn steering _ OpenAI API.mhtml](https://developers.openai.com/api/docs/guides/steering) | `a6bb73dd4db2cfcc57e56557db8fa61852822de99093542644e4ee7c73011899` |
| [Model selection _ OpenAI API.mhtml](https://developers.openai.com/api/docs/guides/model-selection) | `23671fff93c6586c7073a535b91e460268b03c997c5d34a462f12a74d6cdbb5c` |
| [Prompt cache diagnostics _ OpenAI API.mhtml](https://developers.openai.com/api/docs/guides/prompt-caching/diagnostics) | `47a4d8ee229d2de0c4dab1d708d84c3ca174d4756f01b355791e56da73230be4` |
| [Rethinking skills and prompts for GPT-6 Astra _ OpenAI Developers.mhtml](https://developers.openai.com/blog/rethinking-skills-and-prompts-for-gpt-6-astra) | `82f33644a82899bfd3b5ecaf24766cee955149d08d639f1ee2cb78691255fdc8` |
| [Using GPT-6 _ OpenAI API.mhtml](https://developers.openai.com/api/docs/guides/latest-model) | `1e86754aa8bad71be7633bdca8bf9a2c10f037e0cd4165b50bb96110d045c571` |

Additional relevant official references reviewed:
[AGENTS discovery](https://learn.chatgpt.com/docs/agent-configuration/agents-md),
[subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents),
[config](https://learn.chatgpt.com/docs/config-file/config-reference),
[prompt caching](https://developers.openai.com/api/docs/guides/prompt-caching),
[compaction](https://developers.openai.com/api/docs/guides/compaction),
[reasoning](https://developers.openai.com/api/docs/guides/reasoning),
[reasoning best practices](https://developers.openai.com/api/docs/guides/reasoning-best-practices),
[cost](https://developers.openai.com/api/docs/guides/cost-optimization),
[latency](https://developers.openai.com/api/docs/guides/latency-optimization).

## Validation and deployment checks

The existing agent-policy tests remain unchanged. The new context tests guard entry
size, conditional onboarding, coordinator-only queue selection, relevant retrieval,
completion, pending-job handling and full-diff review. They check written contracts,
not whether a model obeys them. Entry-size limits do not limit necessary evidence.

```sh
python3 -m unittest discover -s tests -p 'test_codex_agent_policy.py' -v
python3 -m unittest discover -s tests -p 'test_agent_context.py' -v
# In a complete checkout, also run the existing workflow checks:
python3 -m unittest discover -s tests -p 'test_feature_workflow*.py' -v
python3 scripts/feature_workflow.py validate
python3 scripts/feature_workflow.py next
git diff --check
git diff --cached --check
```

This author could not clone through the execution environment's DNS; the GitHub
connector provided pinned source reads/publication. Focused tests run on a
reconstructed relevant-source fixture, with original source blobs verified by hash.
Full repository history/queue validation, independent review, live Codex traces,
QEMU and hardware acceptance were not run. Do not count those checks as passed.

Before merge, independently review the whole PR and run the full-checkout checks.
Changing AGENTS or requirement documents can stale pending approval hashes; obtain
genuine review for affected inputs, never mechanically refresh hashes or rewrite
completed history. Restart clients that cache instructions. Verify source-only
examples: (1) lookup does not load whole roadmap/guide, (2) a scoped implementation
loads relevant requirements, tests and completes its in-scope repair, (3) a verifier
still checks the complete stable diff, (4) a pending job is observed, not relaunched.
No printer operation or external spending is authorized by those examples.

For representative tasks retain actual read paths/bytes, runtime context/usage if
available, cache reads/writes, selected role/effort, retries, elapsed model versus
build time and independent acceptance. Compare task classes, include failures and
missing measurements, and keep raw traces private. Do not buy duplicate production
runs merely to claim savings. Roll back this PR's instructions after reconciling
active jobs/worktrees if required context is missed; retain all evidence and the
unchanged model/execution settings.
