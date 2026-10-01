# Current delivery goals

Reset: 2026-10-01 at the owner's request. This replaces the previous live
assignment list; its full contents remain in [the historical record](goals-history-through-20261001.md).
The [recalibrated execution plan](../docs/remaining-work-plan.md) gives order and
[the assessment](../docs/development/goals-reset-20261001.md) records evidence,
remaining dependencies and the goal-tracker limitation. Existing acceptance
requirements, decisions and failed attempts remain intact.

## Goal order and completion gates

| Goal | Current state | Next action | Done when |
| --- | --- | --- | --- |
| G1 — Restore SD control and pass H12 preflight | Active priority; capture, authenticated SD return and read-only reconciliation passed; urh-04 still failed/unpassed | Review and stage the freshly built preflight/selector repair, then arm and test through separate reviewed operations | Reconcile named spare/controller/CID, both environment records, RTC and read-only p5; stage the accepted selector repair with fresh signed inputs; actual preflight and required automatic return pass |
| G2 — Complete writerless reimage and reliable commissioning host | Queued behind G1; offline writer/handoff accepted, physical urh-05 open | After urh-04, establish exact urh-05 authority, reviewed source image and recovery path; perform write/readback/return as separate admitted operations | Physical full-image verification and automatic return pass; selected commissioning host has captured normal boots, persistent access/state, working administration and sufficient boot/DRAM reliability for commissioning |
| G3 — First working printer on test-sv08-01 | Offline interface and paired MCU work accepted; physical commissioning open | Complete remaining candidate substitutions and essential sensor/heater facts; activate only on the ready matching host/MCUs | Attended inputs, fans, motor direction, homing, controlled heat, calibration and first print pass, including pause/resume/cancel/shutdown |
| G4 — Complete factory-capacity host OS and recovery | Many components/VM journeys accepted; assembled product incomplete | Integrate accepted components and address remaining required administration, update, restore and peripheral gaps in bounded slices | Complete factory-capacity artifact, signed physical A/B health/fallback, persistent identities/state, required interfaces/peripherals and independent export/restore/recovery meet the host checklist |
| G5 — Supported stock release | Future qualification; no profile release-qualified | Prepare source/license and reproducibility closure while actual stock access and owner license decision wait | Actual stock commissioning, representative prints, clean install, recovery/failure/update regressions, documentation and release decision pass |

G3 may begin when its actual host and sensor prerequisites pass; it need not wait
for every G4 administration or G5 release feature. G4/G5 authorized preparation
may proceed while physical work waits. This ordering does not waive the accepted
writerless milestone or make a physical full-image write implicitly authorized.

## Immediate G1 execution

Checkpoint 2026-10-01: one reviewed keyboard reboot intercepted U-Boot and
loaded the hash-verified SD script. Authenticated SD SSH and independent passive
serial collector restoration passed. Fresh read-only intake identifies the same
spare on `4022000.mmc`, now `/dev/mmcblk0`; both environment CRCs pass, with
flags 5/4, zero A/B counters and the expired job token still present. See the
[measured return](../docs/hardware/host-h12-boot-capture-rethink-20261001.md#sd-return-physically-demonstrated).
Read-only p5 reconciliation subsequently passed: the old wrapper, original
script, FIT and retained marker match recorded hashes; private mount cleanup
and unchanged global mounts passed. Fresh signed preflight preparation and
artifact verification passed on Beelink with the accepted selector repair.
Exact staging, arm, activation, boot and physical return remain open.

1. Reuse [the measured warm-capture path](../docs/hardware/host-h12-boot-capture-rethink-20261001.md).
   USB stays connected; prepare the sole serial controller before one keyboard
   reboot. Confirm source, current capture readiness and exact operation review.
2. Intercept the observed three-second U-Boot window and validate the stopped
   prompt before the existing verified SD boot sequence. Capture-only success
   did not demonstrate interception or SD return. Do not stream commands after
   missing the window.
3. Once SD SSH is authenticated, record current media identity, environments,
   Linux/RTC and p5/staged marker state. Preserve beforeimages outside target tmpfs.
4. Use the independently accepted selector correction and freshly prepared
   preflight inputs. Reuse unchanged artifact/test evidence; independently review
   exact staging, arm and boot operations. Expired inputs are never rearmed.
5. Record real urh-04 admission and return evidence. Only then admit G2's distinct
   physical write; do not equate ordinary recovery boot with preflight success.

Use one bounded initial attempt and, only with a concrete diagnosis and exact
review, a corrected follow-up for the same interception failure. If still unable
to regain control, compare a physical keyboard, identified external RX tap or
existing USB-reader/SD rescue against more automation. Select the smallest useful
recovery step under applicable authority. Do not create another general guard
framework merely because the historical guard rejects today's state.

## Removed from the active path

- Early warm-boot capture: physically passed; no new capture framework needed.
- SSH-key enrollment: owner address-based trust resolved it; authenticate current
  access without asking the same decision again.
- Preflight implementation, runtime MMC binding and selector source repair:
  independently accepted offline; only applicable physical delivery remains.
- Recovery export composition, inactive printer interface and boot-health
  composition: accepted offline; retain their separate physical/integration gates.
- Beelink storage expansion: completed. The coordinator root is a separate host.
- `h12-expired-preflight-return-guard`: unapproved contingency, not an active
  implementation assignment. Preserve its proposal/record; reconsider only if a
  specific remaining control failure demonstrates a need.

## Execution, authority and dependencies

One production implementation at a time. Exact high-consequence reviews remain
required; use existing owner authority without repeat permission requests. The
owner's temporary Astra/high exception applies to concluding H12; normal role
mapping in [the agent guide](agent-guide.md) remains unchanged for other work and
after H12. No global/project model configuration was changed. Independent roles
stay separate; supported separate-session fallback is available when native
threads cannot launch, with actual runtime and role contract recorded.

No physical owner action is requested by this reset. Combine later sensor,
peripheral and attended commissioning needs in [the existing H queue](../docs/hardware/coordinated-human-tasks.md).
No new backup, board photograph, external adapter, soldering or stock-machine
requirement is added to G1 solely for boot capture. True cold-boot reliability
and stock qualification retain their later evidence requirements.

Optional features remain paused; no scheduling or publication is enabled.
Branch/worktree presence is evidence retention, not an active assignment. All
original candidates, failures, reviews and artifacts remain preserved.

## Tracker status

The repository goals above are reset. The application still holds the previous
unfinished goal with status `blocked`. A replacement request on 2026-10-01 was
rejected because an unfinished goal exists; available tools cannot edit its
objective or resume/cancel it. Its objective is not complete and must not be
marked complete to bypass that restriction. This UI limitation does not prevent
manually continuing authorized work from G1.
