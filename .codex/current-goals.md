# Current subclient goals

Updated 2026-09-30. These are bounded assignments under the existing
[remaining-work plan](../docs/remaining-work-plan.md) and
[parallel delivery plan](../docs/development/parallel-work.md). The owner has
paused optional new features, but explicitly authorized the active goal to
finish a safe writerless eMMC reimage path and, on September 29, a running SD
recovery interface with SSH to replace the finite diagnostic. The work below advances that goal;
other optional features remain paused. A goal is complete only when its stated
evidence is delivered. It does not certify a printer or a release.

| Goal | Role and model | Owned scope | Completion evidence | Physical dependency |
| --- | --- | --- | --- | --- |
| H616 nonwriting physical preflight — offline delivery done | `project_implementer`, GPT-6.1 Sol / medium; separate approver and fresh `feature_verifier_high`, GPT-6.1 Sol / high; actual runtime settings observed | Distinct signed preflight purpose, compiled writer/embedded-input staging binding, bounded readers and representative artifact resources | [Delivery evidence](../docs/hardware/host-h616-physical-preflight.md) and [completed record](../docs/features/h616-physical-preflight/record.json): 47 affected tests, 13 independent critical tests and representative 48,899,052-byte FIT; accepted source `035b36f` merged locally. Failed candidate `fafb87a` and verdict preserved. | H12 key enrollment resolved by owner; fresh authenticated inventory/RTC recorded. Recovery p5 inspection and separately reviewed physical urh-04, then urh-05 remain. No physical result inferred from offline acceptance. |
| Running SD recovery host-test — host-only physical boot passed | One project implementer on GPT-6 Sol/medium, separate feature approver and verifier, coordinator for artifacts/media | Explicit separately named SD composition of existing recovery userspace, pinned kernel/loader, wired DHCP and public-key SSH; readonly root/volatile runtime, no automatic eMMC/MCU/boot-policy or printer activity | [Approved scope](../docs/features/sd-recovery-host-test/proposal.md); complete userspace VM must keep normal init, GTK and authenticated SSH running, test restart/unauthorized access and root/hash refusal; exact artifact and source inventories | SanDisk is installed and host is running from SD; [H13 physical result](../docs/hardware/host-sd-recovery-host-first-boot-20260929.md) confirms GTK/native HDMI/SSH and read-only spare intake. Keep USB/Ethernet connected and PSU off; no further media move requested. Touch and printer outputs remain pending. |
| Writerless full-eMMC reimage — in progress | Coordinator, with separate feature approval and delivery verification for substantive implementation | Select and compose one authenticated writer boot route (SD-resident initramfs or kexec from the running host), then integrate the H616 writer, exact v5 source and one-shot claim path without changing the default read-only diagnostic | Current read-only audit reconfirmed the compressed v5 input and streamed raw hash on Beelink. H616 adapter/descriptor admission and signed one-shot receipt pass synthetic QEMU. The pending boot proposal is paired with a [kexec route assessment](../docs/hardware/host-network-emmc-kexec-assessment-20260927.md): the v5 6.18 kernel has kexec disabled; no H616 kexec handoff is tested. Independent feature approval is required before behavioral implementation. | The installed spare has current CID/controller/GPT/environment and read-only p5 measurements. Existing trusted initramfs writer and p5 handoff passed offline review, but current SD-only U-Boot cannot select eMMC. Prepare a bounded remotely managed boot route and required stager tools, then independently review exact SD/eMMC artifacts and operations. No repeat SD move or USB writer request. Factory eMMC stored; all physical eMMC/boot-policy gates remain open. |
| Reconcile recovery export record — done | `project_implementer`, GPT-6 Sol / medium, then separate `feature_verifier`, GPT-6 Sol / high | `docs/features/host-recovery-export-composition/record.json` and only the evidence bookkeeping needed to bind the merged implementation | Six schema-valid offline checks and independent verdict passed; `feature_workflow.py validate` and `next` succeeded at `db33359`. | H04/H07 remain open for physical UI, media and recovery tests. |
| Finish approved inactive printer interface configuration — done | `project_implementer`, GPT-6 Sol / medium, then separate verifier | Approved `printer-interface-config` scope: inactive include and focused tests | Five pinned Klipper tests, coordinator private overlay file-output check, and independent pc-01–pc-08 verdict passed at `72000d3`; no physical claim. | H01/H02/H05/H06 for identification, boot, inputs and attended outputs. |
| Compose approved boot health — done | `project_implementer`, GPT-6 Sol / medium, separate `project_integration`, and independent verifier | Approved `host-boot-health-composition` coordinator, transaction admission, unit ordering and image enablement | All 12 offline checks passed independent review at `316be5f`: 59 focused tests and clean-source disposable QEMU A→B/A fallback. The harness selected roots and seeded a staged transaction; signed install and U-Boot attempt decrement remain untested. | H02/H07 for later board boot and fallback tests. |
| Prepare the next board artifact — research done | `project_researcher`, GPT-6 Luna / high | Read-only input receipt, capacity and resource audit | Identified the exact v6 SPL and retained reviewed host/data/recovery inputs on Beelink; the resulting candidate is recorded below. | H03 for writer access; H02/H04 for boot and UI. |
| Compose and write v3 board diagnostic candidate — physical A boot observed | Coordinator with independent Sol offline byte review | Reviewed v3 composition and spare writer transfer | Complete image readback matched SHA-256 `d6dde04282cf33908a7d3f051faefbb4b027c4348b41f2beb311320b778d5d56`; [physical A boot, HDMI/KVM login and temporary Wi-Fi](../docs/hardware/host-board-v3-first-boot.md) are recorded. | Corrected image needed for persistent Wi-Fi and diagnostic boot-health; one A boot attempt remained at last read. H04 touch, H07 and output gates remain open. |
| Complete approved disposable SD/NFS diagnostic — **done 2026-09-26** | Coordinator with independent artifact reviewer | Existing SD-to-Linux-to-read-only-NFS path plus bounded H10 probe correction | Reviewed supervised boot passed DHCP, read-only NFS root checks, and both read-only U-Boot environment CRC/layout checks on installed spare eMMC. Exact measurements and private capture hash are in [H10 record](../docs/hardware/host-sd-network-emmc-probe-20260926.md). | H10 is complete; no repeated network boot or media write planned. This does not validate boot policy or printer functions. |

