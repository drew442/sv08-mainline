# One SV08 commissioning session

Status: prepared offline; no physical check is marked passed here. This is the
single H01/H02/H04/H05/H06 session form linked by the
[human queue](coordinated-human-tasks.md). Use it for the identified printer with its actual selected definitions, including modifications. The filename retains its historical named
machine identity; an unmodified printer and exhaustive parameter combinations are not prerequisites for this session.
See the [current readiness and remaining gaps](../development/stock-printer-readiness.md).

The purpose is to reach an attended first print with the correct configuration,
without asking for repeated inspections, media moves or calibration transcription.
Keep one private session record and link it from every consuming H row. Do not put
serials, private configuration, calibration, keys or raw captures in this document.

## Current candidate bindings — 2026-11-17

Superseding preparation note: the new blank SC16G SD is identified read-only on
Beelink and remains unwritten. Passive actual-printer inventory exposed protected
eMMC boot regions missing from the reader. The correction at `7317a89` passes
source checks and its in-memory reader now succeeds on the actual eMMC, without
deployment or mutation. [Evidence](https://github.com/drew442/sv08-mainline/blob/bc1c71a39301630779892c505203ef4caa0d910b/docs/features/supported-release-candidate/boot-area-evidence.json).
The DD65 image/bundle bindings below remain historical, superseded and **not for
deployment**. Current independent-SD policy waits for a separate USB backup disk;
then refresh affected artifacts from cached pinned inputs. Source self-validation
is recorded at `bc1c71a`; no physical H acceptance is claimed. At that source checkpoint, ceilings were source 7,200 seconds/1 GiB and native
18,000 seconds/124 GiB; conservative charges were 3,900 seconds/880 MiB and
12,100 seconds/98 GiB, without deletion credits. The current continuation below
supersedes those preparation figures.


### Current native refresh at 7317a89

This continuation supersedes the DD65 artifact bindings below. It changes no
production source beyond the already validated protected-boot-area repair;
production paths at `7317a890b4cf812f2010c3fdf480edb0657e8d8b` match PR39 head
`5cd49102f83b512f210c868df925934c44309a11`. No image was installed or printer
service/output operated. The separate USB backup drive remains unidentified.

| Artifact | Bytes | SHA256 |
| --- | ---: | --- |
| Normal revision 4 disk | 7818182656 | `f8eaeac00354895b4bfdab9274cd68ddb1a35d65c683748610220752d5efc61a` |
| Internal recovery | 536870912 | `ea326e623141fd7cee2a8e58f17fbd4619eb12fd1df6192838f42b41e9f2500a` |
| Signed revision 5 OTA | 545114542 | `096369b715fd26a91b019f6519b40280ec4385d73ea2ab9c90acbe1f90052883` |

The refreshed normal root passed clean-owner/identity/disabled-physical-service
checks and preserved its DD65 source parent before retirement. Fresh recovery
assembly used the cached 285 pinned packages and unchanged owner supplement;
board derivations preserved the base. Internal recovery and SD root derivation
pass. All six normal filesystems, partition byte readbacks, SPL and both boot
environment copies pass. The default **selected-software** gate checked matching
anonymous public source in all three actual software roots, both normal roots'
application bindings and selected notices. This is construction/source evidence,
not physical boot, legal completeness, whole-image reproducibility or a printing
release. The gate retains those explicit limits.

The revision 5 bundle's signer is trusted by the qualification CA. Both payload
streams match their signed image hashes and its embedded release/source/MCU
recommendation matches. Inspection left its source root unchanged, with bytecode
writes explicitly disabled. Actual verity-device installation, production health
and the revision 4→5 trial/reboot journey remain unproven. This bundle does not
authorise updating the current legacy installation directly. Normal-image
filesystem IDs were probed read-only at their verified GPT extents for the later
post-install recovery policy; they are artifact facts, not a claim about the
currently installed target.

<details>
<summary>Source-bound commands, receipts and carried allowance</summary>

| Phase (existing builders; exact invocation in private receipt) | Exit | Elapsed seconds | Log SHA256 |
| --- | ---: | ---: | --- |
| recovery / assemble | 0 | 210.102 | `e57e446aac57fb3bd0d11135a6aab34cb422136256334bf78c6af33a1354ca7f` |
| recovery / derive-emmc | 0 | 35.254 | `b3b47c2e059ce6bca5723da62b9bf9872fd4a0ddea54be64c4474efa472c3224` |
| recovery / build-emmc | 0 | 221.695 | `3694be4f58b6032263e9805f3fd10fe8f7bf13a3aa716afd84405304a40ede02` |
| recovery / derive-sd | 0 | 36.838 | `a977716e7cb5a03569bff4a7aa6b0f777882951fba1611a0d43212efe2378567` |
| normal / compose | 0 | 117.271 | `ae0da34795b9df9c99ee38384a4f39da30bb28d4d9a3bc663b4bbc8c41f905d8` |
| normal / readback | 0 | 31.856 | `c7a9e8ccd6ba5dcc3f6545c11744164b9dc7c0432e94ccd960c9d0a7c26b6acb` |
| normal / selected-software | 0 | 215.863 | `ab85d53eb31a77603ff6a3f757fde6ae434924cdcdb7061635cc96199cbe24a3` |
| update / prepare-update-root-7317a89.py | 0 | 42.752 | `bb78ae359691cfc084d2938ff4397760dc8e61dfe7cd9e785f775f1a90acaffa` |
| update / build-update-payloads-7317a89.py | 0 | 20.561 | `ffb5b0b7dfad1b89c240b40013c4435db09805f62e30fe809b9a564b3a68dbab` |
| update / sign-update-7317a89.py | 0 | 165.826 | `67a4c64b86a99508e62ff2acae4d6ea7a0cf3ecc8a56587037ad654a6cc47e8d` |
| update / readback-update-7317a89.py | 0 | 6.825 | `5b4c71edf5f044923e6cf367e7071138c017fc39b7a51729b8e0eed3770bbf22` |

Coordinator additionally refreshed/staged/finalized the normal cached root in
44.725 seconds. Existing product commands are `recovery_image.py`
assemble/derive/build, `assemble_supported_candidate.py`, the default
`prepare_release.py` selected-software gate, RAUC bundle/trusted inspection and
read-only stream/partition comparisons. No OS bootstrap or permanent host change.
The small scripts and complete phase commands/logs remain in the assigned private
release workspace and Codex `~/.sv08-release-20261117/`; failed default-SFTP intake
was retained and corrected to the existing legacy SCP transport before building.

Exact aggregate receipt: `/run/a733-guests/sv08-release-20261117/logs/artifact-refresh-7317a89.json`,
SHA256 `fc2167f07f144f5d8ea92405be35b6347295f04c36ec379eb7a8e27c90165973`; its copy is
`~/.sv08-release-20261117/boot-area-fix/artifact-refresh-7317a89.json`. It pins the
normal finalization/parent/owner, recovery assembly/build, composition, signed
bundle/readback and release report/manifest receipts. Filesystem observations are
in adjacent `normal-7317a89-filesystems.json`. Full image and bundle stay private
in `workspace/candidate/build/supported-emmc-7317a89/` and `update5-7317a89/out/`.

Current allocation supersedes earlier preparation figures only: source ceiling
7,200 process-seconds/1 GiB; conservative source charge 4,000 seconds/896 MiB.
Native ceiling remains 18,000 process-seconds, with a bounded additional 4 GiB
output continuation to **128 GiB** for mandatory refresh/temporary output and the
pending SD artifact. Conservative native charge is now **14,500 seconds/126 GiB**.
The existing 32 GiB workspace is included, previous attempts carry forward and
deletion earns no credit. The last direct size observation accounts for
25,370,057,849 new logical bytes, including retired current components; the
conservative charge also covers temporary generation. Native
`logs/native-refresh-allowance.json` and `native-refresh-output-continuation.json`
retain the unchanged scope/authority and earlier ceilings. These are continuations
of the same release goal, not new physical-operation permission.

After byte checks, redundant current partition/OTA components, obsolete DD65 roots
and superseded OTA bundles were retired. Their JSON receipts/hashes and the two
round-trip-verified prototype archives remain. Current full disk, signed bundle,
current normal/update/recovery roots, package/app/kernel/license caches and native
fixture remain. Workspace free space after retirement: **14,026,801,152 bytes**.
No SD/eMMC write, target service restart, MCU operation or public binary release
occurred. Source-checkpoint hashes/records remain at their original revisions.

</details>

Next action: identify the separate USB drive and its host/location, then bind the
export/restore inventories to the actual SD/backup/eMMC, finish the SD build and
script-bound loader, and obtain the existing exact-operation assessment/authority.
Preserve the tested rescue SD. All physical commissioning/printing/peripheral and
candidate-specific update/recovery acceptance remains in the existing H phases.

### Preserved pre-refresh bindings

Preparation only; no physical launch/write is authorised. These historical bindings belong to
[PR39](https://github.com/drew442/sv08-mainline/pull/39), whose source checks and
four hosted workflows passed. The source feature remains self-validated, awaiting
integration; the full release goal remains active. Keep the source worktree and
native build checkout frozen rather than rebuilding for this coordinator record.

<details>
<summary>Coordinator bindings, offline checks and cumulative allowance</summary>

| Item | Prepared binding / remaining condition |
| --- | --- |
| Fitted hardware | Owner confirmed saved revision 13: Funssor/CN3D heated bed, factory mainboard/toolhead/hotend, filament sensor and exhaust fan. This declaration does not close wiring, input association, MCU identity or thermal checks. |
| Production source | `dd65c33f51d535c1f9f3ff7a15482fc5bb4c008d`; pinned host Klipper `f0892d82b0f1c1228454f09eb508eddde2250f4b`. Source/evidence candidate `adb8be0d061bd4eac3fc8623ea86a600e4248f13`; PR head `9e874f075e4a2332aa97aee52c4301f26fbfb138`. Later queue/packet records do not change the built production inputs. |
| Initial normal disk | `0.1.0-supported-candidate.1`, revision 4, 7,818,182,656 bytes; SHA256 `49697c8eaf21f9b8d83784d3e3525aed3f2bdec38f1a707cdb83647e1362ec63`. Six filesystems/partition readbacks, loader and both environment copies checked; actual normal boot remains unqualified. |
| Update qualification payload | `0.1.0-supported-candidate.2`, revision 5, 545,122,734 bytes; SHA256 `dba542811057ff68df1cf899aa29b4178ee06a36a58ef7abfa2d995d42c0d019`. Signer, payload hashes and embedded release identity checked. This is the later revision 4→5 trial payload, not authority or proven eligibility to update the current legacy installation. |
| Recovery / media | Current internal recovery and independent-SD source base are built. **No current independent-SD artifact/admission profile is ready:** spare SD and backup drive identities/location are still required. Preserve the tested rescue SD. Initial migration is planned through independent-SD installation/private-data restore/owner enrollment, subject to exact-operation review. |
| Saved configuration | Private saved-hardware capture SHA256 `1e4ddf2ef152bc1f6c4b6012f679d4bb613d3ba61b7cdc4a71ee7c6626831cc6`; generated preview JSON `21161db468d2d029ea8604f93d99788359525bd440a4bfa0821962c04feb7115`. The preview is complete with printing disabled; it is not an applied/active publication receipt. Regenerate/review after restore against the installed release and record that receipt before normal commissioning permission. |
| Input-only phase | Private 1,203-byte candidate SHA256 `af010cc9e3c8a3e992dfe6f28300ea0101b655f1d25dd8d8e6beda57bab9a154`, derived from that captured selection. It contains only the two MCU declarations, inert `kinematics: none`, exact selected thermistor curves/conversion settings, temperature inputs and empty probe/filament button handlers. No heaters, motors, fans, includes, actuation macros or nonempty event commands. |
| Stop / phase activation | Still requires exact live launch/socket ownership, lifetime/stop procedure, target/boot-state binding, independent operation assessment and owner authority. The input-only artifact is not a substitute managed Full publication and must not be fed to the normal commissioning service or used to remove its guards. No generic unmask/start or readiness-marker creation is approved. |

The input-only candidate reached **ready** using the actual pinned production
validator in native ARM64/KVM, with observed 8-second CPU/256 MiB address-space
limits and unchanged 10-second readiness deadline. `query-kvm` reported enabled
and present; guest boot ID `760a5a3e-fe3f-437d-b25e-91340834f431` exited 0 and stopped.
The source helper hash is `77fe141910f601962a67efc5d225a5115d49887e6923e73d3b35aca3193b4c3e`;
the returned dictionary hash is `86665c7ba90587f09347af0001faf3681cc35819141b5c37c1f646e49a15125b`.
This establishes parser/software readiness only, using file-output simulated MCUs;
it does not connect to actual MCUs, establish firmware compatibility, prove
physical sensor associations/accuracy or approve a physical launch. A first local
derivation guard stopped before output because it assumed a generic sensor name;
the corrected candidate preserves the exact two named thermistor definitions
already selected by the owner. No default conversion was substituted.

Private assigned evidence: `~/.sv08-release-20261117/commissioning/` on Codex
(`inputs.cfg`, provenance, original failed derivation, allowance, native summary,
filtered runtime limits and `packet-evidence.json`). Native raw diagnostics remain
under `/run/a733-guests/sv08-release-20261117/logs/native-input-stage/` on the ARM
runner. Native summary SHA256 `5d236ae4e62eabb13274544ef5179acca40c87efe39caded7b827006de8bcd56`;
filtered runtime receipt SHA256 `f3b4f73d8beb4ac5f10a617b3951c0e4fa6310c171d5f5df81a060c7eb3de326`. Keep private serials/configuration
out of this public form. [Built artifact receipts](https://github.com/drew442/sv08-mainline/blob/adb8be0d061bd4eac3fc8623ea86a600e4248f13/docs/features/supported-release-candidate/candidate-build-evidence.json)
retain the construction/source/notice evidence and its precise limits.

At `2026-11-17T11:53:41+00:00`, a read-only metadata snapshot of the identified installed eMMC data
partition matched the build profile's expected medium identity. It reported
1,929,543,680 available bytes, 156,223 available inodes and 504,561,664 allocated
bytes under `/data/sv08`; no private file contents were read by that snapshot and
no service/configuration/output change was requested. Receipt SHA256
`9b862c4a3e77f6ad9034194eee86f60f7224ab5bf167bd7482274781f71c224f`. The current guard calculation admits the actual
545,122,734-byte bundle plus an assumed maximum 256 MiB state copy: required
1,625,419,776 bytes/8,256 inodes. A hypothetical 1 GiB bundle plus that copy correctly
refuses. These are calculations against the older installed filesystem snapshot,
not an allocation or new-candidate/restore measurement; recheck immediately before
any live operation. Do not delete user data to turn a refusal into a pass.

This preparation retained prior consumption/attempts and used the existing source
and native allowances: conservative cumulative upper bounds are 3,620 process-seconds/
708 MiB source and 11,360 seconds/(93 GiB+64 MiB) native, within 7,200 seconds/1 GiB and
14,400 seconds/96 GiB respectively. The logical 32 GiB workspace remains charged, the
existing native fixture was reused, and no image was rebuilt or deletion credit
claimed. Media identification and physical gates remain unmet.


</details>

## Before scheduling the attended work

The coordinator prepares the exact candidate/configuration manifest, firmware/source
matches, last applicable evidence, logging and a known stop/restore route. The owner
confirms the actual target and available independent recovery medium. Reuse earlier
measurements only when the same parts, wiring and configuration still match; do not
ask the owner to recreate source inventories. Never ask for a media move before
reviewed bytes, target boundaries and the writing procedure are ready.

The session packet must identify how Klipper will be launched for each approved
phase, its configuration hash, service/socket ownership, output limits and stop
procedure. Configuration publication deliberately leaves Klipper stopped. Current
diagnostic images retain production masks and do not grant normal OS-health
readiness. Their physical commissioning launch must receive a separate exact-target
operation assessment and owner authorization. **No generic unmask/start command or
fabricated health marker is part of this form.** If no supported/reviewed activation
route is ready, stop at that explicit integration dependency before requesting
output tests; do not disguise it as a failed sensor or ask the owner to debug Linux.

For an unqualified factory host, prepare target-specific boot/MCU and independent
recovery checks before any installation. The existing complete diagnostic image is
not a generic stock printing installer. This session does not authorize flashing,
power cycling, motion or heating merely because its instructions exist.

## One header, one result log

Record these once in the assigned private session directory:

- Date/operator, physical target, selected profile and fitted parts; mark stock or modified.
- Image/source/slot/boot and both MCU revision/identity bindings; reuse exact known evidence where still applicable.
- Saved hardware revision and final Full configuration/manifest hash/publication receipt; record each earlier input-only, setup or calibration candidate separately.
- Independent reference instrument, approved phase limits, stop control, recovery route and capture paths.
- Exact reviewed activation procedure, operation authorization and coordinator contact.

Use a single row per phase: `time | configuration hash / launch-stop review binding | pass/fail/inconclusive | observation/evidence | next action`.
A failed/inconclusive prerequisite stops dependent phases. Leave later rows unpassed.
A safe pause between phases is allowed; changed hardware/configuration invalidates
its dependent evidence, not unrelated completed checks.

## The session, in order

| Phase | Owner/coordinator action and observable pass condition | H dependency |
| --- | --- | --- |
| 1. Identify the fitted machine | With power isolated, including USB/serial back-power, confirm board/connector/part evidence and wiring changes without unnecessary disassembly. Confirm factory bed/hotend/sensors or choose definitions for the actual replacements. Do not select a factory sensor merely because a hotend name matches. | H01 |
| 2. Establish the host and stopped setup | Arm capture, then use only the reviewed boot/installation procedure. Confirm intended slot, persistent configuration/identity, correct MCU revision/serial association, Mainsail/Moonraker access and no unintended outputs. Confirm the independent recovery/stop route. No trial, update or service race may be active. | H02/H04 |
| 3. Check inputs before outputs | Use the reviewed input-only configuration. Observe each actual probe/filament/endstop released–operated–released transition and physical association. Compare plausible stable ambient readings with the independent reference. Take pins, names and configured conversion settings from this session's generated manifest, not old hardcoded pin tables. | H05 |
| 4. Verify stop, fans and motors | After phase 3 and exact action review, enable only the approved phase. Verify the stop path and each physically identified fan; check one bounded motor action/direction at a time with clear travel. Wrong direction, unexpected motion or inability to stop is a failure. | H06 |
| 5. Establish homing/probing | Verify the configured probe and sensorless/DIAG dependencies before the separately reviewed bounded homing sequence. Do not issue ordinary `G28`, gantry levelling or mesh before these dependencies pass. Keep pressure GPIO observations separate from proprietary automatic calibration. | H06 |
| 6. Validate heating and extrusion | With identified sensor/heater parts, reviewed limits and an independent reference, observe each approved controlled heat response and shutdown. Stop on implausible readings, overshoot or protection failure. Perform reviewed PID/extrusion checks only after thermal behavior is accepted; persist any measured gains with native `SAVE_CONFIG` as described below, never by borrowing factory measured gains. Maximum configuration limits are not initial test targets. | H06 |
| 7. Record manual probe calibration | Establish the reviewed gantry/bed plane at the intended thermal state, then run the supported manual probe procedure and native `SAVE_CONFIG`. Wait for restart and automatic reconciliation, then confirm the persisted value in Cockpit. Exercise the actual print-start levelling and Z-rehoming sequence and verify the nozzle-to-bed reference before first extrusion. If levelling changes that reference, recalibrate after levelling and rebuild the mesh before printing. | H06 |
| 8. First layer and print controls | With all preceding gates passed, use a known bounded test file and matching slicer start/end controls. Attend the first layer; separately verify pause, resume, cancel and shutdown. Record observed behavior, not just a successfully uploaded file. | H06 |
| 9. Finish cleanly | Stop the job and outputs, preserve logs/calibration/configuration, confirm the intended persistent/stopped service state and record which capabilities are accepted. Accept the actual configured printer and record its selected definitions; no exhaustive combination testing is required. | H02/H06 closure |

Stop immediately for smoke, unexpected heat/motion, wrong input association,
communication loss or any inability to stop. Use the reviewed independent stop
control. Do not continue by weakening heater protections, inventing offsets,
changing limits or disabling a guard. Send one exact failed phase/evidence reference
to the coordinator and keep the setup available for diagnosis where safe.

Fine sensor-curve fitting remains deferred. The earlier chamber BLE measurement is
a location-specific ambient reference, not proof of heater temperature accuracy or
a reason to fit a conversion curve. Forced update fallback and destructive recovery
are separate controlled maintenance qualifications, not extra first-print tasks.

## Native Klipper calibration and persistence

The generated setup uses the sourced starting offset of zero until a measured
probe offset is recorded. A persisted measured zero is valid; a starting zero is
not evidence that calibration has been performed. Full printing starts guarded
and the observer acknowledges only a matching loaded configuration and accepted
calibration. Explicit Setup mode remains blocked.

Under the reviewed physical procedure, use normal Klipper calibration tools:

1. Establish the intended warmed gantry/bed plane, then run the supported
   `PROBE_CALIBRATE` / `TESTZ` / `ACCEPT` interaction.
2. Issue normal `SAVE_CONFIG`. Klipper persists the result and restarts. There is
   no required transcription into Cockpit or separate hardware publication for
   this calibration-only save.
3. Wait for Klipper to become ready and Cockpit's calibration synchronization
   message to report acceptance. Confirm the persisted value survives reload in
   **Printer Hardware → Inspect changes → Configuration output, calibration and
   expert actions → Existing component calibration**. Pending/conflicting values
   are not a successful active calibration.
4. Before first extrusion, exercise the actual print-start levelling, Z-rehoming
   and mesh sequence in the reviewed thermal state, then verify the nozzle-to-bed
   reference. Record the active configuration hash for this phase.

The [pinned Klipper guidance](https://github.com/Klipper3d/klipper/blob/f0892d82b0f1c1228454f09eb508eddde2250f4b/docs/Probe_Calibrate.md#calibrating-probe-z-offset)
requires recalibration after changes to the motion system, hotend position or
probe location. With XY probe offsets, a changed bed tilt can also invalidate the
measurement and dependent mesh. QGL can change that relationship; it is not proof
of an offset's validity. The normal generated QGL → Z-rehome → mesh sequence is
retained, consistent with the [published Voron start example](https://docs.vorondesign.com/community/howto/EricZimmerman/SlicerAndPrintStart.html).
Whether this configured machine reproduces its calibrated reference is an attended
check. If it does not, stop, recalibrate after levelling and rebuild the mesh.

Supported native results are mirrored automatically against the applied hardware.
Unrelated root edits, immutable include drift and incompatible records are refused;
normal later hardware publication/restoration still requires stopped services.
Manual calibration fields remain optional overrides. If used, save, regenerate,
review and apply stopped; they do not authorize writing generated files by hand.
Replacement of affected hardware clears dependent measurements. The automatic
observer validates persisted data and loaded configuration, not physical accuracy.

## Optional heater PID calibration

Hardware selection does not require PID calibration. Supported Full configurations
can retain explicitly selected watermark control while PID is deferred. Do not
invent or borrow measured gains.

After thermal identity, limits and response have passed their reviewed checks,
use Klipper's normal PID calibration for the identified heater and agreed target,
then `SAVE_CONFIG`. The native result includes PID control and gains; automatic
reconciliation records them without manually copying numbers or changing an
advanced control selector. Wait for accepted synchronization and verify the active
control/gains and thermal response before printing.

If PID remains deferred, record the accepted watermark behavior and limits. Fine
sensor-curve fitting remains deferred; changing control mode does not identify an
unknown sensor. Keep this phase's result/configuration binding in the same session
record instead of repeating unaffected input checks.

## Handoff

The coordinator links this single result into H01/H02/H04/H05/H06, recording exact
passed phases and exclusions. Unresolved fitted parts, activation, calibration or
print behavior remain named dependencies with the next useful action. No H row is
closed from an empty form, a parser pass, an export or a publication receipt.


## Recovery media ready, 2026-11-19

Production source `c69618ea9ac060b8714d68c1751fd36bb653988c`; delivery wrapper
`766b0257c55be3675493e7cc38bb05bd2b73af66` differs only in the wrapper/fixture
among shipped source. Native explicit pin verifies source blobs, upstream gitlinks
and integration inputs. DTB is read from sealed compressed usr. Original production
images and receipts remain unchanged; failed first lookup/log remains preserved.

| Artifact | Bytes | SHA256 | Measured preparation |
| --- | ---: | --- | --- |
| Normal disk | 7,818,182,656 | `7cbf00915e670e999d86bdfa985889c564a5d982562211bade4831e4ef7968b9` | Six partition/SPL/environment readbacks and selected-software source/notice gate; Beelink NFS staging/readback |
| Internal recovery | 536,870,912 | `c95163aaf5f74feb2b4a3ce8e4af5ba68c96f77b20535f2482f2d0a63ec590fc` | Actual current-source construction/fsck/readback |
| Revision5 OTA | 545,130,926 | `42b5caa8b421e2a812d1300238656b75fb8af4f317cfdd9b03b04c67c75ecab5` | Trusted signature, streamed payload and embedded release checks; no installation/verity-install claim |
| Export SD | 738,197,504 | `b1d992da6b77d1c20abff03017e4ba28803e2fa53c595da08029688a2afe83e3` | GPT, SPL, all FAT payloads, root partition and both kernel manifest bindings; Beelink private staging/readback |

The exact blank SD is15,931,539,456bytes, CID-file SHA256
`599fd94c2cf7c3604aad8f72f28cbc9b48edf0e88016be0658a8b61f603a1ce3`.
USB is31,014,191,104bytes with its original FAT32 partition. Both remain
unmounted/unwritten; stable raw identifiers/policy stay in private preparation
records. SD removable=true is inferred from the actual pinned DTB, not a physical
observation; recovery must match the complete live policy before export.

Reviewed writer SHA256
`ab4ab55f2e3ad0d0e8f9e2b12786371c82e81c4ddd4e6d11e0b6fe0115685063`.
Independent assessment passes with conditions for only this card-prefix write and
conditional initial recovery boot/export. Owner authority is pending. Recheck all
target/usage/image facts immediately, run with assertions enabled and require full
direct readback; no tail write, GPT repair or resize. Keep the tested rescue SD.
Confirm actual idle/outputs/source/recovery state, perform orderly old-system
shutdown and observe completion before removing PSU and USB back-power for moves.
No heater, motion, MCU or eMMC installation action is covered. Stop on mismatch,
unexpected output, boot loop or admission failure; no repeated attempt by default.

Native actual-image helper prerequisite passed with synthetic legacy data; actual
backup conversion against the final image is still mandatory. Export and restore
retain separate immutable policies. Preserve/verify the original actual archive
outside the installation boundary before proceeding; an interrupted helper or tar
without its matching completed receipt is unusable. Calibration/identity persist;
inherited start permission is quarantined and fresh commissioning remains required.

Resources retain all prior consumption: source7,200seconds/1.25GiB ceiling with
5,200seconds/1,220MiB conservative charge; native18,000seconds/168GiB ceiling with
17,000seconds/166GiB conservative charge. Includes logical32GiB workspace, retained
failed attempts, compressed731 prototype, local loader and Beelink transfers; no
deletion credits. Original package/app/kernel/license inputs are retained.

These are construction/offline/native-source receipts, not installed hardware,
printing or release qualification. No new SD/USB/eMMC writes, printer service/boot
changes, outputs, deployment or public binary release occurred.


## SD card written, 2026-11-19

This post-source physical record supersedes earlier unwritten-card statements.
Validated source snapshots and historical evidence remain unchanged. The owner
explicitly authorised writing the new blank SD in Beelink and confirmed that the
tested rescue SD is available; authority covers this card write. The current
card CID digest differs from the historically tested rescue-card digest.

Fresh08:09:47Z preflight confirmed the exact SD capacity15,931,539,456bytes, CID-file
SHA256 `599fd94c2cf7c3604aad8f72f28cbc9b48edf0e88016be0658a8b61f603a1ce3`,
SD type, unmounted whole disk/child and unchanged reviewed writer/image. The
assertions-enabled reviewed writer independently rechecked source hash, target
CID/capacity, all child mounts/holders/users/swaps and held exclusive block FD.
One write completed08:11:24Z: exactly738,197,504bytes, offsetzero; fsync and
full direct-I/O prefix readback both match
`b1d992da6b77d1c20abff03017e4ba28803e2fa53c595da08029688a2afe83e3`.
No tail write, resize or GPT repair occurred. USB and printer eMMC were not targets.

08:13:10Z post-check confirms both expected partitions: FAT128MiB at32768sectors,
UUID `5356-3038`; ext4512MiB at294912sectors, UUID
`27ea34a6-fb05-4814-aaee-251071577ae1`. Both PARTUUIDs match the image recipe.
Whole/children are unmounted, with no holders or open users. USB is still its
original unmounted FAT32 partition. The first read-only collector assumed the
whole-disk `slaves` sysfs directory existed on partitions; corrected invocation
permits absence only for verified partitions while requiring the whole-disk
directory and retaining every usage/layout/identity check. No write was repeated.

Private exact write-receipt SHA256 `5150ebc7f55aba73be712a150aaa1037027af2d119a997579080e8df05a7aa21`;
post-check receipt SHA256 `38a642a9ab0d70d2f4ff0f9a8d78b373638b84aecfe887b11ff5de59ca921e34`.
Raw card identifiers, full receipts, failed collector diagnosis and unchanged
writer remain in the assigned private preparation directory and Beelink's
`/var/tmp/sv08-release-20261119/`. No credentials or owner backup were inspected.

Primary exact-write suballowance300process-seconds/1GiB was drawn from the existing
continuation, with conservative charge150seconds/740MiB. Cumulative native charge
is now17,150seconds/167GiB under18,000seconds/168GiB; previous source charge and
all attempts remain carried, without deletion credits. No printer boot or printing
acceptance is inferred from writing the SD.

Next: an attended first recovery boot/export under its reviewed conditions.
Establish current idle/output/source state, authorise orderly old-system shutdown,
observe completion and fully remove PSU/USB back-power before moving this SD and
USB into the printer. Keep the tested rescue SD unchanged. Current owner authority
does not cover shutdown/boot/export or an eMMC image write. Actual complete media
inventory must match the immutable export policy; any mismatch stops admission.
After successful export, independently preserve/verify the original archive before
conversion or installation. No physical printer/service, firmware, heater or
motion changes have been made.


## First recovery session, 2026-11-20

Owner confirms: “nothing is printing, the heaters are off, you may proceed as needed”
in response to the requested orderly shutdown/first recovery boot/export phase.
The previously tested rescue SD remains available. These facts and the completed
new-card write satisfy the corresponding conditions of the existing exact-operation
assessment; image, policy, loader, protected media and stop conditions are unchanged.

Fresh preflight observed original stable immutableB/`0.1.0-physical-update.2`,
release-revision2, no trial/pending image transaction, terminal historical update
phasefailed, automatic updatesdisabled, no package/firmware processes and inactive
Klipper. The first disposable collector refused all systemd jobs, including the
normal web-auth/Mainsail/graphical startup chain. The diagnosed correction permits
only those observed non-installation start jobs; all update/package/firmware and
unknown-job protections remain. No product code or service configuration changed.

An ordinary `systemctl poweroff` was issued once at04:58:15UTC. SSH closed before
the requester could acknowledge completion (exit255); positive independent serial
observations confirm all filesystems unmounted, all swaps deactivated, final sync
and `reboot: Power down`. This is not an inferred halt from SSH loss.
Immutable console prefix18,086bytes has SHA256
`c203a7d9ad20258d7d090f418bf16d3ebf710e0366b301d6929553d4d55b0d7a`.
Private shutdown confirmation, request transcript and collector-attempt diagnosis
are retained under `.sv08-release-20261117/first-export-20261120/`. No raw UART
transcript or private data is published.

The existing receive-only collector remains source SHA256
`5c4e6cd4f1e8039949c83654c1265ffad51c269230268ca445e4491d7bf2b0ed`:1152008N1,
no transmit and noHUPCL. Beelink transient unit
`sv08-export-capture-20261120.service`, mainPID107941, started04:56:30UTC;
RuntimeMaxSec900 and32MiB per-file limit bound its two log files to64MiB. This
is a live handle, not evidence of a new boot. Owner was given power-isolated
new-SD/USB transfer instructions, using the host slot used by the rescue SD;
stand the printer upright, keep Ethernet/PSUoff and reconnect USB serial only
after media is fitted. New boot/GUI/media admission/export are still unproven.

Before this phase, the coordinator allocated a bounded1,800seconds/4GiB continuation
for one capped capture, actual500MiB-class export and independently verified copies.
Cumulative native ceiling is19,800seconds/172GiB; previous17,150seconds/167GiB,
all attempts and logical32GiB workspace remain carried without deletion credit.
Source allowance is unchanged. Reuse current artifacts; no new OS image.

Stop on unexpected outputs, repeated boot, policy/auth/inventory/mount errors.
Actual complete media inventory, including expected SD-removable status, must match
the immutable policy. Preserve and independently verify the completed original
archive before target-bound preparation or any later installation. The allocation
and authority here do not claim commissioning, printing or release qualification.


## First SD boot and refusal, 2026-11-20

This supersedes the preceding request for manual power/screen handling. The owner
confirmed “New card fitted; hands clear”, distinguishing it from the old tested
rescue card. Coordinator controls are the existing Beelink `sv08-power` utility
(as its configured user), identified NC-wired HW-667 USB relay, and GLKVM. The
PSU stayed OFF throughout; only host USB power was restored once at 05:19:50 UTC.
The relay's off/restore operation received a specific independent assessment.

The card image `b1d992da6b77d1c20abff03017e4ba28803e2fa53c595da08029688a2afe83e3`
booted kernel `6.18.51-sv08-candidate1`. Its expected envelope/provider bindings
verified and the serial marker was `SV08_RECOVERY_VERIFIED: independent envelope
and compressed userspace`. GLKVM showed the actual recovery page after a modifier
key woke its blanked display. These observations establish this SD boot, not
successful export, normal installation or printing qualification.

`sv08-recovery-prepare.service` stopped at its full reviewed-inventory comparison:
“Observed media topology differs from immutable reviewed policy”. No source or
USB destination mount had occurred. The structured boot report shows only the SD
root and compressed `/usr` as persistent mounts, both read-only; other mounts are
kernel APIs/tmpfs. The particular mismatch is **unobserved**. The inferred SD
removable flag is a hypothesis, not a measured correction. Do not change the
policy or mount media manually to bypass admission.

GLKVM VT2 reached getty, but serial logs establish `can't exec /bin/login: No such
file or directory`. The documented convenience account is therefore unusable
through this path. A source read of the exact cached assembly confirms that the
pinned BusyBox has its login applet; a complete supported console repair and
actual login check remain required. No credential file was inspected.

A fresh independent assessment approved one guarded HID Power-key request. Actual
logind accepted it; at 05:37:00 UTC serial evidence confirmed all filesystems unmounted,
swaps deactivated and `reboot: Power down`. The 10,023-byte confirmation prefix has
SHA256 `db9e408cb8186ecc60d065fd8e265b48b969e29fdc69ba9c4b86b9e70096716a`.
Only then was USB power held off. Its immediate zero-delay enumeration assertion
failed; four later samples over 1.5 seconds observed bridge absent and relay present.
No off retry, automatic restoration or additional boot occurred. PSU remained OFF.

GLKVM capture used its installed producer/settings in a temporary process, with
cleanup on exit, without changing configuration/authentication or installing tools.
Retain failed legacy-socket, unsupported-JPEG, absent-producer, unavailable-SFTP,
missing-hook and stale-socket evidence. UART capture units `sv08-export-capture-
20261120.service` and `…20261120b.service` each reached their 900-second cap; the
later 300-second `…20261120c.service` is stopped with MainPID 0. No capture process
is presumed active after that point.

Private evidence is under `~/.sv08-release-20261117/first-export-20261120/`, indexed
by `first-boot-result-private.json`; raw stable device identifiers stay private.
The Beelink copies remain in `/var/tmp/sv08-release-20261119/first-export-20261120*`.
No actual user-data archive exists yet. The tested rescue, original eMMC, normal
image source and preceding evidence remain preserved.

Next prepare a diagnostic-only SD using the unchanged sealed recovery root,
kernel/initrd/DTB and media policy, appending only `systemd.debug_shell` for a
local temporary console. Rebind the SD-only loader to that exact script and
verify all bytes before requesting a card move/write. This avoids repeating the
historically stopped UART-input variants; proposed serial-controller preparation
was stopped after source reads, without a controller or any UART transmission.
The diagnostic boot will not count as normal production acceptance. Collect the
actual normalized topology before deciding any policy/source correction.

The diagnostic continuation carries every previous attempt and charge. Native
ceiling increases from 19,800 seconds/172 GiB by 1,800 seconds/2.5 GiB to
**21,600 process-seconds/174.5 GiB**; the 32 GiB workspace remains included and deleting
files earns no credit. Conservative prior charge is 19,400 seconds/167.016 GiB.
Scope is one card-based diagnostic boot/collection, reused payloads and SD-only
loader derivation; no normal/internal-recovery/OTA rebuild, installation or output
activation is included. The separate source ceiling remains 7,200 seconds/1.25 GiB,
with its earlier 5,200 seconds/1,220 MiB carried forward. The named implementer was
requested at medium effort for the disposable recipe; effective runtime effort
has not been independently observed. Source-only preparation, independent action
assessment, actual SD boot and still-open release acceptance remain distinct.
