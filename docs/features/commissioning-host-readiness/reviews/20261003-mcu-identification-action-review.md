# Exact MCU identification action review

**PASS WITH CONDITIONS** — applies only to the prepared, non-output identification operation for test-sv08-01. Date: 2026-10-03 UTC. Separate full-role CLI fallback was requested because native capacity was unavailable. Requested role is high_consequence_reviewer, GPT-6.1 Sol/medium. Effective runtime verification remains coordinator-owned and was not independently observed here. This review grants no hardware authority.

## Bound artifact and operation

Script: `deployment/identify-mcu.py`, SHA-256 `dbfde321f5680124c9f29bb30c9d2900a015c9d79ed53d4a770c800182a58926`, under the assigned commissioning probe directory. Preparation JSON agrees with the measured script hash. All reviewed source/evidence hashes are recorded in result.json.

Exact targets are the script's mainboard by-id suffix `[private-device-id]-if00` and toolhead suffix `[private-device-id]-if00`, both `usb-Klipper_stm32f103xe_...`. Device ordering is not identity. H616_JC_6Z_V1.2 is owner-reported host-board identity, not a measured MCU-board revision. Other board/sensor electrical facts remain unverified.

## Source findings and measured check

At selected f0892d82b0f1c1228454f09eb508eddde2250f4b, serialhdl.py:69-120 obtains 40-byte identify chunks, loads their dictionary and updates host-side transport settings. It does not configure MCU objects, request clocks, reset, clear shutdown, or command outputs. Its response/transport machinery may retransmit the same identify request; bypassing connect_uart removes its STK500-leave sequence and connection retry loop, not protocol retransmission. basecmd.c:361-374 identifies a read/response handler permitted in shutdown; identify does not establish an MCU's ready/safe/output state.

msgproto.py:413-441 decompresses the identify stream with zlib, retains those uncompressed bytes, parses JSON and returns version/build strings as a tuple. Hashing get_raw_data_dictionary() is correct for an uncompressed retained dictionary artifact. One synthetic offline probe measured exact byte preservation, SHA256 and tuple behavior and parsed the submitted script syntax; diagnostic.json records the result. No raw private dictionary was read. Its recorded SHA256 is the comparison reference, not a hash independently recomputed from the private artifact by this reviewer.

usb_cdc.c:452-490 requests the bootloader only when enabled and line coding is 1200 with DTR bit clear. The script sets 250000 before open; normal DTR/RTS/close control effects are still USB control operations. They are not a universal electrical-safety guarantee. Current firmware source equivalence is the question being measured; the pinned source alone cannot prove behavior of an unidentified physical MCU.

serialhdl.py:217-230 stops the serial queue, joins its reader and closes the owned port on ordinary completion/error after session ownership transfers. Opening failures before that transfer can leave cleanup to process exit. Exceptions in cleanup or a timeout can suppress JSON; require process termination/port closure and classify as failure, not success. Assertions must remain enabled. The script itself does not enforce version/hash matching or cross-device sequencing; the coordinator must enforce these externally.

chelper/__init__.py:261-321 may compile when source mtimes exceed the helper mtime or the helper is missing. The unchanged installed file-output success supports loading this package, but does not itself prove future timestamp selection. Fresh prebuilt-library selection and root read-only are required; this review covers no rebuild.

## Evidence level and applicability

Documented: proposal sensors criterion requires package/helper matching, physical two-device reconciliation and inactive private input-only file-output parsing, without flashing/output activation. Owner access amendment changes account access only. Historical 2026-09-08 sanitized observation records both f0892d8 identities, matching host, 139 messages, no outputs and stopped temporary process. It is historical communication evidence, not current device presence or physical identity waiver.