Run at most one production implementer at a time. A verifier never reviews its
own implementation. Research can proceed while the implementation lease is held.
The coordinator alone assigns build and QEMU directories, operates the printer,
updates shared records, commits and pushes. No subclient asks the owner to repeat
a physical action. Add any physical need to the existing
[H01–H08 queue](../docs/hardware/coordinated-human-tasks.md), then combine ready
checks into one session. In particular, HDMI capture pending under H04 must not
hold the offline goals above.

The VM had about 36 GiB free at the board artifact audit on 2026-09-23.
Inventory old `build/` outputs before a factory-sized image or concurrent VM
run. Retain only accepted evidence; never remove another worker's fixtures.
The recovery record, inactive printer interface and boot-health composition
have passed independent offline review. None certifies physical board behavior.

`feature_workflow.py next` returns `null` while its single approved implementation
lease is active; this is not a reason to stop authorized coordination. The earlier sandbox deferral is historical; the trusted writer and p5 handoff
now have accepted offline evidence. The running-SD boot route has an [approved bounded proposal](../docs/features/sd-managed-boot-route/proposal.md).
Main-loader assembly/component preservation, focused capture refusal checks and
ARM64/QMP success-only reboot proof passed independent verification; the bounded
implementation is complete. A separately reviewed SD transfer passed exact
readback and full FAT/root/GPT preservation. The subsequent warm return probe
failed because the coordinator used a refused serial symlink and proceeded
without controller readiness. The host reached original recovery; current SSH,
environment and RTC retention are not established. See the
[measured transfer and failed probe](../docs/hardware/host-managed-sd-transfer-20260929.md).
Correct concrete UART admission, transient collector recreation and a separately
reviewed recovery action are next; do not retry blindly or arm a writer.
Exact full-loader inspection found missing CMD_HASH and CRC32_VERIFY, so the
proposal now preserves the proven SPL and adds only required main-loader
commands. The [hardware RTC correction and readback](../docs/hardware/host-rtc-preparation-20260929.md)
passed separate review/execution. Warm-reboot retention still needs checking
before a signed job. The delivery changes `finish` only for verified handoff
PASS to request reboot; QMP reset/shutdown proof passed. Existing bulk/QEMU
second-boot evidence remains distinct from pending automatic H616 return. Do not arm a
physical whole-device write while that unattended return gap remains. H10's single
reviewed retry passed on 2026-09-26. The spare eMMC appeared as
`/dev/mmcblk0`; both U-Boot environment copies passed CRC/layout checks and the
SD/NFS read-only checks passed. The probe shut down the host. See the H10 record;
no repeat boot is planned. H10 evidence does not validate A/B activation, normal
OS operation or printer functions.


