# Goal assessment and reset — 2026-10-01

Owner request: assess all goals, recalibrate the plan and reset the goals.
Assessment baseline: `bca3cfe`, after the successful H12 warm-capture experiment.
This is a planning/status reset, not hardware execution, a product-scope change
or a claim that the project is complete. The live list is
[Current delivery goals](../../.codex/current-goals.md); the
[remaining-work plan](../remaining-work-plan.md) supplies execution detail.

## Evidence-based assessment

| Workstream | Accepted evidence | Remaining result | Assessment |
| --- | --- | --- | --- |
| H12 control and capture | Address-based SSH trust decision; earlier SD Linux/SSH/GUI; current warm reset captured SPL, DRAM, U-Boot and original recovery | Intercept U-Boot, return to SD and refresh current target/environment/RTC/p5 facts | Ready for a bounded next operation, not blocked on new hardware or capture research |
| H12 physical preflight | Preflight-only executable, dynamic MMC binding and selector correction independently accepted offline | Corrected selector physically staged; fresh actual preflight/claim/return | First attempt failed before FIT entry; urh-04 remains open |
| Writerless reimage | Signed purpose/claim, target binding, trusted writer and recovery handoff; full-size QEMU write/readback and return evidence | Physical urh-05 write/readback and required return on identified spare | Queued after urh-04; not a completed physical capability |
| Normal host and boot health | Diagnostic normal boots/SSH/persistence; accepted boot-health composition and immutable Cockpit TLS fix offline | Compose/install selected corrections; normal health confirmation, stable access and repeatable boot/DRAM behavior | Host is presently evidenced in original recovery, not a ready printing OS |
| Printer configuration and firmware | Matching MCU builds, Katapult USB updates, paired no-output communication; inactive interface configuration independently verified | Essential sensor/heater/geometry facts, final machine substitutions, service activation and attended commissioning | No motion/heater/printing completion; modified test printer cannot certify stock |
| Administration and signed updates | Cockpit/authenticated upload/durable jobs, ambiguous-job resolution and signed A/B VM journeys accepted | Production onboarding/access/network/software workflows, history rollover, integrated physical A/B and failure behavior | Substantial offline foundation; complete host product still open |
| Independent recovery | 512 MiB image, installed boot-to-export composition and preservation/refusal evidence offline; physical recovery startup | Actual export/UI/media tests, signed restore, explicit initialization/preserved-slot operations and user-data restoration | Export implementation is done; physical usability and restore remain open |
| Peripherals and reliability | Wired network; earlier Wi-Fi association; HDMI/USB/touch enumeration and short camera/memory tests | Selected-image Wi-Fi/reconnect, touch interaction, sustained camera, cold boot/DRAM, thermal/watchdog and workloads | Partial physical evidence, not comprehensive reliability |
| Release | Factory-capacity diagnostic layout, pinned inputs and many reproducible builds; preserved factory/MCU recovery material | Complete final image/source/license closure, stock hardware qualification, install/recovery/print/update regression and license decision | No supported release or validated hardware combination |
| Development resources | Beelink root LV/FS expanded and checked; separate CLI review fallback demonstrated | Per-operation storage/resource admission; coordinator root remains constrained | Old Beelink space and native-agent-limit blockers no longer justify stopping all work |

Primary evidence: [warm capture](../hardware/host-h12-boot-capture-rethink-20261001.md),
[failed preflight](../hardware/host-h12-urh04-first-boot-20261001.md),
[accepted selector correction](../features/h616-selector-environment-source/record.json),
[SD host test](../hardware/host-sd-recovery-host-first-boot-20260929.md),
[writer handoff](../features/network-emmc-unattended-recovery-handoff/record.json),
[boot health](../features/host-boot-health-composition/record.json),
[printer interface](../features/printer-interface-config/record.json),
[recovery composition](../features/host-recovery-export-composition/record.json),
[A/B journey](../features/host-unattended-ab-updates/record.json),
[printer intake](parallel-printer-work.md) and
[host acceptance checklist](../hardware/host-os-tasks.md).
No live printer state was queried or changed during this assessment. “Current”
hardware state means the latest recorded result, subject to fresh action checks.

## Why the plan changes

The previous live list accumulated chronological checkpoints and obsolete active
assignments. Completed export, printer-interface and boot-health implementations
still appeared in the September execution order. Historical v5 counters and
older SSH conditions coexisted with later physical operations. The old global
`blocked` flag arose from agent launch limits even though separate supported
sessions subsequently supplied independent research/review and hardware progress.

