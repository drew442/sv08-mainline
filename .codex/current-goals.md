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
| G1 — Restore SD control and pass H12 preflight | Active priority; capture, SD return, reconciliation and corrected selector delivery passed; physical preflight reached RAM but refused claim, automatic return stopped in SPL DRAM training | Arrange a fresh reviewed USB reset/SD return window; deliver the independently accepted startup repair using a fresh job; keep failed jobs retired | Reconcile named spare/controller/CID, both environment records, RTC and read-only p5; stage the accepted selector repair with fresh signed inputs; actual preflight and required automatic return pass |
| G2 — Complete writerless reimage and reliable commissioning host | Queued behind G1; offline writer/handoff accepted, physical urh-05 open | After urh-04, establish exact urh-05 authority, reviewed source image and recovery path; perform write/readback/return as separate admitted operations | Physical full-image verification and automatic return pass; selected commissioning host has captured normal boots, persistent access/state, working administration and sufficient boot/DRAM reliability for commissioning |
| G3 — First working printer on test-sv08-01 | Offline interface and paired MCU work accepted; physical commissioning open | Complete remaining candidate substitutions and essential sensor/heater facts; activate only on the ready matching host/MCUs | Attended inputs, fans, motor direction, homing, controlled heat, calibration and first print pass, including pause/resume/cancel/shutdown |
| G4 — Complete factory-capacity host OS and recovery | Many components/VM journeys accepted; assembled product incomplete | Integrate accepted components and address remaining required administration, update, restore and peripheral gaps in bounded slices | Complete factory-capacity artifact, signed physical A/B health/fallback, persistent identities/state, required interfaces/peripherals and independent export/restore/recovery meet the host checklist |
| G5 — Supported stock release | Future qualification; no profile release-qualified | Prepare source/license and reproducibility closure while actual stock access and owner license decision wait | Actual stock commissioning, representative prints, clean install, recovery/failure/update regressions, documentation and release decision pass |

G3 may begin when its actual host and sensor prerequisites pass; it need not wait
for every G4 administration or G5 release feature. G4/G5 authorized preparation
may proceed while physical work waits. This ordering does not waive the accepted
writerless milestone or make a physical full-image write implicitly authorized.

## Live H12 window — 2026-10-01 13:38 UTC

Following the owner's concern about stalled execution, current work is focused on
H12. Required G4 rollover has design approval but no implementation is running.
The fresh D receiver passed exact independent high-consequence review and live
admissions, then started at 13:37:33 UTC. Independent readiness at 13:38:22 passed:
PID 77432/starttime 28608617, exact supervised unit/commands, passive C stopped,
zero UART owners, bridge still present and no disconnect observed. It waits until
14:07:33 UTC for one physical USB unplug of at least five seconds and same-port
reconnect, PSU still off and SD/eMMC untouched. The owner has been asked for the
step after readiness; elapsed time is not a completed physical action. This dated
window supersedes the expired C request. Do not act after expiry without new
readiness. H12/preflight remain incomplete. Private source, review, corrected
manifest binding and live receipts are in
`local/feature-workflow/probes/h12-cold-sd-return-20261001d/`.

While D waits, offline source preparation passed at 13:53 UTC: a separate
Beelink source directory contains the preserved C build inputs and the exact
accepted startup-repair writer and test from `0708a18a2528929ad9a59c22e32d865003e95ed2`.
A separate readback checked all 36 copied entries and the preparation receipt.
No job, keys, target policy, listener or candidate artifact was created. Historical
C inputs remain provenance; fresh SD intake must supply current target policy
before a newly signed candidate is prepared. The original C directory is retained.
Private preparation/readback evidence is beside D's receiver evidence above.

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
Fresh job B staging and expired-token retirement subsequently passed. B stayed unarmed and expired during review; its complete artifact remains on Beelink. Distinct fresh job C then passed staging, arming, marker publication and independent readbacks. Its corrected selector reached RAM preflight at 11:32 UTC, but the runtime refused the claim before target preflight acceptance. The server claim remained unused; automatic return stopped in SPL DRAM training. G1 is incomplete. The reviewed cold-return receiver waited until 12:22 UTC without observing a
physical disconnect, then stopped with zero captured bytes. Independent passive
capture restoration passed: PID 75865 is the sole UART reader, with the original
log inodes preserved. The dated reset request has expired; a new operation needs
current receiver readiness. No software reset was issued at the SPL halt.
The bounded claim-startup repair passed fresh independent Astra/high delivery
verification at `0708a18a2528929ad9a59c22e32d865003e95ed2` and is integrated;
its offline feature task is done. The verifier reproduced 42 startup scenarios,
the purpose regression, focused receipt regressions and four before/after ARM64
builds. This does not establish the physical claim failure's errno or pass H12.
See the [physical attempt](../docs/hardware/host-h12-boot-capture-rethink-20261001.md#corrected-preflight-entered-ram-but-did-not-pass).

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

The reset initially added no physical owner action. The subsequent measured SPL
halt now needs a prepared, independently reviewed physical USB reset to regain
SD control; software keyboard/SysRq requires a running host. Combine later sensor,
peripheral and attended commissioning needs in [the existing H queue](../docs/hardware/coordinated-human-tasks.md).
No new backup, board photograph, external adapter, soldering or stock-machine
requirement is added to G1 solely for boot capture. True cold-boot reliability
and stock qualification retain their later evidence requirements.

Optional features remain paused; no scheduling or publication is enabled.
Branch/worktree presence is evidence retention, not an active assignment. All
original candidates, failures, reviews and artifacts remain preserved.

## Latest required G4 delivery

While H12 waits for the physical reset, the required recovery-intake receipt race
was corrected, independently verified by a fresh Sol/medium session and integrated.
The offline task is done, with a reproduced baseline false success and 23 passing
tests. See [the record](../docs/features/recovery-intake-receipt-binding/record.json).
Fresh downstream image assembly and physical recovery gates remain open.

## Coordinator resources

Disk pressure was relieved by moving one closed historical QEMU disk to a durably
verified private Beelink archive before retiring its local duplicate. About 1.3 GiB
was recovered; original bytes and restore metadata remain preserved. See
[the storage record](../docs/development/artifact-preservation-20261001.md).

## Tracker status

At 12:07 UTC the application returned no current goal. A fresh G1–G5 goal was
created at 12:11 UTC and is active. Earlier replacement refusals remain historical
evidence in the reset assessment; they no longer describe current tracker state.
The project remains incomplete and physical dependencies remain explicit.
