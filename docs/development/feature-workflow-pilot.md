# Feature workflow offline pilot

Date: 2026-09-12. The owner approved the framework, delegated approval and this
bounded offline pilot. Both offline deliveries are complete after independent
review. Physical acceptance remains open; scheduling remains disabled. No printer,
Beelink, private backup or physical device access was needed for the pilot.

## Delivered workflow

The [operating guide](feature-workflow.md) and
[project entry point](../../.codex/README.md) provide native role definitions,
proposal/fix templates, structured decision/evidence contracts and a deterministic
queue. The coordinator imports separate reviews, claims one isolated implementation,
submits a clean committed result, integrates the reviewed commit and then completes
its task. Proposal approval does not grant hardware authority.

The separate suggester selected one unfinished recovery capability and one
measurable improvement from the accepted backlog. The approver reviewed both
against decision 0010, required concrete preservation/identity checks and kept
physical acceptance separate. The readback task depended on completed media
implementation; its dispatch proceeded while the physical task stayed blocked.
No additional owner decision was required within the approved pilot.

| Delivery | Reviewed source commit | Outcome |
| --- | --- | --- |
| Verified pre-mounted recovery export | `03cb99996e7ad92eed97c312932463821818ec8e` | Staged GTK entry uses explicit, verified recovery/source/destination admission. Offline implementation passed; physical acceptance remains open. |
| Single-pass export readback | `2a50af2289650b04263d47b6859665d0416c56e0` | One complete readback retains member and whole-byte integrity while removing the separate digest scan. |

[Media evidence](../hardware/host-recovery-media.md) and
[readback evidence](../hardware/host-recovery-readback.md) describe methods and
limits. The durable [media record](../features/recovery-media-export/record.json)
and [improvement record](../features/recovery-export-readback/record.json) bind each
accepted decision, complete source commit, public evidence hashes and independent
verification. The original evidence commits remain in normal main-branch history.

## Measured outcomes

The approved archive is 9,123,840 bytes with SHA-256
`0767efa76615052ca0c1506ec6c76bbdeee2ce989c44dfa5aff434872102aa72`.
Verification reads fell from 18,242,915 to 9,123,840 logical bytes, approximately
50%, with zero seeks and an explicit EOF read. This counts all underlying returned
bytes, including headers, stream read-ahead and padding. It does not establish
physical-media speed or power-loss durability.

The final 53 targeted workstation tests and 34 selected ARM64 Python runtime tests
passed. Actual native GTK chooser/review/apply and provider ext4/FAT32 fixtures
passed with cancellation, whole-source/recovery preservation, shared exclusion,
media removal and device reuse. The staged production entry also has checked
diagnostic behavior for absent, malformed and untrusted preparation inputs.
These are offline fixtures, not validation of any SV08 hardware combination.

The workflow's 27 regression tests and five independent live proposal cases
passed; see [framework validation](feature-workflow-validation.md). A fresh normal
Git clone also validated both completed records, all historical
evidence hashes and reachable source commits without private leases or worktrees,
and reproduced the exact before/after measurement.
Seven upstream gitlinks still agree with their lock file. No submodule revision
or printer configuration changed for this pilot. The framework adds workstation
Python/jsonschema coordination only, with no agent runtime in the printer image.

## Review findings and iteration

Separate framework review found approval and evidence-binding defects before the
pilot, including incomplete change-set coverage and acceptance changes reusing old
verification. The five-case live evaluation rejected duplicate scope, unsupported
hardware assumptions and owner conflicts while allowing useful offline work.
This is a small regression evaluation, not a statistical model-quality benchmark.

The first submitted media candidate (`e54d46c`) failed independent review: identity
normalization could discard an alias when duplicate attribute names appeared.
The coordinator imported the failed verdict and blocked the task, preserving it
in commit `272290c`. A fresh worktree based on that integration state retained the
candidate in history, corrected comparison to preserve every key/value alias and
added both attribute-order and inventory-order regressions. The separate verifier
then passed `03cb999`; the coordinator integrated it before completing the task.
This exercised actual rejection, changed-method resumption and independent retry.

Independent readback research identified permissive late-header handling and
metadata allocation risks in tarfile. A supported public parser hook bounds
metadata input, while matching the write-time digest detects byte changes beyond
member payloads. Review then reproduced synthetic sparse expansion from a tiny
archive; the final implementation rejects sparse metadata before extraction and
retains the real regression. These review findings changed delivered behavior.

Keep one implementation active, short task packets and the existing canonical
checklists. Treat declared role permissions as instructions until the actual
runner enforces them. A native CLI sandbox trial failed and an empty result was
rejected; the separate-session collaboration fallback completed proposal and
delivery review with inherited parent permissions. Restricted unattended runner
deployment and scheduling were outside the approved offline pilot and remain
unconfigured. The dispatcher itself launches no process.

## Remaining project work

The pilot's two offline tasks are complete; its physical recovery task remains
blocked at the [canonical human checklist](../hardware/host-os-tasks.md#human-and-powered-printer-tasks).
A reviewed independent recovery image and trusted media preparer, full package and
512 MiB/8 GB capacity closure, real touch/keyboard/mouse input and attended
power-interruption/media tests are still required. Other accepted host OS work
remains on that checklist; finishing this pilot does not mark the host OS complete
or produce a deployable recovery image.

Final queue inspection selects no further task in this bounded pilot: both offline
tasks are done and physical acceptance is explicitly blocked. Future development
sessions should import the next bounded item from the accepted host checklist and
continue through this workflow; a null selection is not completion of the project.
