# Working in SV08 Mainline

## Context

Read `README.md`, `docs/project.md`, `docs/roadmap.md`, and the applicable hardware
profile before changing behavior. The project supports stock and modified SV08
electronics, starting with stock. No hardware combination is validated yet.

## Evidence and hardware profiles

- Treat `docs/hardware/stock-sv08.md` as a source-backed inventory, not proof of
  the connected printer's identity. Record board revision and evidence with
  every hardware claim. Keep documented, inferred, and measured facts distinct.
- Unknown MCU clocks, bootloader offsets, GPIO polarities, thermistor circuits,
  and device identities must stay unknown until verified. Do not fill them from
  a similar printer. SV08 Max and Zero are separate hardware targets.
- Represent electronics changes in explicit profiles. Keep machine serials,
  calibration, network credentials, and private backups in ignored local paths.
- Cite primary documents with path/page or URL, revision where available, and
  access date. If sources disagree, document the discrepancy and required check.

## Implementation

- Prefer upstream configuration and supported extension mechanisms. Add custom
  code only for an identified gap, with a test, provenance, and an upstreaming or
  retirement plan. Record architectural choices in `docs/decisions/`.
- Treat `upstream/` as pinned third-party source. Do not silently modify it or
  run bundled installers. Use a documented patch or an explicit fork when needed.
- A submodule update must include its gitlink and `upstream-lock.json` changes,
  the reason, and validation status. Do not use floating updates in build/install
  paths. Never describe a downloaded revision as tested compatibility.
- Build host and MCU Klipper artifacts from the same selected revision unless
  a separately tested compatibility policy is documented. Record toolchain,
  configuration, patches, and output hashes for reproducible artifacts.
- Keep bootstrap, build, backup, flash, and activation as separate operations.
  Default tooling to inspection/dry-run where a command can alter hardware.
  Hardware writes require an identified target, reviewed artifacts, and a
  recovery path; follow the user's authorization for the action.
- Preserve heater protections and validate sensor behavior before heat or motion.
  Do not turn off protections to make a migration appear successful.

## Validation and reporting

Run checks proportionate to the change. Documentation changes need link/path and
consistency checks. Code and firmware changes need relevant tests/builds; state
clearly which checks were offline and which used a named hardware profile.

For foundation changes, inspect `git diff --check`, `git diff --cached --check`,
`git submodule status`, and agreement between the lock file and indexed gitlinks.
Check JSON syntax and local Markdown targets when changing those files.

Update affected documentation with behavior changes. Report the result, evidence,
and remaining limitations. Do not commit secrets, device dumps, generated images,
or unrelated upstream changes. Do not publish or push unless requested.

## Feature delivery and delegated review

The owner approved the [feature workflow](.codex/README.md), delegated approval
and an offline pilot on 2026-09-11; see [decision 0011](docs/decisions/0011-feature-agent-workflow.md).
For substantive new features or improvements, use that workflow and its durable
records. Previously approved work needs no repeated product approval.

Spawn a separate feature-approver agent for bounded proposal review and a separate
feature-verifier agent for delivery review. Invoke a feature-suggester agent when
triage would help select the next useful task. Give reviewers relevant source and
evidence, not the author's conversation as justification. Parallel agent work is
appropriate for independent review or research alongside useful implementation;
keep one implementation active unless separate ownership is explicitly justified.

Agents may approve bounded work within accepted project requirements. Changes to
owner requirements, material scope expansion or expanded agent authority require
the owner's decision. Preserve existing authorization for routine implementation,
validation, commits and pushes. Feature approval grants no hardware authority.

After finishing or blocking a task, continue the next authorized ready task.
Record physical dependencies in the existing human task lists and investigate
small non-destructive alternatives where useful. Keep offline, hardware and release
evidence distinct. Scheduling remains disabled unless explicitly configured.