Latest H12 observation, 2026-09-29: the [stopped-prompt correction](../docs/hardware/host-stopped-prompt-resume.md)
passed independent offline verification and its reviewed continuation verified
SD identity/script hash before sourcing. The SD SSH service responds and KVM
shows recovery at1024x600. A temporary coordinator supervisor failed a malformed
nonce, so early boot/fresh SSH-key fingerprint capture was missed; the capped
receive-only collector was restored manually. Initial key enrollment awaits a
single owner decision under H12; do not bypass console-fingerprint admission or
prepare actual jobs before fresh environment/RTC inspection. The
[nonwriting physical preflight proposal](../docs/features/h616-physical-preflight/proposal.md)
addresses the remaining urh-04 gap. Neither SD GUI nor offline code completes
urh-04/05 or the writerless goal. No additional media move is requested.


Continuation on 2026-09-30 completed the approved preflight repair and independent
offline verification. Its task is done; the dispatcher has no ready offline task.
The active thread goal remains the full project delivery: finish H12 under its
physical gates, establish reliable host operation and safe attended printing,
complete the host OS, then qualify actual stock hardware for release. The pause
on new feature development and hardware/publication authorization boundaries
remain in force.

A fresh Beelink network scan found an SSH responder at the reserved printer
address and the previously recorded wired MAC. It offered the same volatile
ED25519 fingerprint as the earlier refused enrollment. This is target correlation,
not independently authenticated printer access. The one H12 owner decision was
requested with that exact fingerprint; no key has been enrolled or printer SSH
login attempted. The earlier failed operation review and console-fingerprint
requirement remain preserved. Fresh Linux/RTC/raw-environment inventory, real
preflight jobs, staging, arming and commissioning wait for that identity gate.


H12 continuation, 2026-09-30: the owner authorized trusting any host key at the
reserved printer address. Strict isolated enrollment and authenticated SSH now
pass. [Fresh intake](../docs/hardware/host-h12-authenticated-intake-20260930.md)
confirms the installed spare CID, controller, GPT and both environment CRCs;
Linux/RTC clocks agree. Current eMMC is `/dev/mmcblk2`; A counters remain 3/2,
so physical preflight admission still needs reviewed exhaustion. The initial
identity gate is resolved; earlier failed enrollment evidence remains preserved.
Fresh p5 inspection passed an exact independently reviewed read-only namespace
operation; recovery script/free space match prior intake. Fixed mmcblk0 source
checks now block actual mmcblk2 staging; a bounded repair is submitted for
independent approval. No physical
preflight/reimage or printer-output result is claimed.

The node-binding proposal received `needs-research`: pinned Linux assigns MMC
host names and device minors separately, and the retained DT has no MMC aliases.
Resolve the shared signed path/dev_t across SD staging and RAM boot before
production edits. Existing scope approval permits bounded offline investigation;
physical H12 remains pending. This is an implementation/design dependency, not
a request for another media move or SSH enrollment decision.


The node-binding research hold is resolved by independent delegated approval of
an explicit signed v2 phase contract at `a44d6c8`. V1 exact numeric binding stays
unchanged. V2 keeps signed current staging numbers and requires the RAM writer
to pin/revalidate one boot-local mapping of the same signed physical eMMC.
One isolated implementation is active on `feature/h616-emmc-node-binding` with
`project_implementer`, GPT-6.1 Sol / medium, actual runtime confirmed. A native
thread-limit failure affected the optional planner launch; coordinator completed
the bounded source/design work, and a slot subsequently freed for the native
implementer. No CLI fallback ran. Fresh independent high delivery verification
and exact physical high-consequence reviews remain required before H12 staging.


