# Autonomous PSU-control amendment — test-sv08-01

**PASS WITH CONDITIONS**, 2026-10-04 UTC. Explicit owner authorization in the exact packet permits coordinator use of Beelink `/usr/local/bin/sv08-power on|off|status` in place of the prior human PSU ON/OFF confirmations. This satisfies the existing review intent provided the conditions below are enforced. Only that substitution is reviewed; the existing identification restrictions and physical arrangement still apply. No hardware authority is granted by this review.

## Evidence and boundaries

Measured locally: identify script hash matches the prior review (`dbfde321f5680124c9f29bb30c9d2900a015c9d79ed53d4a770c800182a58926`). Five relevant Klipper source files match the prior review hashes. Preflight script hash is `9c453919da01ce75a37d0907cfce63647216e684ec98fee1577460073bf10832`.

Recorded coordinator measurements: `preflight-before-power.json` reports root ro, masks inactive, package verification passed, prebuilt helper selected, no active printer config and mainboard only at ttyACM0. It contains neither current PSU status nor boot ID nor serial-idle proof. Normal-restart and relay observations under the 20261003 deployment directory match both installed-progress.json receipts byte-for-byte. Each reports commissioning success, distinct boot IDs, slot A/A3/B0, valid environment CRCs, read-only root/boot and all seven masks inactive. This resolves the prior review's pending healthy restart gate at the recorded evidence level; fresh gates still apply.

Owner-reported: plug controls printer PSU; USB HW667, Ethernet and media arrangement unchanged; autonomous PSU switching explicitly authorized. This is sufficient authorization for the scoped substitution, not independently measured wiring or board identity.

Coordinator source-inspection findings, recorded in packet.md: utility uses Meross channel 0 ToggleX SET with ON/OFF printed only after SETACK, System.All GET for status and 5-second HTTP timeout; credentials are read internally. Utility bytes/hash and raw current OFF observation were not supplied locally and were not independently inspected. Preserve a sanitized receipt and bind the utility before operation. SETACK alone does not replace status verification, and reported plug state does not measure voltage or establish output safety.

Write boundary: only smartplug channel state is added. USB relay, boot policy, host software, MCU configuration/firmware and output-command boundaries do not expand. PSU ON is for toolhead availability, not heater/motion commissioning. No sensor accuracy, physical electrical safety, complete firmware attestation or release qualification follows from dictionary matching.

## Conditions

1. Before ON, coordinator binds the existing Beelink /usr/local/bin/sv08-power utility by SHA256 and records sanitized source-review findings and fresh OFF status, without exposing credentials. Owner authorization and plug-to-PSU mapping are recorded in packet.md; no independent electrical measurement is claimed. Bound every control invocation by an outer process timeout (at most 15 seconds); a 5-second HTTP timeout alone is not a process bound.

2. Fresh target identity/same boot, root and boot read-only, seven masks and inactive services, absent active printer configuration, package/helper/venv/source integrity and serial idle must pass. HW667 remains ON; issue no USB relay command. USB, Ethernet, media and owner-established physical arrangement remain unchanged.

3. After exactly one ON attempt, require successful command and independent status ON. Allow at most 20 seconds for enumeration, then require fresh preflight plus both exact ALLOWED by-id devices resolving to distinct live ttyACM character devices and unchanged host boot. preflight-mcu.py alone does not require both named devices or prove serial idle/boot identity; enforce those separately. Missing device, ambiguity, boot change or unexpected activity stops.

4. Preserve original query conditions: unchanged identify script SHA256 dbfde321f5680124c9f29bb30c9d2900a015c9d79ed53d4a770c800182a58926; installed exact-pin venv, PYTHONDONTWRITEBYTECODE=1, assertions enabled, exclusive 250000 baud, one outer-15-second process per device. Mainboard must exit successfully and match exact role/by-id/resolution, retained version/build metadata for f0892d82b0f1c1228454f09eb508eddde2250f4b and uncompressed dictionary SHA256 86665c7ba90587f09347af0001faf3681cc35819141b5c37c1f646e49a15125b before toolhead. No failed-session retry, reset, configuration, output command, flash or service activation.

5. Install unconditional cleanup before attempting ON: on success or any later failure, including ON/status/enumeration/preflight/query failure, terminate surviving query processes, establish port closure, issue OFF and require successful fresh status OFF. Unexpected physical activity requires immediate OFF rather than waiting for query/normal cleanup. For ordinary control failure inspect status boundedly then issue idempotent OFF; never retry ON. If OFF/status fails or cannot establish OFF, stop and return to coordinator for owner physical intervention; do not report safe power state or retry identification. Beelink control/cleanup must remain available independently of printer SSH.

6. After OFF record same host identity and boot ID, root/boot read-only, masks/inactive services/no configuration, no surviving serial users and final topology. Preserve both command exit results and separate ON/OFF status observations with timestamps. OFF is smartplug channel state, not whole-printer isolation; mainboard/host may remain USB powered. Retain failure evidence and request owner through coordinator if postconditions fail.

## Recovery, tier and runtime

Returning the smartplug to verified OFF is the fallback; it is not firmware rollback or complete removal of printer power. No new reasoning uncertainty requiring the high profile was identified for the narrowly bounded substitution. Missing physical facts remain unknown. Unexpected behavior, conflicting identity/source binding or a materially different control implementation requires coordinator reassessment and high_consequence_reviewer_high when material uncertainty remains; higher effort cannot replace physical evidence.

The assigned runtime.json records full-role loading, GPT-6.1 Sol/medium, approval never and danger-full-access. Coordinator must verify the effective session before relying on this fallback; this review does not independently attest runtime execution settings.

Only review.md/result.json in the assigned scratch directory were written. No hardware/network command, credential/private-backup/dump read, tracked edit, Git mutation, agent launch or diagnostic experiment occurred. Review used bounded local source/evidence reads and hashes; operation remains unexecuted.