Boot capture and H12 acceptance are distinct. We now have a measured way to reset
the host while the serial bridge stays connected. The simplest immediate route
is to use it with a ready serial controller and the existing SD recovery script.
The unapproved return-guard implementation and external receiver are contingencies,
not prerequisites. Cold-start-only faults may still justify independent capture.

The reset preserves the original end goals but makes the next checkpoint small:
G1 SD control and urh-04; G2 physical writerless delivery/reliable host; G3 attended
first print; G4 complete host product; G5 stock qualification/release. First print
requires its real boot, firmware, sensor and output gates, not completion of every
administration convenience or stock-release test.

Prefer a bounded trial when its target, likely effects and recovery are known.
An unchanged failed experiment is not progress: record the first failure, make
one diagnosis-driven correction, then reconsider the recovery method if it still
fails. This changes execution priority, not heater protections, review independence
or the meaning of accepted evidence. No redundant backup gate is introduced.

## Task and branch census

`feature_workflow.py validate` reports 34 features / 41 tasks: **36 done,
4 pending and 1 blocked**. These are heterogeneous feature tasks, mostly offline;
36/41 is not a project-completion percentage. The five unfinished tasks are:

| Record/task | Recorded state | Reset disposition |
| --- | --- | --- |
| `h12-expired-preflight-return-guard / implement-return-guard` | Pending, decision null | Contingency outside active plan; neither approved nor falsely marked done |
| `network-emmc-unattended-recovery-handoff / physical-read-only` | Pending | G1 urh-04 |
| `network-emmc-unattended-recovery-handoff / physical-reimage` | Pending | G2 urh-05 |
| `host-unattended-ab-updates / physical-validation` | Pending | G4 physical A/B acceptance |
| `recovery-media-export / physical` | Blocked on physical evidence | G4/H04/H07 physical export/UI/media acceptance |

`feature_workflow.py next` returns null: no approved offline implementation is
ready. It does not dispatch coordinator hardware operations and does not mean the
project has no next action. Remaining requirements not yet represented by these
feature records remain in the host checklist and plan; they are not erased by
this census. No proposal approval or verification record is rewritten by the reset.

There are 49 local branches including main. Of the 48 others, 38 tips are ancestors
of main; 10 are not. Non-ancestor tips include older attempts and alternative
revisions, so neither automatic merging nor deletion is warranted. Worktrees and
failed candidates remain preserved; none is assigned implementation merely by
existing. Main was 38 commits ahead of the locally recorded upstream before this
reset. No fetch was performed, so this is not a current remote-server comparison.
The reset publishes nothing and creates no new implementation branch.

## Human dependencies and authority

G1 uses the current reported PSU-off/USB-power/Ethernet/spare-installed/factory-stored
setup. No new physical action is requested merely to reset the plan. Authenticate
and check current state at each operation; the owner's same-scope authority stands.
Urh-05 whole-image authority is evaluated explicitly when ready and is not inferred
from urh-04. Exact high-consequence reviews remain required immediately before
applicable actions. Failed reviews and actual unsuccessful attempts remain evidence.

Later physical dependencies stay in the [single H queue](../hardware/coordinated-human-tasks.md):
essential sensor/heater facts and independent temperature reference (H01/H05),
attended outputs/printing (H06), peripherals (H04), failure/recovery tests (H07),
license/stock qualification (H08). Existing observations satisfy only their actual
scope. Modified-machine printing may proceed without stock-machine availability.

Temporary Astra/high use remains limited to concluding H12 as the owner requested.
Normal Sol role defaults continue elsewhere and after H12; no model configuration
was changed by the capture experiment or this reset. One implementation and bounded
independent review remain the normal resource policy; scheduling stays disabled.

## Goal-tracker history and resolution

At the initial reset, the old application goal described the full project and had status `blocked`.
The coordinator attempted to replace it with G1–G5 through `create_goal`; the tool
returned: `cannot create a new goal because this thread has an unfinished goal; complete the existing goal first`.
Available controls expose create/get and complete/blocked/paused status updates,
but no objective edit, cancel, reset or resume. The project is unfinished, so
marking it complete to unlock replacement would be false. Repository goals and
plans have been reset; application-goal replacement requires a user-side control
if available. Manual authorized work can continue independently of that flag.

At 12:07 UTC on 2026-10-01, `get_goal` returned null. At 12:11 UTC the
coordinator created a fresh active G1–G5 goal using the existing owner request.
The earlier limitation is resolved; project completion has not been claimed.