H12 preparation also restored the [volatile staging tool closure](../docs/hardware/host-h12-runtime-tools-20260930.md)
after an exact independent high-consequence review with a recorded separate-session
fallback and verified Sol6.1/medium runtime. Version-only calls and all 29 installed
hashes/modes pass; no environment/media write or reboot. The node-binding worker
is still active; fresh independent delivery verification remains pending.


The node-binding worker is finished and the coordinator froze all nine assigned
files at `a1854e25e5164cb6a462c541b8d1bbe7043994ba` on its feature branch.
All final source and retained log hashes match the handoff. The submitted
offline evidence records 58 regressions plus six final live/policy checks, four
strict C checks and actual ARM64 v1/v2 resource comparisons; the broad suite
preceded final localized changes. A fresh native `feature_verifier_high`,
GPT-6.1 Sol / high, is independently checking the unchanged candidate and
approved constraints. Its actual runtime was observed. Integration waits for
that verdict; H12 physical preflight/reimage and all printer gates remain open.
No new job, key, boot-policy change or target write was performed.


Independent high delivery review failed candidate `a1854e2`: marker-time
whole-eMMC `O_RDONLY|O_EXCL` conflicts with the mounted p5 filesystem claim
in pinned Linux6.18.51. One source-grounded actual-C syscall reproduction
confirmed refusal before marker unlink for both v2 purposes and numbering
directions. The candidate, source/log hashes and original verdict are preserved.
The bounded repair remains within the approved nine-file scope: retain exact
snapshot/GPT/descriptor and durability checks, accommodate legitimate p5
ownership, and add an actual-main regression with kernel claim semantics.
Physical H12 remains pending; the complete project goal remains active.


The failed verdict is preserved in main `1cbdcbd` before resumption. A single
`project_implementer`, Sol6.1/medium with observed runtime, now owns the same
approved nine-file deliverable in isolated
`feature/h616-emmc-node-binding-marker-repair`, based on integration `cef44b0`
with the preserved candidate cherry-picked at `a582946`. No failed source was
integrated into main. New final-source evidence and a fresh independent high
verifier are required. Fresh read-only capacity also shows no single existing
volatile filesystem can hold the full artifact; exact workspace planning and
separate operation review remain prerequisites for physical staging.


The mounted-p5 repair is frozen at `9d98550` on its isolated branch and submitted
for fresh independent `feature_verifier_high` review, Sol6.1/high confirmed.
Sixty relevant tests pass; eight modeled actual-main before/after cases show the
original marker refusal and repaired passage to the existing expiry gate with
no claim/transfer. Current ARM64 builds and all handoff hashes pass coordinator
audit. Passing delivery and physical urh04/05 remain pending.
A separate high-consequence review rejected the first volatile workspace script
because its rollback could act after mount identity uncertainty; the original
script/verdict are preserved. Revised source removes automatic rollback and
stops for read-only reconciliation on any failure. A fresh separate high-tier
review is active with confirmed Sol6.1/high runtime and exact role contract.
No remount or other printer mutation has occurred under that preparation.


Fresh independent Sol6.1/high delivery verification passed every approved
node-binding check/constraint at `9d98550`; the accepted source was merged
locally at `3223541` and its task is done. The strict completion gate checked
the complete accepted source tree; coordinator goal-log updates were preserved
separately during that check and restored after completion. No source gate was
waived. The original failed candidate/verdict remain preserved. Sixty submitted
regressions and six independent final-source critical tests support offline
delivery; no physical RAM entry, p5 kernel mount, preflight return or whole-write
acceptance is claimed. Reviewed volatile workspace preparation can proceed under
its exact conditions; actual jobs/artifacts and physical operation gates remain.


