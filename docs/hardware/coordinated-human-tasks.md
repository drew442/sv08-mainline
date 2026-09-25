# Coordinated human tasks

Dispatch queue created 2026-09-18 for the [parallel assignments](../development/parallel-work.md).
All entries below are pending coordination, not requests to act immediately.
Historical evidence and detailed acceptance remain in the [host tasks](host-os-tasks.md#human-and-powered-printer-tasks),
[recovery tasks](test-sv08-01-recovery-tasks.md) and [sensor bring-up](test-sv08-01-sensor-bringup.md).
Do not interpret old unchecked preservation or v1 imaging tasks as new requests.
The owner has accepted existing backups and USB-reader/ST-Link recovery paths.

Only the coordinator asks the owner to act. Agents submit additional consumers
or prerequisites against an existing H ID before proposing a new physical task.
No current power state, reachability, installed slot or hardware identity is
inferred from a historical report. Inspect current state before acting.

| ID / shared action | Prepare before asking | Consumers and execution order | Evidence reuse / invalidation |
| --- | --- | --- | --- |
| H01 — One accessible, fully unpowered inspection | Consolidated list of unresolved board/sensor facts, existing marking evidence and a safe isolation procedure; no unnecessary heatsink removal | Host PCB/DRAM/radio/PMIC identity; installed bed/hotend sensor and circuit identity; outstanding board revisions | One private evidence set with public nonsecret conclusions; repeat only for changed hardware/wiring or an unresolved essential detail |
| H02 — Capture-ready power isolation and boot session | Start serial logging before any reconnection; account for serial/USB back-power; review intended image/slot/boot environment and safe printer state | True cold-boot/DRAM evidence, warm boot, ordinary MCU start, host health and A/B transitions, baseline HDMI observation | Distinct captures/boot IDs per required trial; repeatability needs multiple boots, not one reused success. Loader/kernel/firmware changes invalidate affected checks |
| H03 — Write spare eMMC and reinstall | V5 is independently byte-reviewed, written once to the identified spare, and full direct-I/O readback matches the raw SHA-256. Beelink's receive-only serial capture is armed and waiting. The writer has been safely powered off through Beelink. With the printer unpowered, unplug the writer, reinstall only the spare eMMC, and stand the printer upright; keep the factory eMMC stored. Then connect the USB serial cable to Beelink (this powers the host). | V4's A boot failed during preparation and the next U-Boot pass selected recovery. V5 contains the corrected persistent-identity initramfs hook. Capture the first v5 boot, assess A/recovery behavior and record HDMI mode. Do not power-cycle again until logs are checked and the next boot is planned. | The exact v5 image hash and direct readback receipt are recorded; any media alteration or write/readback mismatch requires revalidation. Continue reusing the same capture for boot consumers |
| H04 — One physical console and peripheral session | Installed reviewed UI and input tests ready; keep Ethernet recovery; prepare private Wi-Fi configuration and camera test; optional capture/HID setup only if useful | Normal HDMI/touch, recovery touch-only/keyboard-only/mouse paths, Wi-Fi association/reconnect, retained camera presentation/streaming, USB/peripheral observations | Record image, input device, network conditions and path separately. A normal desktop observation does not prove recovery; changed UI/driver/device invalidates affected results |
| H05 — Sensor reference and input session, outputs disabled | Reviewed input-only config, matching host/MCUs, exact queries, independent temperature instrument and known physical associations | Current bed/hotend ambient comparison; probe and filament operation/polarity; resolve sensor identity from H01 before accepting conversion | Record simultaneous references/configuration and input transitions once for printer and host consumers. Old room temperature cannot satisfy a new reference check |
| H06 — Attended staged output and printing session | H05 passes; reviewed limits/homing/stop procedure; operator can stop immediately; safe mechanics and clear workspace | Separate gated steps: fans/shutdown → bounded motor direction → X/Y sensorless and Z probe homing → controlled heat/reference → PID/extrusion → leveling/mesh/manual Z offset → first layer/prints/pause/cancel | Each step has its own result and must pass before dependent action. Reuse host UI/camera observations during safe prints; changes to mechanics/sensors/firmware/config invalidate relevant results |
| H07 — Controlled failure/recovery session | Reliable baseline, reviewed failure plan, expendable data, loads safe, captures and restoration artifacts ready | Power interruption, A/B exhausted/bad trials, watchdog, physical checks consuming recovery delivery's reviewed export/restore artifacts, partial MCU update and USB-reader recovery checks | Group ready cases in one session but preserve individual outcomes and distinct safe states. Deliberate interruption is not bundled into heating/printing; final artifact changes require relevant retests |
| H08 — Release decisions and stock access | Concise unresolved license/omission choices and a stock qualification plan; no re-asking settled OS/backup decisions | Owner license decision, any actual required-feature omission, access to an actual stock profile for supported-stock qualification | Record decisions once; modified test printer first print is independent of stock access, and never certifies stock support |
| H09 — One supervised SD/NFS diagnostic boot | Physical-address SD image independently inspected, written and directly read back; spare A counter re-armed under review but still unconfirmed; temporary read-only NFSv3 export mounted successfully from Beelink and content hash checked; DHCP reservation for Beelink `.136` still required; receive-only UART process is active; separate high-consequence review says no-go until reservation and final identity checks pass | Before the session, owner reserves Beelink MAC `84:39:be:9e:10:d9` to `192.168.1.136` and confirms the reservation is active. In one session, connect printer Ethernet to the same LAN, fully isolate printer power including serial back-power, move the written SD from reader to printer, stand printer upright, arm/verify receive-only UART capture, then reconnect serial (which can start the host). Make one attempt only. Stop if the loader path is unclear, eMMC U-Boot/RAUC appears, or the diagnostic probe does not prove the NFS root; if eMMC boot occurs, record its A counter before any retry. The H02 capture is reused for this boot | Reuse the exact SD image hash, SD write receipt, Beelink export manifest/log, one boot ID and one UART trace. Success requires SD-loader, DHCP, read-only NFS-root and exact `SV08_SD_NFS_PASS root_ro=1 data_tmpfs=1 dhcp_address=1` evidence followed by diagnostic power-off. SSH/HDMI are not expected. Any failed or inconclusive selection is not proof of safe fallback or eMMC isolation |

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
priority and physical network root remain unverified.

H09 software preparation is ready, pending the owner's DHCP reservation and
physical media session. The [disposable SD/NFS image](host-sd-network-root-prototype.md)
was independently inspected, written to the USB-reader SD card and passed a
192 MiB direct readback. The spare eMMC remains on its v5 A root; a separate
reviewed operation restored three A attempts without rebooting, but A health
remains unconfirmed. See the [SD write receipt](host-sd-network-card-write-20260925.md)
and [A-counter re-arm record](host-board-image-20260925-v5-a-rearm.md). Beelink
currently owns `192.168.1.136` at MAC `84:39:be:9e:10:d9`; a local NFSv3/TCP
client mounted the sanitized export read-only and verified its init hash. The
export is also configured read-only with root-squash. The SD image hardcodes
`.136`, so reserve this address before booting. Receive-only UART capture is
active, but its connection readiness must be rechecked immediately before the
session. One high-consequence review says no-go until reservation and final
identity checks pass. The printer SD boot has not been attempted.

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