Recorded coordinator measurements: klipper-provenance.txt gives package full source pin and helper SHA256 `3bb1a213c83bbd627ae931c789b1f14c4f466d9e5ba6224bf285fc648c0509ad`; sensor-file-output.json records installed ARM64 exit 0 and both retained dictionary fixtures. Those fixtures were configured into output files, not live MCUs. Reuse the unchanged inactive config parsing result; it proves neither sensor accuracy nor live MCU configuration. Intake records package file verification and only mainboard enumeration while last reported PSU state was off.

The handoff reports current full pin matching checkout and proposes queries after corrected host plus two restart checks. Those future checks and fresh topology were not measured in this review. The available repair preflight says passed/executed false; normal-restart-command.txt contains only 0. Neither establishes both restart acceptance. The public lock records the expected full source revision; no Git or hardware/network command was run to independently attest current commit state.

A matched dictionary/version reconciles protocol/build metadata with the selected artifact. It does not attest the complete flashed binary, bootloader/option bytes, crystal, board wiring, thermistor circuits, safe powered outputs or restored factory firmware. Modified sensors remain uncommissioned.

## Conditions before and after action

1. Coordinator records corrected-host acceptance and both required restart checks before this operation; a restart command exit 0 is not restart acceptance.

2. Fresh evidence immediately before communication: root read-only, all seven diagnostic masks unchanged, printer services inactive, no active printer.cfg, no printer/serial-using processes; installed package verification and selected full source/helper/venv dependency integrity unchanged. Verify helper timestamp selection takes the prebuilt-library branch, not auto-compilation; no runtime repair or install is covered.

3. Owner confirms current physical arrangement and performs PSU ON solely for toolhead availability, retaining USB host power and the specified USB relay/Ethernet/spare/SD-removed arrangement. Stop on unexpected physical activity; masks/inventory do not establish electrical safety. Fresh topology must bind both exact by-id symlinks to distinct live ttyACM character devices and the historical physical role mapping; unknown or conflicting mapping stops.

4. Use the hash-bound script via stdin with /opt/sv08-mainline/venvs/klipper-f0892d8/bin/python, PYTHONDONTWRITEBYTECODE=1, assertions enabled, and an outer 15-second timeout. One process per named device, sequentially, exclusive USB CDC at 250000 baud. No additional commands, retries of a failed session, service/config activation, reset, bootloader request, or flashing.

5. After mainboard exits successfully, compare role/by-id/resolved topology, reported version f0892d8 and build metadata against retained exact-pin metadata, plus SHA256 of uncompressed dictionary bytes equal to 86665c7ba90587f09347af0001faf3681cc35819141b5c37c1f646e49a15125b. Only then query toolhead and repeat the comparisons. Error, timeout, mismatch, re-enumeration, or uncertain outcome stops without flashing. A short version alone is insufficient.

6. On success or failure, terminate any surviving query process and establish ports closed; return owner instruction to set printer PSU OFF while preserving USB host power. Record owner confirmation, post-action topology, root/masks/inactive services/no active configuration/processes unchanged. No automated rollback or reset; unresolved physical behavior goes to coordinator.

## Stop, recovery and review tier

There is no intended persistent MCU write and no configuration activation. Stop the bounded process, close ports, request owner PSU OFF preserving host USB power and retain the failed evidence; do not repair, retry, reset, flash or swap firmware as fallback. Unexpected activity on PSU ON requires the physical stop procedure immediately, rather than waiting for identification. Recovery beyond returning to the stated arrangement needs a new exact action packet.

No unresolved source-semantics uncertainty requiring a high-profile reasoning review was found. Pending physical evidence/owner confirmation remain hard execution gates; higher effort cannot replace them. If new source mismatch, topology ambiguity or unexpected hardware behavior introduces material uncertainty, return to the coordinator for high_consequence_reviewer_high selection before further action.

Only scratch diagnostic.json, review.md and result.json were written. No tracked edits, Git operation, hardware/network access, raw dumps, credentials, private backups, agents or operation execution. Auxiliary usage: one synthetic probe, approximately 0.01 seconds measured body runtime, outputs well below 8 MiB. Primary task stayed within six minutes and 16 MiB.