The revised capacity-only operation passed its exact high-consequence review
and execution after delivery acceptance. Fresh independent postchecks confirm
`/tmp`256MiB limit with4096bytes used, same boot/root/mount flags and retained
`ro,norecovery` root. See [workspace record](../docs/hardware/host-h12-workspace-20260930.md).
No artifact was allocated/staged and no media, environment or boot action
occurred. Next: prepare fresh signed physical preflight inputs/artifacts and
capture, then obtain exact operation reviews under existing authorization.


Owner review instruction, 2026-09-30: use the separate
`high_consequence_reviewer` role for independent action reviews. Apply the named
high variant where material uncertainty warrants it, with actual model/effort
confirmed. Feature approval and independent delivery verification retain their
separate contracts under AGENTS.md.

Physical preflight preparation now has an actual signed v2 candidate built from
accepted source `9d98550`, using fresh distinct preflight-only signing keys and
job `a46735b7ce7ee9ab7e25a00e0312ae18` (expires 2026-09-30 23:47:37 UTC).
The persistent FIT is 48,901,632 bytes, SHA-256
`15ef085c90896e0fea3f146290611fefe5e43adf59d05dd43c0c54bc8d087235`;
actual shared artifact and signed-stage verification passed. Conservative static
working memory is 565,513,633 bytes against an assumed 1 GiB; this does not prove
physical RAM availability or relocation. Initial missing source-closure and disk
space failures remain preserved; the successful composition used a bounded local
tmpfs, now unmounted. Unique retained preparation allocation is 98,746,368 bytes.
Private receipts remain under ignored `local/feature-workflow/probes/`.

The existing bounded serial collector was restored after a separate
`high_consequence_reviewer_high` PASS WITH CONDITIONS and complete process/FD
visibility check. A fresh independent postcheck confirmed its exact source,
UART identity, exclusive receive-only descriptor and active capped unit.
The collector's inherited disconnect reopen behavior and termios changes remain
explicit; receive-only application access does not prove electrical inactivity.
Capture readiness must be checked again immediately before any boot.
No claim listener, target artifact staging, environment arming, activation,
printer boot or whole-device write occurred in this preparation. Exact physical
action authorization and immediate independent reviews remain prerequisites;
expired jobs must not be rearmed or reused. The full project goal remains active.

Detailed actual candidate, preserved preparation failures, resources and capture evidence are now recorded in [the H12 candidate record](../docs/hardware/host-h12-preflight-candidate-20260930.md). A separate exact volatile-transfer review found a bundle-path/library-wrapper preparation error before execution; corrected layout passes full shared verification with unmodified accepted source. Physical staging/arming/boot remain gated.


The corrected exact volatile transfer passed separate high-consequence review,
execution and independent read-only postchecks:27root-owned exact files,
98,738,504bytes, real on-printer signature/purpose/FIT verification, same read-only
SD root and169,627,648bytes free/tmp. No claim/p5/environment/marker/boot operation.
Fresh GPT/environment/clean-ext4 metadata checks are recorded. Independent high
review refused the initial prospective p5-stage script because writable mounting
preceded signed map admission; candidate/verdict preserved and never executed.
The corrected prospective stage performs full read-only admission first and
requires actual owner p5-write authority/setup provenance. Separate review and
current physical confirmation are pending. Physical urh04/05 and full goal remain open.


The revised prospective p5 file stage passed independent high review with
conditions; the earlier FAIL is preserved. [The complete urh-04 action plan](../docs/hardware/host-h12-urh04-operation-plan-20260930.md)
binds the current spare and actual preflight artifact, separates file stage,
environment preparation, marker activation, claim readiness and one boot/return,
and excludes urh05/fullimage writing. Owner approval for this single urh04 scope
and current setup confirmation have been requested under AGENTS hardware authority.
No authorization receipt exists yet and no p5/boot-policy operation occurred.
Bounded claim-service source preparation also completed without launching it.
Expired inputs require fresh preparation and review; no automatic rearm/retry.


Owner setup confirmation received2026-09-30 23:42UTC: PSU off, USB serial powers
the host, Ethernet connected, spare eMMC installed, factory module stored and no
new irreplaceable spare data. Exact reply/provenance is privately recorded.
This answers the physical-facts question only; the separately requested urh04
metadata/boot-policy/action authorization remains pending. No write/boot action.

