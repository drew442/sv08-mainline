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
| G1 — Restore SD control and pass H12 preflight | Active priority; independent SD boot/SSH restored, spare/p5 reconciled and clocks corrected; previous physical preflight failed | Prepare fresh repaired job while SD SSH works; stage/arm/activate, then restore accepted managed loader last and run one reviewed attended preflight | Reconcile named spare/controller/CID, both environment records, RTC and read-only p5; stage the accepted selector repair with fresh signed inputs; actual preflight and required automatic return pass |
| G2 — Complete writerless reimage and reliable commissioning host | Queued behind G1; offline writer/handoff accepted, physical urh-05 open | After urh-04, establish exact urh-05 authority, reviewed source image and recovery path; perform write/readback/return as separate admitted operations | Physical full-image verification and automatic return pass; selected commissioning host has captured normal boots, persistent access/state, working administration and sufficient boot/DRAM reliability for commissioning |
| G3 — First working printer on test-sv08-01 | Offline interface and paired MCU work accepted; physical commissioning open | Complete remaining candidate substitutions and essential sensor/heater facts; activate only on the ready matching host/MCUs | Attended inputs, fans, motor direction, homing, controlled heat, calibration and first print pass, including pause/resume/cancel/shutdown |
| G4 — Complete factory-capacity host OS and recovery | Many components/VM journeys accepted; assembled product incomplete | Integrate accepted components and address remaining required administration, update, restore and peripheral gaps in bounded slices | Complete factory-capacity artifact, signed physical A/B health/fallback, persistent identities/state, required interfaces/peripherals and independent export/restore/recovery meet the host checklist |
| G5 — Supported stock release | Future qualification; no profile release-qualified | Prepare source/license and reproducibility closure while actual stock access and owner license decision wait | Actual stock commissioning, representative prints, clean install, recovery/failure/update regressions, documentation and release decision pass |

G3 may begin when its actual host and sensor prerequisites pass; it need not wait
for every G4 administration or G5 release feature. G4/G5 authorized preparation
may proceed while physical work waits. This ordering does not waive the accepted
writerless milestone or make a physical full-image write implicitly authorized.

## Independent SD-loader restoration — 2026-10-02

The owner completed the power-off SD-only move to Beelink. Read-only inspection
matched the rescue card identity and found the managed loader still installed.
The original independent SD-only loader has now been restored after separate
GPT-6.1 Sol/high exact review. Only the previously overwritten 786,225-byte span
at byte 8192 changed; full direct 738,197,504-byte prefix readback matches the
original recovery image. FAT/root/GPT are preserved; eMMC/MCUs were not accessed.
The original partial-write helper is excluded and preserved; v2 stops without
retry. Durable beforeimage and independent post-write/process/card reconciliation
passed. See [the restoration record](../docs/hardware/host-h12-sd-loader-restoration-20261002.md).

The separately reviewed one-connect boot succeeded at approximately 02:31 UTC.
Authenticated SSH, wired DHCP, kernel 6.18.51-sv08-candidate1, read-only SD root,
recovery-display service and no failed systemd units were measured. The owner
was released from immediate physical attendance; leave USB connected and PSU OFF.
Beelink card absence was verified and udisks2 restored active/enabled.

Fresh read-only spare intake and off-target p5 reconciliation passed. Both raw
environment records have valid CRCs, flags 9/8, zero A/B counters and no arm token;
the old C marker is absent. Linux/RTC were corrected after independent Sol/high
review and independently checked against synchronized Beelink time. The complete
p5 beforeimage is durably preserved off target. Source preparation for the fresh
accepted startup repair passed: 27 entries verified, current staging node/dev_t
bound to `/dev/mmcblk2` / `179:8`; no job, keys, artifact or listener created.

Next, prepare and stage/arm/activate a fresh repaired preflight while independent
SD SSH works, then restore the exact accepted managed loader last and use one
reviewed SSH reboot. Its automatic dispatch preserves the required original-p5
return route. No new loader implementation or UART commands are needed. Exact
operation reviews and actual preflight/automatic-return evidence remain required.
Owner availability for that attended test has been requested and is pending;
no reboot or new physical action is requested yet.

## Earlier UART recovery outcome — 2026-10-02 (superseded by SD boot)

The owner's confirmed cable cycle completed. The receiver observed disappearance
and re-enumeration and captured main U-Boot; the host is no longer at the earlier
SPL halt. That earlier attempt did **not** reach authenticated SD Linux.
Cold-start byte capture remains a documented limitation and receives no further work.

The initial scripted SD continuation stopped without a completed command result.
An Enter-only continuation exposed a stale-prompt framing error; a separately
reviewed CR/framing correction then timed out. Each attempt stopped and passive
monitoring was independently restored. A proposed byte-paced script received an
independent **FAIL** and was never staged or run. Those failures remain preserved.

