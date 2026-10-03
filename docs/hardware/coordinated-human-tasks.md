# Coordinated human tasks

**Owner scope change, 2026-10-02:** Keep installed-eMMC reimaging using SD
maintenance, simple target/image checks, full write verification and an attended
yes/no prompt. Abandon RAM maintenance, permission anti-forgery/anti-replay and
secure-randomness work, and complete cold-boot capture. Automatic maintenance
launch and automatic recovery return are deferred until further notice. SD
recovery is sufficient. The separate rehearsal is dropped; incorporate minimum
target/image checks before the flashing yes/no prompt. The old RAM preflight
is not a gate.
The [owner-selected scope](../decisions/20261002-h12-scope-reduction.md)
supersedes conflicting historical requirements below. The attended SD software delivery is now independently verified on installed
ARM64 fixtures. Physical write/flush/full readback passed on October 3 at 05:23 UTC;
manual SD removal/restart and normal installed boot are still pending.

Dispatch queue created 2026-09-18 for the [parallel assignments](../development/parallel-work.md).
Pending entries below are coordination items, not requests to act immediately;
completed entries retain their result for reuse.
Historical evidence and detailed acceptance remain in the [host tasks](host-os-tasks.md#human-and-powered-printer-tasks),
[recovery tasks](test-sv08-01-recovery-tasks.md) and [sensor bring-up](test-sv08-01-sensor-bringup.md).
Do not interpret old unchecked preservation or v1 imaging tasks as new requests.
The owner has accepted existing backups and USB-reader/ST-Link recovery paths.

Only the coordinator asks the owner to act. Agents submit additional consumers
or prerequisites against an existing H ID before proposing a new physical task.
No current power state, reachability, installed slot or hardware identity is
inferred from a historical report. Inspect current state before acting.

## Attended SD reimage — final manual boot check, 2026-10-03

The [concrete session](host-h12-attended-sd-session-20261003.md) completed the
actual 7,818,182,656-byte spare-eMMC write, flush and full readback successfully.
Owner repaired KVM video; the corrected keyboard UI passed separate delivery
review, and a fresh exact action review preceded autonomous KVM confirmation
under the owner's delegation. Final KVM result, closed source/target descriptors,
matching runtime/configuration and device byte counts are retained.

Owner reported completing the restart and added an HW-667 relay for USB host
power. The [relay test](host-hw667-test-20261003.md) passed: five seconds off,
automatic power restoration, new host boot ID, SSH and KVM recovery screen.
However, the 16 GB SD remains detected and supplies the running root; the 32 GB
spare eMMC is unused. A clarification about SD removal/reinsertion is pending.
Do not remove the running SD while powered. Resolve that physical fact, then use
an unpowered SD removal and observed installed-system boot to finish H12. No
repeat flash, permission/entropy work or cold-capture investigation is required.

## Independent SD-loader restoration — 2026-10-02

The owner completed the power-off SD-only move to Beelink. Read-only inspection
matched the rescue card identity and found the managed loader still installed.
The original independent SD-only loader has now been restored after separate
GPT-6.1 Sol/high exact review. Only the previously overwritten 786,225-byte span
at byte 8192 changed; full direct 738,197,504-byte prefix readback matches the
original recovery image. FAT/root/GPT are preserved; eMMC/MCUs were not accessed.
The original partial-write helper is excluded and preserved; v2 stops without
retry. Durable beforeimage and independent post-write/process/card reconciliation
passed. See [the restoration record](host-h12-sd-loader-restoration-20261002.md).

The separately reviewed one-connect boot succeeded at approximately 02:31 UTC.
Authenticated SSH, wired DHCP, kernel 6.18.51-sv08-candidate1, read-only SD root,
recovery-display service and no failed systemd units were measured. The owner
was released from immediate physical attendance; leave USB connected and PSU OFF.
Beelink card absence was verified and udisks2 restored active/enabled.

Fresh read-only spare intake and off-target p5 reconciliation passed. Both raw
environment records have valid CRCs, flags 9/8 and zero A/B counters; the expired
C arm token remains and its p5 marker is absent. The initial intake checked the
wrong capitalization and falsely reported token absence; actual staging stopped
before any write, exposing that error. Exact reviewed token retirement is pending. Linux/RTC were corrected after independent Sol/high
review and independently checked against synchronized Beelink time. The complete
p5 beforeimage is durably preserved off target. Source preparation for the fresh
accepted startup repair passed: 27 entries verified, current staging node/dev_t
bound to `/dev/mmcblk2` / `179:8`; no job, keys, artifact or listener created.

Next, prepare and stage/arm/activate a fresh repaired preflight while independent
SD SSH works, then restore the exact accepted managed loader last and use one
reviewed SSH reboot. Its automatic dispatch preserves the required original-p5
return route. No new loader implementation or UART commands are needed. Exact
operation reviews and actual preflight/automatic-return evidence remain required.
The owner confirmed availability for the attended test. Fresh signed repaired
artifacts and volatile transfer passed; exact expired-token retirement is now
being reviewed before staging. No reboot or new physical action is requested yet.

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

## Current dispatch — 2026-10-02

The owner has removed complete initial cold-boot capture as an active dependency.
Record missed early bytes as a limitation and use warm reboot, human recovery,
HDMI/SSH and bounded practical trials. No new external receiver, alternate UART,
soldering or cold-capture framework is requested. Actual later cold-start
reliability remains to be tested through boot outcomes.

The latest October 2 04:53 UTC physical preflight reached trusted RAM but timed
out acquiring secure randomness before creating a claim socket. The claim stayed
unused; the listener is now stopped. Automatic return passed U-Boot and started
the original p5 kernel; the recovery screen and final environment/marker readback
remain unverified. G1/H12 are incomplete.

Current owner request: unplug USB power, keep PSU OFF and do not reconnect.
Confirmation of completed power removal and whether the recovery screen appeared
is pending. Earlier leave-connected instructions are historical and superseded.
The managed SD loader is the last measured installed loader. Prepare a separately
reviewed independent-SD recovery operation before requesting another media move
or boot. Offline bounded entropy repair may proceed meanwhile; no more UART input
or cold-capture investigation is assigned.

D's October 1 USB-return window expired at 14:07:33 UTC without observing a
disconnect, capturing zero bytes. Its controller is inactive. A separate October
2 00:19 UTC postcheck verified passive serial monitoring restored, PID 79976,
sole read-only UART owner, pinned source and original log inodes. All dated cable
instructions are expired; do not act on them. Original review and failed-attempt
evidence remain preserved. An earlier October 2 SSH reachability probe returned
no route; later authenticated SD access supersedes that observation above.

H03's media-move instructions below are historical. H09/H10 and H13 retain their
completed evidence. Physical preflight and full-image installation remain open;
warm capture alone does not pass them. H11 physical A/B acceptance remains future
work. See the [current goals](../../.codex/current-goals.md) for the active order.

H01/H05 essential sensor facts and reference measurements, H04 peripheral checks,
H06 attended printing, H07 failure/recovery and H08 stock/license work remain
open only to their actual unresolved extent. See [current goals](../../.codex/current-goals.md)
and [assessment](../development/goals-reset-20261001.md). Preserve the dated
history below without treating old counters or reachability as current facts.

| ID / shared action | Prepare before asking | Consumers and execution order | Evidence reuse / invalidation |
| --- | --- | --- | --- |
| H01 — One accessible, fully unpowered inspection | Consolidated list of unresolved board/sensor facts, existing marking evidence and a safe isolation procedure; no unnecessary heatsink removal | Host PCB/DRAM/radio/PMIC identity; installed bed/hotend sensor and circuit identity; outstanding board revisions | One private evidence set with public nonsecret conclusions; repeat only for changed hardware/wiring or an unresolved essential detail |
| H02 — Power state and boot session | Account for USB back-power; review intended image/slot/boot environment and safe printer state; keep serial recording open for warm reboot where useful | Actual cold-start/DRAM boot outcomes, warm boot, ordinary MCU start, host health and A/B transitions, HDMI/SSH observations | Complete initial cold-boot serial capture is a recorded limitation, not a gate. Record distinct boot results/IDs and available observations; repeatability needs multiple boots. Loader/kernel/firmware changes invalidate affected checks |
| H03 — Write spare eMMC and reinstall | V5 is independently byte-reviewed, written once to the identified spare, and full direct-I/O readback matches the raw SHA-256. Beelink's receive-only serial capture is armed and waiting. The writer has been safely powered off through Beelink. With the printer unpowered, unplug the writer, reinstall only the spare eMMC, and stand the printer upright; keep the factory eMMC stored. Then connect the USB serial cable to Beelink (this powers the host). | V4's A boot failed during preparation and the next U-Boot pass selected recovery. V5 contains the corrected persistent-identity initramfs hook. Capture the first v5 boot, assess A/recovery behavior and record HDMI mode. Do not power-cycle again until logs are checked and the next boot is planned. | The exact v5 image hash and direct readback receipt are recorded; any media alteration or write/readback mismatch requires revalidation. Continue reusing the same capture for boot consumers |
| H04 — One physical console and peripheral session | Installed reviewed UI and input tests ready; keep Ethernet recovery; prepare private Wi-Fi configuration and camera test; optional capture/HID setup only if useful | Normal HDMI/touch, recovery touch-only/keyboard-only/mouse paths, Wi-Fi association/reconnect, retained camera presentation/streaming, USB/peripheral observations | Record image, input device, network conditions and path separately. A normal desktop observation does not prove recovery; changed UI/driver/device invalidates affected results |
| H05 — Sensor reference and input session, outputs disabled | Reviewed input-only config, matching host/MCUs, exact queries, independent temperature instrument and known physical associations | Current bed/hotend ambient comparison; probe and filament operation/polarity; resolve sensor identity from H01 before accepting conversion | Record simultaneous references/configuration and input transitions once for printer and host consumers. Old room temperature cannot satisfy a new reference check |
| H06 — Attended staged output and printing session | H05 passes; reviewed limits/homing/stop procedure; operator can stop immediately; safe mechanics and clear workspace | Separate gated steps: fans/shutdown → bounded motor direction → X/Y sensorless and Z probe homing → controlled heat/reference → PID/extrusion → leveling/mesh/manual Z offset → first layer/prints/pause/cancel | Each step has its own result and must pass before dependent action. Reuse host UI/camera observations during safe prints; changes to mechanics/sensors/firmware/config invalidate relevant results |
| H07 — Controlled failure/recovery session | Reliable baseline, reviewed failure plan, expendable data, loads safe, captures and restoration artifacts ready | Power interruption, A/B exhausted/bad trials, watchdog, physical checks consuming recovery delivery's reviewed export/restore artifacts, partial MCU update and USB-reader recovery checks | Group ready cases in one session but preserve individual outcomes and distinct safe states. Deliberate interruption is not bundled into heating/printing; final artifact changes require relevant retests |
| H08 — Release decisions and stock access | Concise unresolved license/omission choices and a stock qualification plan; no re-asking settled OS/backup decisions | Owner license decision, any actual required-feature omission, access to an actual stock profile for supported-stock qualification | Record decisions once; modified test printer first print is independent of stock access, and never certifies stock support |
| H09 — Correct and retry the supervised SD/NFS diagnostic — **passed 2026-09-26** | The first physical attempt selected the SD loader twice but stopped before Linux because `CONFIG_HASH_VERIFY` was missing; see the [first-boot record](host-sd-network-first-boot-20260925.md). The corrected 192 MiB image SHA `53cc0b2696add39dae24480167d79807e72a15f824fbc9025aaf20a9aa63d08a` has independent GO WITH CONDITIONS review and passed write/readback on the identified SU02G card. | The owner reinstalled the disposable SD with the printer fully powered off, stood the printer upright, and reconnected serial after receive-only capture was waiting. The single supervised retry completed and powered down as designed. | The [v2 result](host-sd-network-first-boot-20260926.md) records SD loader, Linux, wired DHCP, read-only NFS root and the exact `SV08_SD_NFS_PASS root_ro=1 data_tmpfs=1 dhcp_address=1` marker. Keep both boot traces separate. H10 subsequently measured the eMMC environment records; see its result. HDMI output, normal host operation and printer functions remain separate work |

| H10 — Read current spare-eMMC boot state — **passed 2026-09-26** | Exact SD image passed reviewed direct-I/O write/readback; corrected NFS init, `.141` read-only/root-squash export and default NFSv3/TCP mount were hash-checked. Independent Sol review authorized one supervised read-only boot. | The owner installed the spare eMMC and same SD with host power off, kept the factory eMMC stored, and reconnected serial only after receive-only capture was armed. Wired DHCP and NFS boot completed; Linux exposed `/dev/mmcblk0` (61,079,552 sectors). Both 64 KiB U-Boot environment copies passed CRC and recognized-layout checks. Copy at 4 MiB reported flag 3, order A, A=3/B=0; copy at 8 MiB reported flag 2, order A, A=2/B=0. Probe used O_RDONLY/fixed-offset reads and powered the host down after success. | The [H10 record](host-sd-network-emmc-probe-20260926.md) contains the exact sanitized console markers, distinction between measured copies, and private Beelink trace hash. This proves only the bounded environment read and SD/NFS diagnostic checks; it does not validate boot policy, normal OS operation or printing. No more H10 boot is planned. No eMMC, boot-policy or MCU writes. |

| H11 — Commission unattended signed A/B update — queued after offline implementation | A deployable board image and release backend are complete; signed test bundle/feed, update keyring, recovery path and exact active/inactive partition map have passed independent offline and high-consequence review. The current diagnostic image is non-deployable. | Keep the spare eMMC installed and factory module stored. On an idle printer, use available serial/HDMI/SSH observations; complete first cold-boot bytes are not required. Keep USB serial connected for warm reboot capture where applicable. Leave the writer and SD diagnostic disconnected. Allow one reviewed signed test release to stage into the inactive OS pair and arm for next normal boot; observe boot health and fallback readiness without printer-output tests. | Stop on profile/slot mismatch, policy opt-out, customization, busy printer, unexpected write target, an unreviewed environment change, changes to shared GPT/recovery/data/MCU regions, or uncertain outcome. Environment records must remain byte-identical during stage; arm may make only the reviewed order/counter/flag change while preserving all other fields. Preserve the running source pair as fallback and overwrite only the reviewed inactive OS pair. Record this one validation session separately from routine updates; no physical write until the exact release and target have independent review and explicit action authorization. |
| H12 — Attended installed-eMMC reimage from SD | SD recovery/SSH works. Implement the [owner-selected ten-point scope](../decisions/20261002-h12-scope-reduction.md): basic target/image checks integrated before yes/no, followed by write/flush/full readback. No separate rehearsal, RAM maintenance, permission service or cold-capture work; automatic launch and return are deferred. | Prepare the exact image/target and independent review, then use SD maintenance and explicit Yes to start. Operator manually restarts afterward; SD recovery is sufficient. No new physical action is requested by this documentation update. | Stop on wrong/ambiguous target, insufficient capacity, source/target overlap, target in use, image/checksum failure or transfer/readback failure. No/absent confirmation writes nothing. A later invocation asks again; repeated prompt handling is left to the operator. |

H12 coordination update, 2026-09-29: the installed SD loader was reached through
one reviewed keyboard reboot, then its measured stopped prompt was continued
with verified SD/script commands. KVM again shows the SD recovery GUI. See the
[actual continuation and capture limitation](host-stopped-prompt-resume.md).
No media move or additional power cycle is requested. The one pending owner
input is whether to allow initial enrollment of this boot's regenerated SSH key
using the measured physical/network target evidence; the failed supervisor missed
its console fingerprint. Keep that question deduplicated under H12. No job,
claim, writer marker or whole-eMMC write has been armed. The separately proposed
[nonwriting physical preflight](../features/h616-physical-preflight/proposal.md)
addresses the missing urh-04 executable; its proposal reconciles the target-open
wording explicitly, without claiming a passed hardware gate.

The [2026-09-23 v3 board candidate](host-board-image-20260923-v3.json) passed
offline byte review and direct readback on the identified spare. The owner
reinstalled the spare, and [H02/H04 partial evidence](host-board-v3-first-boot.md)
now covers captured slot-A boot, HDMI/KVM video, USB keyboard login and temporary
Wi-Fi association. H03's physical reinstall is complete for this candidate.
The printer still needs the corrected host image for persistent Wi-Fi and normal
boot-health integration. A reviewed live rearm restored three A attempts without
rebooting; see the [v3 record](host-board-image-20260923-v3.json). Touch,
B/recovery and output checks remain separate open H04/H02/H05-H07 work. Arm
serial capture before the next reboot.

The [2026-09-24 v4 diagnostic image](host-board-image-20260924-v4.json) is a
fresh-root rebuild that includes NetworkManager Wi-Fi support and a private,
persistent owner-provided Wi-Fi profile. It passed independent offline byte
review, including the exact v6 loader and complete six-partition image. Its raw
image is 7,818,182,656 bytes (SHA-256
`7e41e123c7a219feb63e549f2e00425f2a75de548b95b1129f459a20cd8a0d13`); its
compressed package is 966,683,880 bytes (SHA-256
`7b60bf88483be861119ac3fcb4e95bb6cc5c0c6f36f22cf3bb35cfb4578ac7bc`). On
2026-09-24 it was written to the previously installed spare using the
05e3:0747 USB reader after immediate independent GPT-6 Sol review. The
31,272,730,624-byte target was unmounted. An exclusive block-device open wrote
exactly 7,818,182,656 bytes, followed by fsync/device flush and a full direct-I/O
readback with the exact raw hash above. The six partition identities match.
The GPT backup header remains at the end of the 8GB image footprint while the
rest of the 32GB module is left unused by design; it was not relocated or
expanded. The reader was safely powered off, and the private receipt is retained
on Beelink. The owner-accepted backup and recovery path remains in force; no new
capture was requested. The owner reinstalled the spare. The first captured A
attempt failed in `sv08-prepare.service`; a subsequent boot entered independent
recovery after DRAM geometry differed and U-Boot found no eligible slot. The
[v4 first-boot record](host-board-image-20260924-v4-first-boot.md) preserves the
trace summary. The custom 1024×600 EDID was also applied to the GL-RM1V2; physical
panel mode validation remains outstanding. Keep the factory eMMC stored.

The [2026-09-25 v5 diagnostic image](host-board-image-20260925-v5.md) passed
independent offline byte review, was written to the identified spare, and passed
full direct-I/O readback. Its compressed and expanded hashes match the receipt;
the six partition identities and sizes are correct. The backup GPT remains at
the reviewed 8 GB image boundary. V5 has booted A and reached SSH/Wi-Fi and HDMI;
see the [first-boot record](host-board-image-20260925-v5-first-boot.md). Health
confirmation remains masked. A was re-armed to three attempts without rebooting;
see the [re-arm record](host-board-image-20260925-v5-a-rearm.md). H03 is complete
for this image. H09 now groups the SD/NFS diagnostic boot prerequisites; its SD
priority is measured, while its physical Linux network root remains unverified.

The H09 owner DHCP reservation is confirmed. The original [disposable SD/NFS
image](host-sd-network-root-prototype.md) was written and read back, and the
first physical attempt selected its SD loader but stopped at the script hash
check. See the [write receipt](host-sd-network-card-write-20260925.md) and
[first-boot result](host-sd-network-first-boot-20260925.md). Beelink currently
owns `192.168.1.136` at MAC `84:39:be:9e:10:d9`; the sanitized export is active,
read-only with root-squash, and passed a Beelink-local NFSv3/TCP mount, hash
check and write-refusal probe. The corrected candidate is written and passed
direct-I/O readback; one supervised printer boot remains.
Receive-only capture is active and will be rechecked before serial reconnection.
The next owner interaction is one deduplicated SD move to the writer; no eMMC or
MCU action is involved. H09 remains open until Linux DHCP/NFS behavior is
captured on the printer.

Current dispatch on 2026-09-27 supersedes the historical H09 preparation
paragraphs above: H09 and H10 passed, the spare v5 eMMC is installed according
to the owner's last physical report, and the factory module remains stored.
For H12, the only immediate owner setup is to make the printer reachable on
wired Ethernet, with Beelink able to reach `192.168.1.141`; no media move is
requested. The coordinator can then prepare receive-only serial capture before
the owner connects USB serial, because that connection powers the host. Keep
the printer's current power state and cabling explicit at that handoff. The
read-only live identity/space check and the later reviewed handoff/write use
this single H12 session rather than repeated media swaps.

Current dispatch on 2026-09-28 supersedes the no-more-H10-boot note and the
2026-09-27 no-media-move dispatch for this replacement-card test only. The owner
requested a fresh 16 GB SanDisk SD because the previous card may be faulty.
The [replacement-card receipt](host-sd-replacement-20260928.md) records reviewed
write/readback, restored persistent NFS services and armed receive-only capture.
The single next physical action is to fully remove printer power including USB
serial, move the new SD from Beelink to the printer while retaining the spare
eMMC, and reconnect Ethernet/USB for one captured diagnostic boot. Keep the
factory eMMC stored. H12 writes remain pending separate physical checks/review.

Current dispatch on 2026-09-29 supersedes the replacement-diagnostic boot
dispatch. Its captured read-only checks passed and it intentionally powered
down. The owner requested an unchanged upstream CB1 minimal SD baseline;
see its [artifact and boot-review record](host-cb1-baseline-sd-20260929.md).
For this single comparison, fully disconnect printer PSU and USB back-power,
remove and store the spare eMMC, and install the prepared SanDisk SD with neither
eMMC module installed. Keep PSU off, connect Ethernet and reconnect USB serial
after capture is confirmed ready. This prevents upstream first-boot resize
from writing either eMMC. No installer, MCU, heater or motion operation is
included. Observe console/HDMI/DHCP and stop on unexpected behavior. H12 remains
pending; no repeated SD/NFS diagnostic is requested.

Current dispatch on 2026-09-29: **H13 — Running SD recovery host, host-only boot passed**
supersedes the completed CB1 comparison dispatch above. The owner observed that
baseline boot; its serial capture was empty. The running replacement's
[offline evidence](host-sd-recovery-host.md) covers normal GTK recovery and
public-key SSH, with no automatic media, MCU, boot-policy or printer operation.
Independent delivery verification, exact SD write review, complete prefix
readback and read-only filesystem/layout checks have passed; see the
[prepared-card receipt](host-sd-recovery-host-write-20260929.md). The [physical boot result](host-sd-recovery-host-first-boot-20260929.md) records
normal GTK/SSH, native HDMI mode and read-only eMMC intake.

The completed owner action was to remove all printer power, including USB serial,
move only the prepared SanDisk SD from Beelink to the printer, reconnect Ethernet,
and reconnect USB serial after the coordinator confirms receive-only capture is
waiting. Keep PSU off for this host-only test and the factory eMMC stored. No
spare eMMC move is required; record whether it is present. Observe normal init,
continued recovery GUI, wired DHCP and authenticated SSH; physical display/touch
and controller behavior remain unvalidated until observed. Disconnect USB power
and stop on unexpected activity. H12 eMMC writing and all printer commissioning
remain separate pending gates. This is a single shared H02/H04/H12 preparation
session, not repeated media requests from individual agents.

## Session dispatch and result record

The printer lane now has a [shared commissioning session form](test-sv08-01-commissioning-session.md)
for H01/H02/H05/H06. Its blank fields are preparation, not a request to repeat
existing evidence. The coordinator has already supplied the
[sanitized candidate section inventory](../development/printer-candidate-sections.md);
the owner does not need to recreate it or expose private configuration to agents.

Each request must list: H IDs, exact physical target/action, prerequisites that have
passed, which agent has armed capture, expected observations, stop conditions and
the next ready action while the setup remains connected. Do not ask for a media
move until the reviewed bytes and writing procedure are ready.

For each result record date, target/profile, artifact/configuration/firmware hashes
where relevant, observation/capture reference, passed/failed/inconclusive result,
consuming requirement/check IDs and remaining exclusions. Keep secrets, raw
captures and machine-specific measurements in appropriate ignored local paths;
commit only the safe evidence summary. Each consuming checklist links that same
result instead of requesting another human action.

Recommended setup sequence when required prerequisites are ready: H01 inspection;
H03 writer transfer only if necessary; H02 captured boot; H04 console/peripherals;
H05 inputs; H06 staged commissioning. H07 is a separate controlled session after
baseline acceptance. H08 decisions can happen independently. Availability may
change this order, but never bypass an input, motion or thermal gate.

No entry is marked done merely because its instructions exist. The coordinator
records actual session results here or links a canonical existing evidence record
before closing its consumers. Preparing an offline package remains useful while
any human entry is pending.


## H12 continuation — 2026-09-30

The [nonwriting preflight](host-h616-physical-preflight.md) now has independent
offline delivery acceptance at `035b36f`, merged locally with its completed
[feature record](../features/h616-physical-preflight/record.json). The original
failed candidate and review are retained. Forty-seven affected tests and thirteen
independent critical checks passed; the representative FIT is 48,899,052 bytes.
Static resource evidence does not prove H616 relocation, DRAM reliability or
physical urh-04/05 acceptance. Legacy commissioning binaries lacking the new
compiled-purpose evidence need rebuilding and a newly reviewed artifact hash.

The approved urh-04 wording reconciliation permits an exclusive whole-device
O_RDONLY descriptor for capacity/device identity and both raw environments.
Image/environment transfer writes are excluded from the preflight executable;
marker consumption still changes p5 metadata. This supersedes this queue's older
"without whole-device target open" shorthand without marking any hardware check
passed. Exact p5 stage, boot-policy arm and preflight boot each retain their
separate target/artifact/recovery review and owner-authority gates.

A fresh network-only observation through pinned Beelink access found SSH at
`192.168.1.141` and the previously measured wired MAC. The offered volatile SSH
fingerprint matches the one already awaiting the H12 identity decision. The
coordinator requested that same pending owner decision with the exact fingerprint;
no key enrollment or printer SSH login occurred. An earlier independent operation
review refused enrollment without console fingerprint evidence and permits only
a trusted match or explicit owner decision for this boot. Fresh authenticated
Linux/RTC/environment intake and actual job preparation remain pending. No
additional media move or power cycle is requested.


H12 update, 2026-09-30: [authenticated fresh intake](host-h12-authenticated-intake-20260930.md)
resolves the key-enrollment decision under the owner's address-based trust
authorization. Current spare CID/GPT/environment CRCs agree with earlier intake;
eMMC now enumerates as `/dev/mmcblk2`. Linux and RTC agree. Reviewed read-only p5
inspection now confirms the original recovery script and 154,374,144 bytes free.
Fixed mmcblk0 admission requires a reviewed repair for current mmcblk2 before
staging. Reviewed environment exhaustion and physical urh-04/05 remain.
The [approved preflight clarification](host-h616-physical-preflight.md) permits
whole-target O_RDONLY identity/capacity/environment reads, with no O_RDWR or
image/environment transfer writes. Marker consumption still changes p5 metadata.


H12 preparation update,2026-09-30: the signed phase-aware node-binding repair
passed fresh independent high offline delivery review and is integrated locally.
The separately reviewed [volatile workspace limit](host-h12-workspace-20260930.md)
now accommodates bounded future artifact verification; no artifact is staged.
No additional key-enrollment decision or media move is needed. Fresh physical
preflight jobs/artifacts, receive-only capture and exact staging/arming/boot
reviews remain pending. Physical urh04 permits the accepted compiled preflight's
whole-target O_RDONLY capacity/environment admission; urh05 whole-write/readback
is separate and follows urh04. Existing printer-output gates remain open.

H12 update,2026-10-01: [first physical urh-04 attempt](host-h12-urh04-first-boot-20261001.md)
staged/armed/activated and passed their separate readbacks, then one reviewed
ordered boot selected the preserved original recovery script without entering the
preflight FIT. U-Boot loaded bad-CRC/default environment from SD; the spare's valid
armed environment did not reach the selector RAM guard. Claim remains unused;
urh-04/05 remain unpassed. The required selector environment repair has passed independent offline delivery
verification and is merged locally; see [accepted repair evidence](../design/unattended-emmc-reimage-handoff.md). Keep setup/media unchanged; no retry/rearm/second
boot/marker removal/full-image action. Original GUI visual confirmation is pending.
Standing urh-04 authority is recorded; later exact reviews/current gates remain
required without repeated same-scope permission.


H12 capture update, 2026-10-01: [one reviewed warm-reset experiment](host-h12-boot-capture-rethink-20261001.md)
kept USB power/serial connected and captured SPL, DRAM initialization, main U-Boot
and Linux recovery using the existing KVM keyboard. The capture obstacle has a
measured solution; no media move, new adapter or soldering is currently required
for warm-boot capture. A future need for true cold-start capture can use a separate
RX-only receiver after identifying the actual console TX point and signal level.
The next bootloader interception/SD return is a distinct reviewed operation under
existing owner authority. Original recovery reached its target; H12 preflight,
current raw environment/marker/RTC reconciliation and printer commissioning remain
open. The prior failed attempt and unapproved return-guard proposal are preserved.

H12 SD-return update, 2026-10-01: the separately reviewed warm reboot intercepted
U-Boot and booted the hash-verified SD script. Authenticated SD SSH and passive
serial collector restoration passed. Fresh intake and a reviewed read-only p5
inspection identify the same spare, valid environment records with zero A/B
counters and the expired token, and the unchanged staged preflight chain with
its marker still present. Linux/RTC agree within one second. Fresh signed
preflight preparation/build passed on Beelink with the accepted selector repair.
Exact retirement/staging, arm, activation, boot and physical automatic return
remain open; this is not urh-04 or urh-05 acceptance. No new owner hardware action
is required for the next G1 operation under unchanged setup and standing authority.


Later inspection of the same preserved boot trace establishes that the automatic
return reached `sv08-recovery.target`; systemd reported startup complete in
59.976 seconds. Its read-only recovery report records the recovery UI processes
and root on p5 with `ro,norecovery`. This extends the return evidence beyond kernel
entry, but is not a human screen/input observation or raw environment/marker
readback. The previously requested power-removal confirmation remains pending.


Current checkpoint 2026-10-02 05:54 UTC: owner power-off/SD-reader move confirmed;
second original-loader restoration and independent closure passed. Offline secure
entropy repair is complete. One independently reviewed SD reinstall/USB connection
is ready until 06:24:31 UTC, with PSU OFF/spare installed/factory stored and owner
nearby for two minutes. Stop by USB power removal on error or no online host in
two minutes. No extra UART/reset/reconnect is admitted. Physical completion and
fresh SD/spare/clock observations remain pending; earlier no-reconnect requests
are superseded only by this admitted one-connect instruction.


### H12 recovery checkpoint — 2026-10-02 07:56 UTC

The owner completed the second rescue-SD return/USB connection. Authenticated
SD recovery, read-only root, wired network and services passed; immediate
physical attendance is released. Leave printer USB connected and PSU OFF,
spare installed and factory eMMC stored. The connection occurred after the
instruction expiry; its unmet pre-connect freshness condition is preserved in
the [restoration record](host-h12-sd-loader-restoration-20261002.md). No repeat
boot is requested. Clock correction/readback and fresh read-only spare/p5
reconciliation passed. A later preflight needs its own prepared exact review
and current attendance; the expired SD-boot instruction grants no retry.


### H12 goal reset — 2026-10-03

Use the [three active H12 goals](../../.codex/current-goals.md) and
[attended SD delivery plan](../development/h12-sd-delivery-plan-20261003.md).
Prepare accepted software/image/target before requesting current physical facts
and attendance. The owner’s Yes starts the actual write; after verified readback
the owner performs the prepared manual restart or SD removal/boot selection.
There is no separate rehearsal, RAM handoff, permission-service, clock-expiry,
automatic-return or complete cold-capture gate. No new physical action is
requested at the goal-reset stage; October 2 setup observations are historical.