### 2026-10-01 urh-04 authority and preparation checkpoint

Owner authorized the complete identified urh-04 sequence with setup unchanged
and standing authority for these changes; repeated permission is no longer
required within that scope. Immediate independent operation review persists.
See [authority decision](../docs/decisions/20260930-h12-urh04-standing-authorization.md)
and [fresh candidate evidence](../docs/hardware/host-h12-preflight-candidate-20260930.md).
A distinct replacement job expires at 00:47:49 UTC on 2026-10-01. Its actual
artifact and 27-file volatile host transfer/postcheck passed. Original expired
inputs/evidence remain preserved. The refreshed p5 packet was rejected before
execution for stale artifact constants; a corrected distinct packet is under
independent review. Physical urh-04 acceptance remains pending; the full delivery
goal and pause on optional new features remain unchanged.

### 2026-10-01 physical urh-04 failure and required repair

[Actual attempt](../docs/hardware/host-h12-urh04-first-boot-20261001.md): stage,
redundant arm and marker activation plus independent readbacks passed. One ordered
boot loaded the wrapper then original recovery; preflight FIT never entered and
claim remains unused. Pinned Sunxi source selects SD0 environment when SD booted,
so the valid armed spare environment does not supply the RAM selector guard.
No urh-04/05 acceptance; preserve failed inputs/evidence and stop boot actions.
Required [selector repair](../docs/features/h616-selector-environment-source/proposal.md)
has delegated offline approval with constraints; implementation and fresh independent delivery verification remain pending. Optional feature development remains
paused. No repeated owner permission within standing urh-04 scope is needed;
exact reviews, current setup/admission/expiry and independent verification remain.

### 2026-10-01 selector repair accepted offline

The required selector environment-source repair passed fresh independent
`feature_verifier_high` delivery review at `9995239` (GPT-6.1 Sol/high runtime
observed), and was merged locally. Its selector explicitly reads and checks
both intended eMMC user-area environments before marker/FIT admission; no loader
or persistent-write command was added. All 43 actual U-Boot cases and 62 focused
regressions passed, with independent complete-selector before/after reproduction
and representative artifact verification. See [accepted evidence](../docs/design/unattended-emmc-reimage-handoff.md)
and [completed record](../docs/features/h616-selector-environment-source/record.json).
H12 needs original-recovery observation/control, a separately reviewed SD return,
fresh target/RTC/raw-environment/p5 reconciliation, replacement expired inputs and
one newly reviewed physical attempt. GUI confirmation is pending; printer SSH
banner timed out and passive KVM snapshot is unavailable. Current media state
remains unmeasured after the failed attempt. Preserve all historical failures.

The failed physical FIT is preserved in a private, verified persistent Beelink
archive and a private volatile cache; its logical local path points to that
cache. Exact hash/readback/metadata receipts record restoration from the archive
if the cache is lost. This recovered 47 MiB on the coordinator root without deleting
the failed candidate bytes. No retired/expired job is reusable. Later physical
boot preparation must retain raw environment preimages/journals durably outside
target tmpfs before reboot. The complete project goal remains active.

### 2026-10-01 development storage and SD return

The owner authorized Beelink VG expansion when needed. A separately reviewed
32 GiB root LV/online ext4 growth completed with exact geometry, identity,
other-volume and error checks; see [actual storage evidence](../docs/development/beelink-storage-20261001.md).
Beelink now has about 31.7 GiB available; subsequent artifacts still require
bounded allocations. The coordinator root is a different host and was not
expanded.

Bounded planning found no unmodified recovery guard admission for the current
failed H12 state. Its used September 29 exception requires disabled markers;
the expired preflight marker may still exist, and current raw environments/RTC
remain unknown. The Recovery GUI Boot A/B controls change policy and do not
provide generic SD restart. A new attempt-specific guard amendment needs genuine
delegated scope review, source-bound independent delivery verification and
immediate high-tier action review; standing same-scope owner authority persists.
No old exception/receipt, fabricated fresh environment or claimed marker absence
may substitute for those gates. Continue only the required H12 correction.