A distinct standard interactive picocom rescue received independent GPT-6.1
Sol/high acceptance with conditions in session
`01a0fa22-6734-7a32-b72f-6263c117b3e8`. Existing manual-recovery authority and fresh
setup confirmation applied; operator text/echo/Enter/result decisions reconciled
the earlier stop boundary without another scripted progression. Complete staging
and live process, UART and PTY admissions passed before input. One CR completed
the known residual and produced `mmc0 is current device` and a fresh U-Boot
prompt. The next text-only `mmc dev 0` echoed incompletely. **No subsequent Enter,
script load/source, reset or target write command was sent.** The coordinator
stopped the terminal through separate SSH. This ends UART recovery attempts;
no further terminal variants or automated retries are planned.

Independent restoration verified passive unit
`sv08-recovery-capture-h12picocomsd20261002a.service`, PID 85082/starttime
33060992, root with the pinned Python source, sole O_RDONLY UART descriptor,
12-hour/no-restart bounds, original log inodes and append-prefix hashes. Private
admission, intent, PTY, raw capture, review and restoration evidence is preserved
under `local/feature-workflow/probes/h12-picocom-sd-return-20261002a/`; preceding
attempts retain separate directories. Board revision and electrical effects of
opening/closing the UART remain unknown.

After these UART failures, the owner confirmed a USB SD reader and completed the
reviewed power-off SD move. The restoration update above supersedes that initial
preparation. SD root/authentication and installed-spare environment/RTC/p5
reconciliation subsequently passed as recorded above; repaired RAM preflight and automatic
return remain open.
Restored-loader acceptance grants no full-image-write, heater or motion authority.

## Cold-boot capture limitation — owner decision 2026-10-02

Complete initial cold-boot serial capture is not an active prerequisite for G1–G5.
USB serial powers the host before enumeration, so initial bytes may be missed.
Warm reboot capture and SD return were physically demonstrated. Use those paths,
manual recovery, HDMI/SSH observations and bounded diagnosis-driven trials as
applicable. No more cold-capture research, external-UART work, soldering or capture
framework development is assigned. This records a limitation, not a claim of
complete cold-start diagnostics or reliable boot. Later cold-start reliability
still needs actual boot outcomes; it does not require every early serial byte.

The earlier SPL halt was a recovery dependency distinct from capture. The
October 2 cable cycle reached U-Boot, but serial rescue did not reach SD Linux.
That recovery subsequently succeeded through the restored SD loader as recorded
above. Authorized offline work may proceed while next-test attendance waits.

## Closed H12 receiver window — 2026-10-01

D stopped at 14:07:33 UTC with a 30-minute timeout, no observed disconnect and
zero captured bytes. It is inactive, MainPID 0. At 00:19 UTC on October 2 a
separate read-only postcheck verified restored passive monitoring: PID 79976,
starttime 28788664, sole UART fd 3 opened read-only, pinned source, original log
inodes and supervised limits. Restoration submission alone was not counted as
success. The old unplug request is expired. This attempt did not pass preflight
or regain SD access. Private review, source and terminal/postcheck evidence remain
in `local/feature-workflow/probes/h12-cold-sd-return-20261001d/`.

Offline source preparation passed on October 1 at 13:53 UTC: a separate
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

1. Independent SD boot and authenticated SSH passed on October 2. Preserve this
   control path through fresh-job staging, arming and activation; install the
   exact accepted managed loader last after separate review.
2. Stop UART recovery attempts. Complete first cold-boot bytes are not a gate;
   reuse the measured warm-capture path later when Linux is running if needed.
3. Fresh media/environment/p5 intake and separately reviewed clock correction
   passed. Recheck necessary live admissions immediately before consequential
   actions; retain durable off-target beforeimages.
4. Use the independently accepted selector correction and freshly prepared
   preflight inputs. Reuse unchanged artifact/test evidence; independently review
   exact staging, arm and boot operations. Expired inputs are never rearmed.
5. Record real urh-04 admission and return evidence. Only then admit G2's distinct
   physical write; do not equate ordinary recovery boot with preflight success.

The October 2 serial attempts are concluded. Preserve their failure evidence;
use physical SD/media recovery rather than another UART variant. No further
capture framework or external RX investigation is assigned.

## Removed from the active path

- Early warm-boot capture: physically passed; cold-boot capture is a documented
  limitation, with no further capture-specific work assigned.
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

The subsequent measured SPL halt was recovered through the independent SD
loader. The next RAM test requires owner attendance for prompt USB power removal
if boot fails. This does not require solving cold capture.
Combine later sensor,
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

The October 2 application readback reports the existing G1–G5 goal as `blocked`.
The available goal tools cannot resume or replace an unfinished blocked goal.
The durable goal order above remains the execution record: recovery and offline
preparation have progressed despite that stale application status. The project
remains incomplete; the next attended preflight is pending owner availability.
